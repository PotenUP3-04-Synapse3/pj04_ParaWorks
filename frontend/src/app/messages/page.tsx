"use client";

import { Hash, Send } from "lucide-react";
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
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-muted">{copy.eyebrow}</p>
        <h2 className="mt-1 text-2xl font-semibold tracking-normal">{copy.title}</h2>
      </div>

      <section className="grid min-h-[640px] overflow-hidden rounded-md border border-line bg-white lg:grid-cols-[280px_1fr]">
        <aside className="border-b border-line bg-neutral-50 lg:border-b-0 lg:border-r">
          <div className="border-b border-line px-4 py-3">
            <h3 className="text-sm font-semibold">{copy.channels}</h3>
          </div>
          <div className="space-y-1 p-2">
            {channels.map((channel) => {
              const active = channel.id === activeChannelId;
              return (
                <button
                  key={channel.id}
                  type="button"
                  onClick={() => setActiveChannelId(channel.id)}
                  className={`flex w-full items-start gap-3 rounded-md px-3 py-3 text-left ${
                    active ? "bg-white shadow-sm ring-1 ring-line" : "hover:bg-white"
                  }`}
                >
                  <Hash className="mt-0.5 h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold">{channel.name}</span>
                    <span className="mt-1 line-clamp-2 block text-xs leading-5 text-muted">
                      {channel.description}
                    </span>
                  </span>
                  {channel.unread_count > 0 ? (
                    <span className="rounded-full bg-neutral-900 px-2 py-0.5 text-xs font-medium text-white">
                      {channel.unread_count}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
        </aside>

        <div className="flex min-w-0 flex-col">
          <header className="border-b border-line px-5 py-4">
            <div className="flex items-center gap-2">
              <Hash className="h-4 w-4 text-muted" aria-hidden="true" />
              <h3 className="text-base font-semibold">{activeChannel?.name ?? copy.channels}</h3>
            </div>
            {activeChannel ? (
              <p className="mt-1 text-sm text-muted">{activeChannel.description}</p>
            ) : null}
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto bg-white p-5">
            {error ? (
              <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                {error}
              </div>
            ) : null}
            {notice ? (
              <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                {notice}
              </div>
            ) : null}
            {loading ? <p className="text-sm text-muted">Loading...</p> : null}
            {!loading && messages.length === 0 ? (
              <p className="text-sm text-muted">{copy.empty}</p>
            ) : null}
            {messages.map((message) => (
              <article key={message.id} className="flex gap-3">
                <div className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-neutral-900 text-sm font-semibold text-white">
                  {message.author_name.slice(0, 1)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline gap-2">
                    <h4 className="text-sm font-semibold">{message.author_name}</h4>
                    <span className="text-xs text-muted">{message.author_role}</span>
                    <time className="text-xs text-muted" dateTime={message.created_at}>
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
                    className="mt-2 inline-flex h-8 items-center rounded-md border border-line bg-white px-3 text-xs font-medium text-ink hover:bg-neutral-50 disabled:cursor-not-allowed disabled:text-muted"
                  >
                    {reviewMessageId === message.id ? copy.sendingToReview : copy.sendToReview}
                  </button>
                </div>
              </article>
            ))}
          </div>

          <form onSubmit={submit} className="border-t border-line bg-neutral-50 p-4">
            <label htmlFor="message-draft" className="text-sm font-medium">
              {copy.composerLabel}
            </label>
            <div className="mt-2 flex flex-col gap-2 sm:flex-row">
              <input
                id="message-draft"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                className="h-10 min-w-0 flex-1 rounded-md border border-line bg-white px-3 text-sm outline-none focus:border-neutral-500"
                placeholder={copy.composerPlaceholder}
              />
              <button
                type="submit"
                disabled={sending || draft.trim().length === 0}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-neutral-900 bg-neutral-900 px-4 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-neutral-400"
              >
                <Send className="h-4 w-4" aria-hidden="true" />
                {sending ? copy.sending : copy.send}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  );
}
