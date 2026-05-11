"use client";

import { useEffect, useState } from "react";
import { FileText, Database, AlertTriangle, Info } from "lucide-react";
import { apiGet } from "@/lib/api/client";
import type { DocumentSummary } from "@/lib/api/types";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;
    setLoading(true);
    apiGet<DocumentSummary[]>("/api/v1/documents")
      .then((data) => {
        if (active) setDocuments(data);
      })
      .catch((caught) => {
        if (active) setError(caught instanceof Error ? caught.message : "문서 목록을 불러오지 못했습니다.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-4">
      <div className="page-heading">
        <div>
          <p className="border-b border-muted pb-1 text-[13px] font-bold text-[var(--primary-dark)]">파서 가시성</p>
          <h1>수집 문서 목록</h1>
          <p>로컬에 동기화된 시스템 문서와 본문 파싱 상태를 확인합니다.</p>
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-[13px] text-red-800">
          {error}
        </div>
      ) : null}

      <div className="space-y-3">
        {loading ? (
          <div className="panel p-8 text-center text-[13px] text-muted">문서 데이터를 불러오고 있습니다...</div>
        ) : documents.length === 0 ? (
          <div className="panel p-8 text-center text-[13px] text-muted">수집된 문서가 없습니다.</div>
        ) : (
          documents.map((doc) => (
            <article key={doc.id} className="panel flex flex-col gap-3 sm:flex-row sm:items-start p-4">
              <FileText className="mt-0.5 h-5 w-5 shrink-0 text-muted" aria-hidden="true" />
              <div className="flex-1 space-y-2">
                <div>
                  <h2 className="text-[15px] font-extrabold text-foreground">{doc.title}</h2>
                  <p className="text-[12px] text-muted">Source ID: {doc.source_id} &middot; Version: {doc.current_version}</p>
                </div>
                
                <div className="flex flex-wrap items-center gap-2">
                  {doc.parser_status === "parsed" && (
                    <span className="badge green flex items-center gap-1">
                      <Database className="h-3 w-3" />
                      Parsed ({doc.chunk_count} chunks)
                    </span>
                  )}
                  {doc.parser_status === "metadata_only" && (
                    <span className="badge amber flex items-center gap-1" title={doc.parser_status_reason || "Metadata only"}>
                      <AlertTriangle className="h-3 w-3" />
                      Metadata Only
                    </span>
                  )}
                  {doc.parser_status === "unsupported" && (
                    <span className="badge red flex items-center gap-1" title={doc.parser_status_reason || "Unsupported type"}>
                      <Info className="h-3 w-3" />
                      Unsupported
                    </span>
                  )}
                  
                  {doc.parser_name && (
                    <span className="badge border bg-[var(--glass-elevated)]">{doc.parser_name}</span>
                  )}
                  {doc.revision_id && (
                    <span className="text-[12px] text-muted ml-auto">Rev: {doc.revision_id}</span>
                  )}
                </div>
              </div>
            </article>
          ))
        )}
      </div>
    </div>
  );
}
