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
        className="inline-flex h-9 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-neutral-50"
      >
        <FileText className="h-4 w-4" aria-hidden="true" />
        근거
      </button>
      {open ? (
        <div className="fixed inset-0 z-40">
          <button
            type="button"
            className="absolute inset-0 cursor-default bg-black/20"
            aria-label="출처 근거 닫기"
            onClick={() => setOpen(false)}
          />
          <aside className="absolute inset-y-0 right-0 flex w-full max-w-xl flex-col border-l border-line bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <div>
                <h2 className="text-base font-semibold">출처 근거</h2>
                <p className="text-sm text-muted">이 항목에 연결된 snippet {snippets.length}개</p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="grid h-9 w-9 place-items-center rounded-md border border-line text-muted hover:bg-neutral-50 hover:text-ink"
                aria-label="닫기"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-4">
              <div className="space-y-4">
                {snippets.map((snippet, index) => (
                  <section key={`${snippet}-${index}`} className="rounded-md border border-line p-4">
                    <p className="text-sm leading-6 text-ink">{snippet}</p>
                    {links[index] ? (
                      <a
                        href={links[index]}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-neutral-700 underline-offset-4 hover:underline"
                      >
                        원문 열기
                        <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                      </a>
                    ) : null}
                  </section>
                ))}
                {snippets.length === 0 ? (
                  <p className="rounded-md border border-line p-4 text-sm text-muted">
                    이 항목에 연결된 출처 snippet이 없습니다.
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
