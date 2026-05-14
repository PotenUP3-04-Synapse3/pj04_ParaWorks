"use client";

import { useEffect, useState } from "react";
import { FileText, Database, AlertTriangle, Info, XCircle, BarChart3 } from "lucide-react";
import { apiGet } from "@/lib/api/client";
import type { DocumentSummary } from "@/lib/api/types";

interface ParserStat {
  mime_type: string;
  parser_status: string;
  parser_name: string;
  document_count: number;
  total_chunks: number;
}

interface ParserStatsSummary {
  total_documents: number;
  parsed_count: number;
  metadata_only_count: number;
  error_count: number;
  unsupported_count: number;
}

interface ParserStatsResponse {
  stats: ParserStat[];
  summary: ParserStatsSummary;
}

/**
 * 문서의 파싱 상태에 따른 뱃지를 표시합니다.
 */
function StatusBadge({ status, reason }: { status?: string | null; reason?: string | null }) {
  if (!status) return null;
  if (status === "parsed")
    return (
      <span className="badge green flex items-center gap-1">
        <Database className="h-3 w-3" /> Parsed
      </span>
    );
  if (status === "metadata_only")
    return (
      <span className="badge amber flex items-center gap-1" title={reason || "Metadata only"}>
        <AlertTriangle className="h-3 w-3" /> Metadata Only
      </span>
    );
  if (status === "unsupported")
    return (
      <span className="badge red flex items-center gap-1" title={reason || "Unsupported type"}>
        <Info className="h-3 w-3" /> Unsupported
      </span>
    );
  if (status === "error")
    return (
      <span className="badge red flex items-center gap-1" title={reason || "Parse error"}>
        <XCircle className="h-3 w-3" /> Error
      </span>
    );
  return <span className="badge">{status}</span>;
}

/**
 * 파서 현황 요약 및 상세 내역(MIME 타입별)을 보여주는 위젯입니다.
 */
function ParserStatsWidget({ stats }: { stats: ParserStatsResponse }) {
  const { summary } = stats;
  const cards = [
    { label: "전체 문서", value: summary.total_documents, color: "var(--foreground)" },
    { label: "파싱 완료", value: summary.parsed_count, color: "#22c55e" },
    { label: "메타데이터만", value: summary.metadata_only_count, color: "#f59e0b" },
    { label: "오류", value: summary.error_count, color: "#ef4444" },
    { label: "미지원", value: summary.unsupported_count, color: "#6b7280" },
  ];

  return (
    <div className="panel p-4 space-y-4">
      <div className="flex items-center gap-2">
        <BarChart3 className="h-4 w-4 text-muted" />
        <span className="text-[13px] font-bold text-foreground">파서 현황 요약</span>
      </div>

      {/* 요약 카드 그리드 */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-lg border border-[var(--border)] bg-[var(--glass-elevated)] p-3 text-center"
          >
            <p className="text-2xl font-extrabold" style={{ color: card.color }}>
              {card.value}
            </p>
            <p className="text-[11px] text-muted">{card.label}</p>
          </div>
        ))}
      </div>

      {/* MIME 타입별 상세 표 */}
      {stats.stats.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-[var(--border)]">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="bg-[var(--glass-elevated)] text-left">
                <th className="px-3 py-2 font-semibold text-muted">MIME Type</th>
                <th className="px-3 py-2 font-semibold text-muted">파서</th>
                <th className="px-3 py-2 font-semibold text-muted">상태</th>
                <th className="px-3 py-2 text-right font-semibold text-muted">문서 수</th>
                <th className="px-3 py-2 text-right font-semibold text-muted">청크 수</th>
              </tr>
            </thead>
            <tbody>
              {stats.stats.map((row, i) => (
                <tr key={i} className="border-t border-[var(--border)] hover:bg-[var(--glass-elevated)]">
                  <td className="px-3 py-2 font-mono text-[11px] text-muted truncate max-w-[180px]" title={row.mime_type}>
                    {row.mime_type.split("/").pop()}
                  </td>
                  <td className="px-3 py-2 text-foreground">{row.parser_name}</td>
                  <td className="px-3 py-2">
                    <StatusBadge status={row.parser_status} />
                  </td>
                  <td className="px-3 py-2 text-right font-bold text-foreground">{row.document_count}</td>
                  <td className="px-3 py-2 text-right text-muted">{row.total_chunks}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/**
 * 수집 문서 목록 및 파싱 상태 확인 페이지
 */
export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [parserStats, setParserStats] = useState<ParserStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;
    setLoading(true);

    // 문서 목록과 파서 통계를 병렬로 조회
    Promise.all([
      apiGet<DocumentSummary[]>("/api/v1/documents"),
      apiGet<ParserStatsResponse>("/api/v1/documents/parser-stats"),
    ])
      .then(([docs, stats]) => {
        if (active) {
          setDocuments(docs);
          setParserStats(stats);
        }
      })
      .catch((caught) => {
        if (active)
          setError(caught instanceof Error ? caught.message : "문서 목록을 불러오지 못했습니다.");
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
          <p className="border-b border-muted pb-1 text-[13px] font-bold text-[var(--primary-dark)]">
            파서 가시성
          </p>
          <h1>수집 문서 목록</h1>
          <p>로컬에 동기화된 시스템 문서와 본문 파싱 상태를 확인합니다.</p>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-[13px] text-red-800">
          {error}
        </div>
      )}

      {/* 파서 현황 요약 위젯 */}
      {!loading && parserStats && <ParserStatsWidget stats={parserStats} />}

      {/* 문서 목록 영역 */}
      <div className="space-y-3">
        {loading ? (
          <div className="panel p-8 text-center text-[13px] text-muted">
            문서 데이터를 불러오고 있습니다...
          </div>
        ) : documents.length === 0 ? (
          <div className="panel p-8 text-center text-[13px] text-muted">수집된 문서가 없습니다.</div>
        ) : (
          documents.map((doc) => (
            <article
              key={doc.id}
              className="panel flex flex-col gap-3 sm:flex-row sm:items-start p-4"
            >
              <FileText className="mt-0.5 h-5 w-5 shrink-0 text-muted" aria-hidden="true" />
              <div className="flex-1 space-y-2">
                <div>
                  <h2 className="text-[15px] font-extrabold text-foreground">{doc.title}</h2>
                  <p className="text-[12px] text-muted">
                    Source ID: {doc.source_id} &middot; Version: {doc.current_version}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={doc.parser_status} reason={doc.parser_status_reason} />

                  {doc.chunk_count !== undefined && doc.parser_status === "parsed" && (
                    <span className="text-[12px] text-muted">{doc.chunk_count} chunks</span>
                  )}

                  {doc.parser_name && (
                    <span className="badge border bg-[var(--glass-elevated)]">
                      {doc.parser_name}
                    </span>
                  )}
                  {doc.revision_id && (
                    <span className="text-[12px] text-muted ml-auto">
                      Rev: {doc.revision_id}
                    </span>
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
