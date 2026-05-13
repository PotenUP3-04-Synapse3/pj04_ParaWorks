"use client";

import {
  Bot,
  ChevronDown,
  ChevronRight,
  Copy,
  FileText,
  Link2,
  MessageSquareText,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Send,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { apiGet, apiPost } from "@/lib/api/client";
import type {
  AssistantConversation,
  AssistantConversationCreatedResponse,
  AssistantConversationsResponse,
  AssistantMessage,
  AssistantMessagesResponse,
  AssistantTurnResponse,
  RagCitation,
} from "@/lib/api/types";

const DEFAULT_CONVERSATION_TITLE = "새 대화";
const SUGGESTED_QUESTIONS = [
  "기획팀 회의 일정을 정리해줘",
  "최근 결정된 사항만 요약해줘",
  "내가 확인해야 할 할 일을 알려줘",
  "관련 근거가 있는 문서만 찾아줘",
];

export default function SearchPage() {
  return (
    <Suspense fallback={<SearchPageFallback />}>
      <SearchPageContent />
    </Suspense>
  );
}

function SearchPageContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q")?.trim() || "";
  const [conversations, setConversations] = useState<AssistantConversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<AssistantConversation>();
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [openEvidenceMessageIds, setOpenEvidenceMessageIds] = useState<Set<number>>(new Set());
  const [query, setQuery] = useState(initialQuery);
  const [loading, setLoading] = useState(false);
  const [booting, setBooting] = useState(true);
  const [error, setError] = useState<string>();
  const [initialQuerySent, setInitialQuerySent] = useState(false);
  const [copiedMessageId, setCopiedMessageId] = useState<number>();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const loadingRef = useRef(false);
  const creatingConversationRef = useRef(false);
  const loadMessagesRequestRef = useRef(0);
  const activeConversationIdRef = useRef<number | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const upsertConversationByUpdatedAt = useCallback((conversation: AssistantConversation) => {
    setConversations((current) => sortConversationsByUpdatedAt([
      conversation,
      ...current.filter((item) => item.id !== conversation.id),
    ]));
  }, []);

  const createConversation = useCallback(async (title?: string) => {
    const requestId = ++loadMessagesRequestRef.current;
    const response = await apiPost<AssistantConversationCreatedResponse>("/api/v1/assistant/conversations", {
      title: title?.trim() || DEFAULT_CONVERSATION_TITLE,
    });
    if (requestId === loadMessagesRequestRef.current) {
      activeConversationIdRef.current = response.conversation.id;
      setActiveConversation(response.conversation);
      setMessages([]);
      setOpenEvidenceMessageIds(new Set());
      upsertConversationByUpdatedAt(response.conversation);
    }
    return response.conversation;
  }, [upsertConversationByUpdatedAt]);

  const loadMessages = useCallback(async (conversation: AssistantConversation) => {
    const requestId = ++loadMessagesRequestRef.current;
    setError(undefined);
    activeConversationIdRef.current = conversation.id;
    setActiveConversation(conversation);
    try {
      const response = await apiGet<AssistantMessagesResponse>(
        `/api/v1/assistant/conversations/${conversation.id}/messages`,
      );
      if (requestId !== loadMessagesRequestRef.current) return [];

      activeConversationIdRef.current = response.conversation.id;
      setActiveConversation(response.conversation);
      setMessages(response.messages);
      setOpenEvidenceMessageIds(new Set());
      upsertConversationByUpdatedAt(response.conversation);
      return response.messages;
    } catch (caught) {
      if (requestId === loadMessagesRequestRef.current) {
        setError(caught instanceof Error ? caught.message : "대화 내용을 불러오지 못했습니다.");
      }
      return [];
    }
  }, [upsertConversationByUpdatedAt]);

  const loadConversations = useCallback(async () => {
    setBooting(true);
    setError(undefined);
    try {
      const response = await apiGet<AssistantConversationsResponse>("/api/v1/assistant/conversations");
      const sortedConversations = sortConversationsByUpdatedAt(response.conversations);
      setConversations(sortedConversations);
      if (sortedConversations.length > 0) {
        await loadMessages(sortedConversations[0]);
      } else {
        await createConversation(initialQuery || DEFAULT_CONVERSATION_TITLE);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "AI 비서 대화를 준비하지 못했습니다.");
    } finally {
      setBooting(false);
    }
  }, [createConversation, initialQuery, loadMessages]);

  const sendMessage = useCallback(async (content: string) => {
    const trimmedContent = content.trim();
    if (!trimmedContent || loadingRef.current) return;

    loadingRef.current = true;
    setLoading(true);
    setError(undefined);
    try {
      const conversation = activeConversation ?? await createConversation(trimmedContent);
      const response = await apiPost<AssistantTurnResponse>(
        `/api/v1/assistant/conversations/${conversation.id}/messages`,
        { content: trimmedContent },
      );
      if (activeConversationIdRef.current !== conversation.id) return;

      activeConversationIdRef.current = response.conversation.id;
      setActiveConversation(response.conversation);
      setMessages((currentMessages) => [
        ...currentMessages,
        response.user_message,
        response.assistant_message,
      ]);
      setOpenEvidenceMessageIds(new Set());
      upsertConversationByUpdatedAt(response.conversation);
      setQuery("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "메시지를 보내지 못했습니다.");
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [activeConversation, createConversation, upsertConversationByUpdatedAt]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;
    void sendMessage(query);
  }

  async function handleNewConversation() {
    if (creatingConversationRef.current) return;
    creatingConversationRef.current = true;
    try {
      setError(undefined);
      setQuery("");
      if (isReusableActiveConversation(activeConversation, messages)) return;

      const reusableConversation = conversations.find(isDefaultConversation);
      if (reusableConversation) {
        await loadMessages(reusableConversation);
        return;
      }

      await createConversation(DEFAULT_CONVERSATION_TITLE);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "새 대화를 만들지 못했습니다.");
    } finally {
      creatingConversationRef.current = false;
    }
  }

  function toggleEvidence(messageId: number) {
    setOpenEvidenceMessageIds((current) => {
      const next = new Set(current);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  }

  async function copyMessage(message: AssistantMessage) {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedMessageId(message.id);
      window.setTimeout(() => setCopiedMessageId((current) => current === message.id ? undefined : current), 1600);
    } catch {
      setError("메시지를 복사하지 못했습니다.");
    }
  }

  useEffect(() => {
    setQuery(initialQuery);
    setInitialQuerySent(false);
  }, [initialQuery]);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    if (booting || initialQuerySent || !initialQuery || !activeConversation) return;

    setInitialQuerySent(true);
    void sendMessage(initialQuery);
  }, [activeConversation, booting, initialQuery, initialQuerySent, sendMessage]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, loading]);

  return (
    <div className="reference-dashboard h-[calc(100vh-7rem)] overflow-hidden">
      <section
        className={`grid h-full min-h-0 gap-3 transition-[grid-template-columns] duration-300 ease-out ${
          sidebarCollapsed ? "lg:grid-cols-[72px_minmax(0,1fr)]" : "lg:grid-cols-[280px_minmax(0,1fr)]"
        }`}
      >
        <aside
          aria-label="대화 목록"
          data-expanded={sidebarCollapsed ? "false" : "true"}
          className={`panel reference-panel group flex h-full min-h-0 flex-col overflow-hidden rounded-2xl transition-all duration-300 ease-out hover:shadow-panel-hover ${
            sidebarCollapsed ? "w-[72px] px-2 py-3" : "w-full"
          }`}
        >
          <div className={`flex items-center gap-2 ${sidebarCollapsed ? "flex-col" : "justify-between border-b border-line pb-3"}`}>
            <div className={`min-w-0 ${sidebarCollapsed ? "sr-only" : ""}`}>
              <p className="text-[12px] font-bold text-[var(--primary-dark)]">AI 비서</p>
              <h2 className="truncate text-[15px] font-extrabold">대화</h2>
            </div>
            <div className={`flex shrink-0 gap-2 ${sidebarCollapsed ? "flex-col" : ""}`}>
              <button
                type="button"
                title={sidebarCollapsed ? "대화 목록 펼치기" : "대화 목록 접기"}
                aria-label={sidebarCollapsed ? "대화 목록 펼치기" : "대화 목록 접기"}
                onClick={() => setSidebarCollapsed((current) => !current)}
                className="row-action h-9 w-9 p-0 transition-transform duration-200 group-hover:scale-105"
              >
                {sidebarCollapsed ? (
                  <PanelLeftOpen className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <PanelLeftClose className="h-4 w-4" aria-hidden="true" />
                )}
              </button>
              <button
                type="button"
                title="새 대화 만들기"
                aria-label="새 대화 만들기"
                onClick={() => void handleNewConversation()}
                className="row-action h-9 w-9 p-0 transition-transform duration-200 group-hover:scale-105"
                disabled={booting}
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>

          {sidebarCollapsed ? (
            <div className="mt-4 grid flex-1 place-items-start justify-center">
              <div className="grid h-10 w-10 place-items-center rounded-full bg-[var(--primary-soft)] text-[var(--primary-dark)]">
                <MessageSquareText className="h-4 w-4" aria-hidden="true" />
              </div>
            </div>
          ) : (
            <div aria-label="대화 히스토리" className="mt-3 flex-1 space-y-1 overflow-y-auto pr-1">
              {conversations.map((conversation) => {
                const selected = conversation.id === activeConversation?.id;
                return (
                  <button
                    key={conversation.id}
                    type="button"
                    onClick={() => void loadMessages(conversation)}
                    className={`w-full truncate rounded-xl px-3 py-2 text-left text-[13px] font-bold transition ${
                      selected
                        ? "bg-[var(--primary-soft)] text-[var(--primary-dark)]"
                        : "text-[var(--ink)] hover:bg-[var(--glass-strong)]"
                    }`}
                  >
                    {conversation.title || DEFAULT_CONVERSATION_TITLE}
                  </button>
                );
              })}
              {booting ? (
                <div className="rounded-xl border border-dashed border-line bg-surface-soft p-3 text-[13px] text-muted">
                  대화를 불러오는 중입니다.
                </div>
              ) : null}
            </div>
          )}
        </aside>

        <main className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl bg-[var(--surface)] p-0 shadow-panel">
          {error ? (
            <div className="mx-auto mt-4 w-full max-w-3xl rounded-lg border border-red-200 bg-red-50 p-3 text-[13px] text-red-800">
              {error}
            </div>
          ) : null}

          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
            <div className="mx-auto flex max-w-3xl flex-col gap-5">
              {messages.map((message) => (
                <AssistantBubble
                  key={message.id}
                  message={message}
                  evidenceOpen={openEvidenceMessageIds.has(message.id)}
                  onToggleEvidence={() => toggleEvidence(message.id)}
                  copied={copiedMessageId === message.id}
                  onCopy={() => void copyMessage(message)}
                />
              ))}
              {!booting && messages.length === 0 ? (
                <div className="flex min-h-[420px] flex-col items-center justify-center text-center">
                  <Bot className="h-9 w-9 text-[var(--primary)]" aria-hidden="true" />
                  <h1 className="mt-4 text-[22px] font-black">무엇을 도와드릴까요?</h1>
                  <p className="mt-2 max-w-lg text-[13px] leading-6 text-muted">
                    회사 기억, 승인된 지식, 접근 가능한 근거를 바탕으로 답변합니다.
                  </p>
                </div>
              ) : null}
              {loading ? (
                <div className="flex justify-start">
                  <div className="rounded-lg bg-[var(--glass-elevated)] px-4 py-3 text-[13px] text-muted">
                    답변을 정리하는 중입니다...
                  </div>
                </div>
              ) : null}
              <div ref={messagesEndRef} />
            </div>
          </div>

          <form
            aria-label="AI 비서 입력"
            onSubmit={submit}
            className="bg-white/80 px-4 pb-4 pt-2 backdrop-blur-md sm:px-6"
          >
            <div className="mx-auto max-w-3xl">
              <div className="mb-3 flex flex-wrap justify-center gap-2">
                {SUGGESTED_QUESTIONS.map((question) => (
                  <button
                    key={question}
                    type="button"
                    onClick={() => void sendMessage(question)}
                    disabled={loading || booting}
                    className="rounded-full bg-[var(--primary)] px-3 py-2 text-[12px] font-bold leading-5 text-white transition hover:bg-[var(--primary-dark)] disabled:bg-neutral-300"
                  >
                    {question}
                  </button>
                ))}
              </div>
              <label htmlFor="assistant-query" className="sr-only">AI 비서에게 질문</label>
              <div className="flex items-end gap-2 rounded-2xl border border-line bg-[var(--glass-elevated)] p-2 shadow-xs focus-within:border-[var(--primary)]">
                <textarea
                  id="assistant-query"
                  aria-label="AI 비서에게 질문"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      void sendMessage(query);
                    }
                  }}
                  className="max-h-32 min-h-11 min-w-0 flex-1 resize-none bg-transparent px-2 py-2 text-[14px] leading-6 outline-none"
                  placeholder="회사 기억에서 무엇을 찾아볼까요?"
                  disabled={booting}
                  rows={1}
                />
                <button
                  type="submit"
                  aria-label="전송"
                  disabled={loading || booting || query.trim().length === 0}
                  className="row-action h-10 w-10 shrink-0 p-0 disabled:bg-neutral-300"
                >
                  <Send className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
            </div>
          </form>
        </main>
      </section>
    </div>
  );
}

function SearchPageFallback() {
  return <div className="panel reference-panel p-8 text-[13px] text-muted">AI 비서 화면을 준비하고 있습니다.</div>;
}

function AssistantBubble({
  message,
  evidenceOpen,
  onToggleEvidence,
  copied,
  onCopy,
}: {
  message: AssistantMessage;
  evidenceOpen: boolean;
  onToggleEvidence: () => void;
  copied: boolean;
  onCopy: () => void;
}) {
  const isAssistant = message.role === "assistant";
  const evidenceCount = evidenceItemCount(message);

  return (
    <article className={`flex ${isAssistant ? "justify-start" : "justify-end"}`}>
      <div className={`min-w-0 ${isAssistant ? "w-full" : "max-w-[82%]"}`}>
        <div
          className={
            isAssistant
              ? "rounded-lg bg-transparent px-4 py-3 text-[14px] leading-7"
              : "rounded-full bg-[var(--primary)] px-3 py-2 text-[12px] font-bold leading-5 text-white"
          }
        >
          {isAssistant ? (
            <MarkdownContent content={message.content} />
          ) : (
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          )}
        </div>

        <div className={`mt-1 flex ${isAssistant ? "justify-start" : "justify-end"}`}>
          <button
            type="button"
            onClick={onCopy}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[12px] font-bold text-muted hover:bg-[var(--glass-strong)] hover:text-[var(--ink)]"
          >
            <Copy className="h-3.5 w-3.5" aria-hidden="true" />
            {copied ? "복사됨" : "복사"}
          </button>
        </div>

        {isAssistant && evidenceCount > 0 ? (
          <div className="mt-2">
            <button
              type="button"
              onClick={onToggleEvidence}
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[12px] font-bold text-[var(--primary-dark)] hover:bg-[var(--primary-soft)]"
            >
              {evidenceOpen ? (
                <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              근거와 출처 {evidenceCount.toLocaleString()}개 {evidenceOpen ? "접기" : "펼치기"}
            </button>
            {evidenceOpen ? <EvidenceDisclosure message={message} /> : null}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function MarkdownContent({ content }: { content: string }) {
  const lines = content.split(/\r?\n/);
  const blocks = [];
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (!line.trim()) {
      blocks.push(<div key={`space-${index}`} className="h-2" />);
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      const level = heading[1].length;
      const className = level === 1
        ? "text-[18px] font-black"
        : level === 2
          ? "text-[16px] font-extrabold"
          : "text-[14px] font-extrabold";
      blocks.push(<h3 key={`heading-${index}`} className={`mt-2 break-words ${className}`}>{renderInlineMarkdown(heading[2])}</h3>);
      continue;
    }

    if (line.trimStart().startsWith("- ")) {
      const items = [];
      let listIndex = index;
      while (listIndex < lines.length && lines[listIndex].trimStart().startsWith("- ")) {
        items.push(lines[listIndex].trimStart().slice(2));
        listIndex += 1;
      }
      blocks.push(
        <ul key={`list-${index}`} className="my-2 list-disc space-y-1 pl-5">
          {items.map((item, itemIndex) => (
            <li key={`${item}-${itemIndex}`} className="break-words">{renderInlineMarkdown(item)}</li>
          ))}
        </ul>,
      );
      index = listIndex - 1;
      continue;
    }

    blocks.push(<p key={`paragraph-${index}`} className="whitespace-pre-wrap break-words">{renderInlineMarkdown(line)}</p>);
  }

  return <div className="space-y-1">{blocks}</div>;
}

function renderInlineMarkdown(text: string) {
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  const parts = text.split(pattern);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={`${part}-${index}`} className="rounded bg-surface-soft px-1 py-0.5 text-[13px]">{part.slice(1, -1)}</code>;
    }
    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (link) {
      return (
        <a
          key={`${part}-${index}`}
          href={link[2]}
          target="_blank"
          rel="noreferrer"
          className="font-bold text-[var(--primary-dark)] underline-offset-4 hover:underline"
        >
          {link[1]}
        </a>
      );
    }
    return part;
  });
}

function EvidenceDisclosure({ message }: { message: AssistantMessage }) {
  const citations = message.citations ?? [];
  const citationSnippets = new Set(citations.map((citation) => citation.source_snippet));
  const snippets = (message.source_snippets ?? []).filter((snippet) => !citationSnippets.has(snippet));
  const links = message.source_links ?? [];

  return (
    <div className="mt-2 max-h-72 overflow-y-auto rounded-lg border border-line bg-[var(--glass-elevated)] p-3">
      {message.permission_notice ? (
        <div className="mb-3 flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-[12px] leading-5 text-amber-900">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p>{message.permission_notice}</p>
        </div>
      ) : null}

      <EvidenceCitationList citations={citations} />

      {snippets.length > 0 ? (
        <section className="mt-3">
          <h3 className="mb-2 flex items-center gap-1 text-[12px] font-extrabold">
            <FileText className="h-3.5 w-3.5" aria-hidden="true" />
            원문 발췌
          </h3>
          <div className="space-y-2">
            {snippets.map((snippet, index) => (
              <p
                key={`${snippet}-${index}`}
                className="rounded-md border border-line bg-surface-soft p-3 text-[12px] leading-5 text-muted"
              >
                {snippet}
              </p>
            ))}
          </div>
        </section>
      ) : null}

      {links.length > 0 ? (
        <section className="mt-3">
          <h3 className="mb-2 flex items-center gap-1 text-[12px] font-extrabold">
            <Link2 className="h-3.5 w-3.5" aria-hidden="true" />
            출처 링크
          </h3>
          <div className="space-y-2">
            {links.map((link, index) => (
              <a
                key={`${link}-${index}`}
                href={link}
                target="_blank"
                rel="noreferrer"
                className="block break-all rounded-md border border-line bg-surface-soft p-3 text-[12px] font-bold text-[var(--primary-dark)] underline-offset-4 hover:underline"
              >
                {link}
              </a>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function EvidenceCitationList({ citations }: { citations: RagCitation[] }) {
  if (citations.length === 0) return null;

  return (
    <section>
      <h3 className="mb-2 flex items-center gap-1 text-[12px] font-extrabold">
        <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
        인용 근거
      </h3>
      <div className="space-y-2">
        {citations.map((citation, index) => (
          <a
            key={`${citation.source_id}-${index}`}
            href={citation.source_url}
            target="_blank"
            rel="noreferrer"
            className="block rounded-md border border-line bg-surface-soft p-3 text-[12px] hover:bg-[var(--glass-strong)]"
          >
            <span className="font-bold text-[var(--primary-dark)]">근거 {index + 1}</span>
            <span className="mt-1 block break-all text-muted">{citation.source_id}</span>
            <span className="mt-1 block text-muted">관련도 {citation.relevance_score.toFixed(2)}</span>
            {citation.matched_terms.length ? (
              <span className="mt-2 flex flex-wrap gap-1">
                {citation.matched_terms.map((term, termIndex) => (
                  <span key={`${term}-${termIndex}`} className="filter-pill active">{term}</span>
                ))}
              </span>
            ) : null}
            <span className="mt-2 block border-l-2 border-line pl-3 leading-5 text-muted">
              {citation.source_snippet}
            </span>
          </a>
        ))}
      </div>
    </section>
  );
}

function evidenceItemCount(message: AssistantMessage) {
  return Math.max(
    message.citations.length,
    message.source_links.length,
    message.source_snippets.length,
  );
}

function isDefaultConversation(conversation: AssistantConversation) {
  return conversation.title.trim() === DEFAULT_CONVERSATION_TITLE;
}

function isReusableActiveConversation(
  conversation: AssistantConversation | undefined,
  messages: AssistantMessage[],
) {
  return Boolean(conversation && isDefaultConversation(conversation) && messages.length === 0);
}

function sortConversationsByUpdatedAt(conversations: AssistantConversation[]) {
  return [...conversations].sort((left, right) => {
    const timeDiff = new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime();
    return timeDiff || right.id - left.id;
  });
}
