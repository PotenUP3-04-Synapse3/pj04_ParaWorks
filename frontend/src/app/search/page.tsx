"use client";

import {
  Bot,
  CheckCircle2,
  Clock3,
  Database,
  FileText,
  Link2,
  Plus,
  Send,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiGet, apiPost } from "@/lib/api/client";
import type {
  AssistantConversation,
  AssistantConversationCreatedResponse,
  AssistantConversationsResponse,
  AssistantMessage,
  AssistantMessagesResponse,
  AssistantTurnResponse,
  RagCitation,
  RagIndexingJobSummary,
  RagIndexingSummaryResponse,
} from "@/lib/api/types";

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
  const [selectedEvidenceMessageId, setSelectedEvidenceMessageId] = useState<number>();
  const [query, setQuery] = useState(initialQuery);
  const [ragIndexing, setRagIndexing] = useState<RagIndexingSummaryResponse>();
  const [loading, setLoading] = useState(false);
  const [booting, setBooting] = useState(true);
  const [error, setError] = useState<string>();
  const [initialQuerySent, setInitialQuerySent] = useState(false);
  const loadingRef = useRef(false);
  const loadMessagesRequestRef = useRef(0);
  const activeConversationIdRef = useRef<number | undefined>(undefined);

  const selectLatestAssistantEvidence = useCallback((nextMessages: AssistantMessage[]) => {
    const latestAssistant = [...nextMessages].reverse().find((message) => message.role === "assistant");
    setSelectedEvidenceMessageId(latestAssistant?.id);
  }, []);

  const moveConversationToTop = useCallback((conversation: AssistantConversation) => {
    setConversations((current) => [
      conversation,
      ...current.filter((item) => item.id !== conversation.id),
    ]);
  }, []);

  const createConversation = useCallback(async (title?: string) => {
    const requestId = ++loadMessagesRequestRef.current;
    const response = await apiPost<AssistantConversationCreatedResponse>("/api/v1/assistant/conversations", {
      title: title?.trim() || "새 대화",
    });
    if (requestId === loadMessagesRequestRef.current) {
      activeConversationIdRef.current = response.conversation.id;
      setActiveConversation(response.conversation);
      setMessages([]);
      setSelectedEvidenceMessageId(undefined);
      moveConversationToTop(response.conversation);
    }
    return response.conversation;
  }, [moveConversationToTop]);

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
      moveConversationToTop(response.conversation);
      selectLatestAssistantEvidence(response.messages);
      return response.messages;
    } catch (caught) {
      if (requestId === loadMessagesRequestRef.current) {
        setError(caught instanceof Error ? caught.message : "대화 내용을 불러오지 못했습니다.");
      }
      return [];
    }
  }, [moveConversationToTop, selectLatestAssistantEvidence]);

  const loadConversations = useCallback(async () => {
    setBooting(true);
    setError(undefined);
    try {
      const response = await apiGet<AssistantConversationsResponse>("/api/v1/assistant/conversations");
      setConversations(response.conversations);
      if (response.conversations.length > 0) {
        await loadMessages(response.conversations[0]);
      } else {
        await createConversation(initialQuery || "새 대화");
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
      setSelectedEvidenceMessageId(response.assistant_message.id);
      moveConversationToTop(response.conversation);
      setQuery("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "메시지를 보내지 못했습니다.");
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [activeConversation, createConversation, moveConversationToTop]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;
    void sendMessage(query);
  }

  async function handleNewConversation() {
    try {
      setError(undefined);
      await createConversation("새 대화");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "새 대화를 만들지 못했습니다.");
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
    let active = true;
    apiGet<RagIndexingSummaryResponse>("/api/v1/rag/indexing/summary")
      .then((result) => {
        if (active) setRagIndexing(result);
      })
      .catch(() => {
        if (active) setRagIndexing(undefined);
      });
    return () => {
      active = false;
    };
  }, []);

  const selectedEvidenceMessage = useMemo(
    () => messages.find((message) => message.id === selectedEvidenceMessageId)
      ?? [...messages].reverse().find((message) => message.role === "assistant"),
    [messages, selectedEvidenceMessageId],
  );

  return (
    <div className="reference-dashboard space-y-4">
      <div className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">AI Assistant</p>
          <h1>AI 비서와 대화</h1>
          <p>대화를 기억하면서 회사 지식에 기반한 답변과 확인 가능한 근거를 함께 보여줍니다.</p>
        </div>
        <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold">
          <Bot className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
          대화형 검색
        </div>
      </div>

      <MemoryFreshnessPanel summary={ragIndexing} />

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-[13px] text-red-800">{error}</div>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)_360px]">
        <aside className="panel reference-panel h-fit">
          <div className="flex items-center justify-between gap-3 border-b border-line pb-4">
            <div>
              <h2 className="text-[15px] font-extrabold">대화 목록</h2>
              <p className="mt-1 text-[12px] text-muted">{conversations.length.toLocaleString()}개 대화</p>
            </div>
            <button
              type="button"
              title="새 대화"
              aria-label="새 대화"
              onClick={() => void handleNewConversation()}
              className="row-action h-9 w-9 p-0"
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>

          <div className="mt-4 space-y-2">
            {conversations.map((conversation) => {
              const selected = conversation.id === activeConversation?.id;
              return (
                <button
                  key={conversation.id}
                  type="button"
                  onClick={() => void loadMessages(conversation)}
                  className={`w-full rounded-lg border p-3 text-left text-[13px] transition ${
                    selected
                      ? "border-[var(--primary)] bg-[var(--glass-strong)]"
                      : "border-line bg-[var(--glass-elevated)] hover:bg-[var(--glass-strong)]"
                  }`}
                >
                  <span className="block truncate font-extrabold">{conversation.title || "새 대화"}</span>
                  {conversation.summary ? (
                    <span className="mt-1 block line-clamp-2 text-[12px] leading-5 text-muted">
                      {conversation.summary}
                    </span>
                  ) : null}
                  <span className="mt-2 block text-[11px] text-muted">{formatDateTime(conversation.updated_at)}</span>
                </button>
              );
            })}
            {booting ? (
              <div className="rounded-lg border border-dashed border-line bg-surface-soft p-4 text-[13px] text-muted">
                대화를 불러오는 중입니다.
              </div>
            ) : null}
          </div>
        </aside>

        <main className="panel reference-panel flex min-h-[620px] flex-col">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
            <div>
              <h2 className="text-[15px] font-extrabold">AI 비서와 대화</h2>
              <p className="mt-1 text-[12px] text-muted">
                {activeConversation?.title || "새 대화"}
              </p>
            </div>
            <span className="badge blue">{messages.length.toLocaleString()}개 메시지</span>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto py-4">
            {messages.map((message) => (
              <AssistantBubble
                key={message.id}
                message={message}
                selected={message.id === selectedEvidenceMessage?.id}
                onSelectEvidence={() => setSelectedEvidenceMessageId(message.id)}
              />
            ))}
            {!booting && messages.length === 0 ? (
              <div className="rounded-lg border border-dashed border-line bg-surface-soft p-8 text-center text-[13px] text-muted">
                첫 질문을 입력하면 AI 비서가 답변과 근거를 함께 정리합니다.
              </div>
            ) : null}
          </div>

          <form onSubmit={submit} className="border-t border-line pt-4">
            <label htmlFor="assistant-query" className="sr-only">AI 비서에게 질문</label>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                id="assistant-query"
                aria-label="AI 비서에게 질문"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="h-11 min-w-0 flex-1 rounded-lg border border-line bg-[var(--glass-elevated)] px-3 text-[13px] outline-none focus:border-[var(--primary)]"
                placeholder="예: 최근 Redis 운영 이슈를 정리해줘"
                disabled={booting}
              />
              <button
                type="submit"
                disabled={loading || booting || query.trim().length === 0}
                className="row-action gap-2 px-4 disabled:bg-neutral-300"
              >
                <Send className="h-4 w-4" aria-hidden="true" />
                {loading ? "보내는 중" : "보내기"}
              </button>
            </div>
          </form>
        </main>

        <EvidencePanel message={selectedEvidenceMessage} />
      </section>
    </div>
  );
}

function SearchPageFallback() {
  return <div className="panel reference-panel p-8 text-[13px] text-muted">AI 비서 화면을 준비하고 있습니다.</div>;
}

function AssistantBubble({
  message,
  selected,
  onSelectEvidence,
}: {
  message: AssistantMessage;
  selected: boolean;
  onSelectEvidence: () => void;
}) {
  const isAssistant = message.role === "assistant";
  const evidenceCount = message.citations.length || message.source_links.length || message.source_snippets.length;

  return (
    <article className={`flex ${isAssistant ? "justify-start" : "justify-end"}`}>
      <div
        className={`max-w-[88%] rounded-lg border p-4 text-[13px] leading-6 ${
          isAssistant
            ? "border-line bg-[var(--glass-elevated)]"
            : "border-[var(--primary)] bg-[var(--primary)] text-white"
        }`}
      >
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className={isAssistant ? "badge blue" : "rounded-md bg-white/20 px-2 py-1 text-[11px] font-bold"}>
            {isAssistant ? "AI 비서" : "나"}
          </span>
          {message.permission_level ? <span className="badge green">{message.permission_level}</span> : null}
          {isAssistant ? <span className="badge violet">근거 {evidenceCount.toLocaleString()}개</span> : null}
          {message.hidden_match_count > 0 ? (
            <span className="badge amber">숨겨진 근거 {message.hidden_match_count.toLocaleString()}개</span>
          ) : null}
        </div>
        <p className="whitespace-pre-wrap break-words">{message.content}</p>
        {isAssistant ? (
          <button
            type="button"
            onClick={onSelectEvidence}
            className={`mt-3 inline-flex items-center gap-1 text-[12px] font-bold underline-offset-4 hover:underline ${
              selected ? "text-[var(--primary-dark)]" : "text-muted"
            }`}
          >
            <Link2 className="h-3.5 w-3.5" aria-hidden="true" />
            근거 보기
          </button>
        ) : null}
      </div>
    </article>
  );
}

function EvidencePanel({ message }: { message?: AssistantMessage }) {
  const citations = message?.citations ?? [];
  const snippets = message?.source_snippets ?? [];
  const links = message?.source_links ?? [];
  const hiddenCount = message?.hidden_match_count ?? 0;

  return (
    <aside className="panel reference-panel h-fit">
      <div className="flex items-center gap-2 border-b border-line pb-4">
        <FileText className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
        <h2 className="text-[15px] font-extrabold">근거와 출처</h2>
      </div>

      {!message ? (
        <div className="mt-4 rounded-lg border border-dashed border-line bg-surface-soft p-6 text-[13px] text-muted">
          답변을 선택하면 참조한 근거와 권한 정보를 확인할 수 있습니다.
        </div>
      ) : (
        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap gap-2">
            {message.permission_level ? <span className="badge green">{message.permission_level}</span> : null}
            <span className="badge violet">근거 {Math.max(citations.length, links.length, snippets.length).toLocaleString()}개</span>
            {hiddenCount > 0 ? <span className="badge amber">숨겨진 근거 {hiddenCount.toLocaleString()}개</span> : null}
          </div>

          {message.permission_notice ? (
            <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-[12px] leading-5 text-amber-900">
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <p>{message.permission_notice}</p>
            </div>
          ) : null}

          <EvidenceCitationList citations={citations} />

          {snippets.length > 0 ? (
            <div>
              <h3 className="mb-2 text-[13px] font-extrabold">원문 발췌</h3>
              <div className="space-y-2">
                {snippets.map((snippet, index) => (
                  <p
                    key={`${snippet}-${index}`}
                    className="rounded-lg border border-line bg-[var(--glass-elevated)] p-3 text-[12px] leading-5 text-muted"
                  >
                    {snippet}
                  </p>
                ))}
              </div>
            </div>
          ) : null}

          {links.length > 0 ? (
            <div>
              <h3 className="mb-2 text-[13px] font-extrabold">출처 링크</h3>
              <div className="space-y-2">
                {links.map((link, index) => (
                  <a
                    key={`${link}-${index}`}
                    href={link}
                    target="_blank"
                    rel="noreferrer"
                    className="block break-all rounded-lg border border-line bg-[var(--glass-elevated)] p-3 text-[12px] font-bold text-[var(--primary-dark)] underline-offset-4 hover:underline"
                  >
                    {link}
                  </a>
                ))}
              </div>
            </div>
          ) : null}

          {citations.length === 0 && snippets.length === 0 && links.length === 0 ? (
            <div className="rounded-lg border border-dashed border-line bg-surface-soft p-6 text-[13px] text-muted">
              현재 권한으로 표시할 수 있는 근거가 없습니다.
            </div>
          ) : null}
        </div>
      )}
    </aside>
  );
}

function EvidenceCitationList({ citations }: { citations: RagCitation[] }) {
  if (citations.length === 0) return null;

  return (
    <div>
      <h3 className="mb-2 text-[13px] font-extrabold">인용 근거</h3>
      <div className="space-y-2">
        {citations.map((citation, index) => (
          <a
            key={`${citation.source_id}-${index}`}
            href={citation.source_url}
            target="_blank"
            rel="noreferrer"
            className="block rounded-lg border border-line bg-[var(--glass-elevated)] p-3 text-[12px] hover:bg-[var(--glass-strong)]"
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
    </div>
  );
}

function MemoryFreshnessPanel({ summary }: { summary?: RagIndexingSummaryResponse }) {
  const latestJob = summary?.latest_jobs[0];
  const indexedCount = summary?.state_counts.indexed ?? 0;
  const state = getFreshnessState(latestJob, indexedCount);
  const Icon = state.icon;

  return (
    <section className={`rounded-lg border p-4 shadow-sm ${state.tone}`}>
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div className="flex items-start gap-3">
          <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
          <div>
            <h2 className="text-[14px] font-extrabold">{state.title}</h2>
            <p className="mt-1 text-[13px] opacity-85">{state.description}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="inline-flex w-fit items-center gap-2 rounded-lg bg-white/70 px-3 py-2 text-[12px] font-bold">
            <Database className="h-4 w-4" aria-hidden="true" />
            {indexedCount.toLocaleString()}개 기억 사용 가능
          </span>
          {latestJob ? (
            <span className="inline-flex w-fit items-center gap-2 rounded-lg bg-white/70 px-3 py-2 text-[12px] font-bold">
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              {latestJob.status}
            </span>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function getFreshnessState(job: RagIndexingJobSummary | undefined, indexedCount: number) {
  if (!job) {
    return {
      title: "회사 기억 준비 중",
      description: "아직 인덱싱 기록이 없습니다. 연동된 업무 기록이 준비되면 답변 근거로 사용할 수 있습니다.",
      tone: "border-[var(--line-soft)] bg-[var(--glass-elevated)] text-[var(--ink)]",
      icon: Clock3,
    };
  }
  if (job.status === "failed") {
    return {
      title: "회사 기억 업데이트 확인 필요",
      description: "최근 인덱싱 작업이 실패했습니다. 기존 기억은 계속 사용할 수 있지만 최신 반영 상태를 확인해 주세요.",
      tone: "border-red-200 bg-red-50 text-red-900",
      icon: ShieldAlert,
    };
  }
  if (job.status === "queued" || job.status === "running") {
    return {
      title: "회사 기억 업데이트 중",
      description: "새 업무 기록을 반영하고 있습니다. 현재 답변은 마지막 완료 시점의 기억을 기준으로 합니다.",
      tone: "border-blue-200 bg-blue-50 text-blue-900",
      icon: Clock3,
    };
  }
  if (indexedCount === 0) {
    return {
      title: "검색 가능한 회사 기억이 없습니다",
      description: "현재 권한으로 볼 수 있는 업무 기록이 아직 없습니다. 연동 상태를 확인한 뒤 다시 질문해 주세요.",
      tone: "border-amber-200 bg-amber-50 text-amber-900",
      icon: ShieldAlert,
    };
  }
  return {
    title: "회사 기억이 최신 상태입니다",
    description: `최근 업데이트: ${formatDateTime(job.updated_at)}. 접근 가능한 업무 기록을 기준으로 답변합니다.`,
    tone: "border-emerald-200 bg-emerald-50 text-emerald-900",
    icon: CheckCircle2,
  };
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
