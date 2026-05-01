"use client";

import { ExternalLink, FileText, X } from "lucide-react";
import { useState } from "react";

type SourceEvidenceDrawerProps = {
  links: string[];
  snippets: string[];
};

export function SourceEvidenceDrawer({ links, snippets }: SourceEvidenceDrawerProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--line-soft)] bg-white px-3 text-sm font-semibold text-ink shadow-sm hover:bg-[#fbfaf8]"
      >
        <FileText className="h-4 w-4" aria-hidden="true" />
        근거 보기
      </button>
      {open ? (
        <div className="fixed inset-0 z-40">
          <button
            type="button"
            className="absolute inset-0 cursor-default bg-black/30"
            aria-label="출처 근거 닫기"
            onClick={() => setOpen(false)}
          />
          <aside className="absolute inset-y-0 right-0 flex w-full max-w-xl flex-col border-l border-[var(--line-soft)] bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-[var(--line-soft)] px-5 py-4">
              <div>
                <h2 className="text-base font-semibold">출처 근거</h2>
                <p className="text-sm text-[var(--ink-muted)]">
                  Review 후보와 연결된 snippet {snippets.length}개
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="grid h-9 w-9 place-items-center rounded-lg border border-[var(--line-soft)] text-[var(--ink-muted)] hover:bg-[#fbfaf8] hover:text-ink"
                aria-label="닫기"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-4">
              <div className="space-y-4">
                {snippets.map((snippet, index) => (
                  <section
                    key={`${snippet}-${index}`}
                    className="rounded-lg border border-[var(--line-soft)] bg-[#fbfaf8] p-4"
                  >
                    <p className="text-sm leading-6 text-ink">{snippet}</p>
                    {links[index] ? (
                      <a
                        href={links[index]}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-[#21132b] underline-offset-4 hover:underline"
                      >
                        원문 열기
                        <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                      </a>
                    ) : null}
                  </section>
                ))}
                {snippets.length === 0 ? (
                  <p className="rounded-lg border border-dashed border-[var(--line-soft)] p-4 text-sm text-[var(--ink-muted)]">
                    이 항목과 연결된 출처 snippet이 없습니다.
                  </p>
                ) : null}
              </div>
            </div>
          </aside>
        </div>
      ) : null}
    </>
  );
}
