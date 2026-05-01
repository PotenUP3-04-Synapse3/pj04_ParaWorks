"use client";

import { Bot, CheckCheck, Hash, MoreHorizontal, Send, Sparkles } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "@/lib/api/client";
import type {
  ChannelMessagesResponse,
  Message,
  MessageChannel,
  MessageChannelsResponse,
  ReviewItem,
} from "@/lib/api/types";
import { useLanguage } from "@/lib/i18n/LanguageProvider";

export default function MessagesPage() {
  const { dictionary } = useLanguage();
  const copy = dictionary.messages;
  const [channels, setChannels] = useState<MessageChannel[]>([]);
  const [activeChannelId, setActiveChannelId] = useState<string>("announcements");
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [reviewMessageId, setReviewMessageId] = useState<string>();
  const [notice, setNotice] = useState<string>();
  const [error, setError] = useState<string>();

  const activeChannel = useMemo(
    () => channels.find((channel) => channel.id === activeChannelId),
    [activeChannelId, channels],
  );

  const loadChannels = useCallback(async () => {
    const response = await apiGet<MessageChannelsResponse>("/api/v1/messages/channels");
    setChannels(response.channels);
    if (response.channels.length > 0) {
      setActiveChannelId((current) => current || response.channels[0].id);
    }
  }, []);

  const loadMessages = useCallback(
    async (channelId: string) => {
      setLoading(true);
      setError(undefined);

      try {
        const response = await apiGet<ChannelMessagesResponse>(
          `/api/v1/messages/channels/${channelId}/messages`,
        );
        setMessages(response.messages);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : copy.loadError);
      } finally {
        setLoading(false);
      }
    },
    [copy.loadError],
  );

  useEffect(() => {
    void loadChannels().catch((caught) => {
      setError(caught instanceof Error ? caught.message : copy.loadError);
      setLoading(false);
    });
  }, [copy.loadError, loadChannels]);

  useEffect(() => {
    if (activeChannelId) {
      void loadMessages(activeChannelId);
    }
  }, [activeChannelId, loadMessages]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = draft.trim();
    if (!body || sending) return;

    setSending(true);
    setError(undefined);

    try {
      const created = await apiPost<Message>(
        `/api/v1/messages/channels/${activeChannelId}/messages`,
        { body },
      );
      setMessages((current) => [...current, created]);
      setDraft("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : copy.sendError);
    } finally {
      setSending(false);
    }
  }

  async function sendToReview(message: Message) {
    setReviewMessageId(message.id);
    setNotice(undefined);
    setError(undefined);

    try {
      await apiPost<ReviewItem>(`/api/v1/messages/messages/${message.id}/send-to-review`);
      setNotice(copy.reviewSent);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : copy.reviewError);
    } finally {
      setReviewMessageId(undefined);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold text-[var(--workspace-rail-active)]">{copy.eyebrow}</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-normal">{copy.title}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--ink-muted)]">
            팀 대화를 검토 큐와 에이전트 타임라인으로 연결하는 ParaWorks 협업 공간입니다.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-white px-3 py-2 text-sm text-[var(--ink-muted)] shadow-sm">
          <Sparkles className="h-4 w-4 text-[var(--workspace-accent)]" aria-hidden="true" />
          Slack Agent 연결 준비 중
        </div>
      </div>

      <section className="grid min-h-[680px] overflow-hidden rounded-lg border border-[var(--line-soft)] bg-white shadow-sm lg:grid-cols-[300px_1fr]">
        <aside className="border-b border-[var(--line-soft)] bg-[#fbfaf8] lg:border-b-0 lg:border-r">
          <div className="border-b border-[var(--line-soft)] px-4 py-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">{copy.channels}</h3>
              <button
                type="button"
                className="grid h-8 w-8 place-items-center rounded-lg text-[var(--ink-muted)] hover:bg-white"
                aria-label="채널 메뉴"
              >
                <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
            <p className="mt-1 text-xs text-[var(--ink-muted)]">프로젝트, 공지, 운영 채널</p>
          </div>
          <div className="space-y-1 p-2">
            {channels.map((channel) => {
              const active = channel.id === activeChannelId;
              return (
                <button
                  key={channel.id}
                  type="button"
                  onClick={() => setActiveChannelId(channel.id)}
                  className={`flex w-full items-start gap-3 rounded-lg px-3 py-3 text-left transition ${
                    active
                      ? "bg-white shadow-sm ring-1 ring-[var(--line-soft)]"
                      : "hover:bg-white/80"
                  }`}
                >
                  <span
                    className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg ${
                      active ? "bg-[var(--workspace-rail)] text-white" : "bg-white text-[var(--ink-muted)]"
                    }`}
                  >
                    <Hash className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold">{channel.name}</span>
                    <span className="mt-1 line-clamp-2 block text-xs leading-5 text-[var(--ink-muted)]">
                      {channel.description}
                    </span>
                  </span>
                  {channel.unread_count > 0 ? (
                    <span className="rounded-full bg-[var(--workspace-accent)] px-2 py-0.5 text-xs font-bold text-[#13231f]">
                      {channel.unread_count}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
        </aside>

        <div className="flex min-w-0 flex-col">
          <header className="border-b border-[var(--line-soft)] bg-white px-5 py-4">
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <div>
                <div className="flex items-center gap-2">
                  <Hash className="h-4 w-4 text-[var(--ink-muted)]" aria-hidden="true" />
                  <h3 className="text-lg font-semibold">{activeChannel?.name ?? copy.channels}</h3>
                </div>
                {activeChannel ? (
                  <p className="mt-1 text-sm text-[var(--ink-muted)]">{activeChannel.description}</p>
                ) : null}
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex h-8 items-center gap-1 rounded-lg border border-[var(--line-soft)] bg-[#fbfaf8] px-3 text-xs font-semibold text-[var(--ink-muted)]">
                  <Bot className="h-3.5 w-3.5" aria-hidden="true" />
                  요약 대기
                </span>
                <span className="inline-flex h-8 items-center gap-1 rounded-lg border border-emerald-100 bg-emerald-50 px-3 text-xs font-semibold text-emerald-700">
                  <CheckCheck className="h-3.5 w-3.5" aria-hidden="true" />
                  Review 연결
                </span>
              </div>
            </div>
          </header>

          <div className="flex-1 space-y-1 overflow-y-auto bg-white px-5 py-4">
            {error ? (
              <div className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                {error}
              </div>
            ) : null}
            {notice ? (
              <div className="mb-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                {notice}
              </div>
            ) : null}
            {loading ? <p className="text-sm text-[var(--ink-muted)]">Loading...</p> : null}
            {!loading && messages.length === 0 ? (
              <p className="text-sm text-[var(--ink-muted)]">{copy.empty}</p>
            ) : null}
            {messages.map((message) => (
              <article
                key={message.id}
                className="group -mx-2 flex gap-3 rounded-lg px-2 py-2 transition hover:bg-[#fbfaf8]"
              >
                <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[var(--workspace-rail)] text-sm font-semibold text-white">
                  {message.author_name.slice(0, 1)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline gap-2">
                    <h4 className="text-sm font-semibold">{message.author_name}</h4>
                    <span className="text-xs text-[var(--ink-muted)]">{message.author_role}</span>
                    <time className="text-xs text-[var(--ink-muted)]" dateTime={message.created_at}>
                      {new Intl.DateTimeFormat("ko-KR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      }).format(new Date(message.created_at))}
                    </time>
                  </div>
                  <p className="mt-1 text-sm leading-6">{message.body}</p>
                  <button
                    type="button"
                    onClick={() => void sendToReview(message)}
                    disabled={Boolean(reviewMessageId)}
                    className="mt-2 inline-flex h-8 items-center rounded-lg border border-[var(--line-soft)] bg-white px-3 text-xs font-semibold text-ink opacity-100 shadow-sm hover:bg-[#f6f3ef] disabled:cursor-not-allowed disabled:text-[var(--ink-muted)] sm:opacity-0 sm:group-hover:opacity-100"
                  >
                    {reviewMessageId === message.id ? copy.sendingToReview : copy.sendToReview}
                  </button>
                </div>
              </article>
            ))}
          </div>

          <form onSubmit={submit} className="border-t border-[var(--line-soft)] bg-[#fbfaf8] p-4">
            <div className="rounded-xl border border-[var(--line-soft)] bg-white p-2 shadow-sm">
              <label htmlFor="message-draft" className="sr-only">
                {copy.composerLabel}
              </label>
              <input
                id="message-draft"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                className="h-11 w-full min-w-0 rounded-lg border-0 bg-white px-3 text-sm outline-none"
                placeholder={copy.composerPlaceholder}
              />
              <div className="mt-2 flex items-center justify-between border-t border-[var(--line-soft)] pt-2">
                <span className="text-xs text-[var(--ink-muted)]">
                  근거가 되는 대화는 Review 큐로 보내 에이전트가 히스토리 후보로 만들 수 있습니다.
                </span>
              <button
                type="submit"
                disabled={sending || draft.trim().length === 0}
                  className="inline-flex h-9 shrink-0 items-center justify-center gap-2 rounded-lg border border-[#21132b] bg-[#21132b] px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:border-neutral-300 disabled:bg-neutral-300"
              >
                <Send className="h-4 w-4" aria-hidden="true" />
                {sending ? copy.sending : copy.send}
              </button>
              </div>
            </div>
          </form>
        </div>
      </section>
    </div>
  );
}
