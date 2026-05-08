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

export default function MessagesPage() {
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

  const loadMessages = useCallback(async (channelId: string) => {
    setLoading(true);
    setError(undefined);
    try {
      const response = await apiGet<ChannelMessagesResponse>(`/api/v1/messages/channels/${channelId}/messages`);
      setMessages(response.messages);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "메시지를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadChannels().catch((caught) => {
      setError(caught instanceof Error ? caught.message : "채널을 불러오지 못했습니다.");
      setLoading(false);
    });
  }, [loadChannels]);

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
      const created = await apiPost<Message>(`/api/v1/messages/channels/${activeChannelId}/messages`, { body });
      setMessages((current) => [...current, created]);
      setDraft("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "메시지를 보내지 못했습니다.");
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
      setNotice("Review Queue에 추가했습니다.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Review Queue로 보내지 못했습니다.");
    } finally {
      setReviewMessageId(undefined);
    }
  }

  return (
    <div className="reference-dashboard space-y-4">
      <div className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Messenger</p>
          <h1>실시간 활동</h1>
          <p>내부 메시지를 확인하고 필요한 대화는 Review Queue로 보내 회사 메모리 후보로 검토합니다.</p>
        </div>
        <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold">
          <Sparkles className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
          Review 연결 활성
        </div>
      </div>

      <section className="grid min-h-[680px] overflow-hidden rounded-lg border border-line bg-white shadow-sm lg:grid-cols-[300px_1fr]">
        <aside className="border-b border-line bg-[#fbfcff] lg:border-b-0 lg:border-r">
          <div className="border-b border-line px-4 py-4">
            <div className="flex items-center justify-between">
              <h2 className="text-[14px] font-extrabold">채널</h2>
              <button type="button" className="icon-button small" aria-label="채널 메뉴">
                <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
            <p className="mt-1 text-[12px] text-muted">프로젝트, 공지, 운영 채널</p>
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
                    active ? "bg-white shadow-sm ring-1 ring-line" : "hover:bg-white/80"
                  }`}
                >
                  <span className={`source-logo ${active ? "blue" : ""}`}>
                    <Hash className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13px] font-extrabold">{channel.name}</span>
                    <span className="mt-1 line-clamp-2 block text-[12px] leading-5 text-muted">
                      {channel.description}
                    </span>
                  </span>
                  {channel.unread_count > 0 ? <span className="nav-badge">{channel.unread_count}</span> : null}
                </button>
              );
            })}
          </div>
        </aside>

        <div className="flex min-w-0 flex-col">
          <header className="border-b border-line bg-white px-5 py-4">
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <div>
                <div className="flex items-center gap-2">
                  <Hash className="h-4 w-4 text-muted" aria-hidden="true" />
                  <h2 className="text-[18px] font-extrabold">{activeChannel?.name ?? "채널"}</h2>
                </div>
                {activeChannel ? <p className="mt-1 text-[13px] text-muted">{activeChannel.description}</p> : null}
              </div>
              <div className="flex items-center gap-2">
                <span className="badge blue">
                  <Bot className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
                  요약 대기
                </span>
                <span className="badge green">
                  <CheckCheck className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
                  Review 연결
                </span>
              </div>
            </div>
          </header>

          <div className="flex-1 space-y-1 overflow-y-auto bg-white px-5 py-4">
            {error ? <div className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-[13px] text-red-800">{error}</div> : null}
            {notice ? <div className="mb-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-[13px] text-emerald-800">{notice}</div> : null}
            {loading ? <p className="text-[13px] text-muted">Loading...</p> : null}
            {!loading && messages.length === 0 ? <p className="text-[13px] text-muted">표시할 메시지가 없습니다.</p> : null}
            {messages.map((message) => (
              <article key={message.id} className="group -mx-2 flex gap-3 rounded-lg px-2 py-2 transition hover:bg-[#fbfcff]">
                <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#243152] text-[13px] font-bold text-white">
                  {message.author_name.slice(0, 1)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline gap-2">
                    <h3 className="text-[13px] font-extrabold">{message.author_name}</h3>
                    <span className="text-[12px] text-muted">{message.author_role}</span>
                    <time className="text-[12px] text-muted" dateTime={message.created_at}>
                      {new Intl.DateTimeFormat("ko-KR", { hour: "2-digit", minute: "2-digit" }).format(new Date(message.created_at))}
                    </time>
                  </div>
                  <p className="mt-1 text-[13px] leading-6">{message.body}</p>
                  <button
                    type="button"
                    onClick={() => void sendToReview(message)}
                    disabled={Boolean(reviewMessageId)}
                    className="mt-2 inline-flex h-8 items-center rounded-lg border border-line bg-white px-3 text-[12px] font-bold text-ink shadow-sm hover:bg-[#f6f8fb] disabled:cursor-not-allowed disabled:text-muted"
                  >
                    {reviewMessageId === message.id ? "보내는 중..." : "Review Queue로 보내기"}
                  </button>
                </div>
              </article>
            ))}
          </div>

          <form onSubmit={submit} className="border-t border-line bg-[#fbfcff] p-4">
            <div className="rounded-xl border border-line bg-white p-2 shadow-sm">
              <label htmlFor="message-draft" className="sr-only">메시지 입력</label>
              <input
                id="message-draft"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                className="h-11 w-full min-w-0 rounded-lg border-0 bg-white px-3 text-[13px] outline-none"
                placeholder="메시지를 입력하세요"
              />
              <div className="mt-2 flex items-center justify-between border-t border-line pt-2">
                <span className="text-[12px] text-muted">근거가 되는 대화는 Review Queue로 보내 검토할 수 있습니다.</span>
                <button type="submit" disabled={sending || draft.trim().length === 0} className="row-action gap-2 px-4 disabled:bg-neutral-300">
                  <Send className="h-4 w-4" aria-hidden="true" />
                  {sending ? "전송 중" : "보내기"}
                </button>
              </div>
            </div>
          </form>
        </div>
      </section>
    </div>
  );
}
