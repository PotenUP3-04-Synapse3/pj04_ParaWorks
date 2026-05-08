import {
  ArrowRight,
  BarChart3,
  Bot,
  FileText,
  Mail,
  MessageSquare,
  MoreHorizontal,
  Pause,
  Settings,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { serverApiGet } from "@/lib/api/server";
import type { AgentRunsResponse, DashboardResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

const FALLBACK_DASHBOARD: DashboardResponse = {
  source_counts: {
    slack: 128,
    gmail: 62,
    drive: 34,
    calendar: 18,
    other: 6,
  },
  pending_review_count: 12,
  recent_jobs: [],
};

const FALLBACK_AGENT_RUNS: AgentRunsResponse = {
  total_runs: 248,
  total_tokens: 1240000,
  estimated_cost_usd: 124.58,
  recent_runs: [],
};

const sourceCards = [
  { label: "전체 소스", key: "all", value: 248, detail: "실시간", icon: BarChart3, tone: "neutral" },
  { label: "Slack", key: "slack", value: 128, detail: "실시간", icon: MessageSquare, tone: "slack" },
  { label: "Gmail", key: "gmail", value: 62, detail: "실시간", icon: Mail, tone: "gmail" },
  { label: "Google Drive", key: "drive", value: 34, detail: "실시간", icon: FileText, tone: "drive" },
  { label: "기타", key: "other", value: 6, detail: "실시간", icon: MoreHorizontal, tone: "neutral" },
];

const activities = [
  {
    time: "11:42:31",
    source: "Slack",
    title: "#project-orion 스레드 수집 완료",
    detail: "김하나님의 언급됨 · 고객사 요구사항 변경에 대한 논의",
    meta: "Slack · #project-orion · 참여자 6명",
    status: "미분석",
    priority: "높은 중요도",
    tone: "purple",
  },
  {
    time: "11:31:05",
    source: "Gmail",
    title: "FW: Oracle DB 선정 이유",
    detail: "이메일 스레드 수집 완료 (8개 메시지)",
    meta: "Gmail · 프로젝트 오리온",
    status: "분석 완료",
    priority: "높은 중요도",
    tone: "blue",
  },
  {
    time: "11:21:18",
    source: "Drive",
    title: "ORION_PRD_v2.docx 수정됨",
    detail: "문서 내용 변경 감지",
    meta: "Drive · ORION / 기획 문서",
    status: "분석 중",
    priority: "중간 중요도",
    tone: "green",
  },
  {
    time: "11:15:42",
    source: "Calendar",
    title: "주간 프로젝트 회의",
    detail: "새 이벤트 생성",
    meta: "Calendar · 2026.05.07 (목) 10:00",
    status: "분석 완료",
    priority: "낮은 중요도",
    tone: "orange",
  },
  {
    time: "11:08:27",
    source: "Slack",
    title: "#backend-team 새 메시지",
    detail: "API 성능 개선 관련 논의",
    meta: "Slack · #backend-team · 참여자 4명",
    status: "미분석",
    priority: "중간 중요도",
    tone: "purple",
  },
  {
    time: "10:55:12",
    source: "Gmail",
    title: "결제 요청: 보안 이슈 대응",
    detail: "이메일 스레드 수집 완료 (5개 메시지)",
    meta: "Gmail · 보안 이슈",
    status: "분석 중",
    priority: "높은 중요도",
    tone: "blue",
  },
  {
    time: "10:42:05",
    source: "Drive",
    title: "보안 점검 결과 보고서.pdf 업로드",
    detail: "새 파일 업로드",
    meta: "Drive · /보안/2026/05",
    status: "미분석",
    priority: "낮은 중요도",
    tone: "green",
  },
  {
    time: "10:33:18",
    source: "Slack",
    title: "#general 새 메시지",
    detail: "일반 공지사항",
    meta: "Slack · #general · 참여자 23명",
    status: "분석 완료",
    priority: "낮은 중요도",
    tone: "purple",
  },
];

const reviewRows = [
  ["프로젝트 ORION 요구사항 변경 검토", "문서", "이준호", "2026.05.07", "D-2", "대기 중", "높음"],
  ["신규 보안 정책(안) 검토 요청", "정책", "박지은", "2026.05.07", "D-4", "대기 중", "보통"],
  ["FY26 2분기 OKR 초안 검토", "의사결정", "정민철", "2026.05.06", "D-1", "검토 중", "높음"],
  ["고객 데이터 처리 절차 문서 검토", "문서", "최유리", "2026.05.05", "D-3", "대기 중", "보통"],
];

export default async function DashboardPage() {
  const [dashboard, agentRuns] = await Promise.all([
    serverApiGet<DashboardResponse>("/api/v1/dashboard").catch(() => FALLBACK_DASHBOARD),
    serverApiGet<AgentRunsResponse>("/api/v1/agent-runs").catch(() => FALLBACK_AGENT_RUNS),
  ]);

  const counts = dashboard.source_counts || FALLBACK_DASHBOARD.source_counts;
  const totalSources = counts.slack + counts.gmail + counts.drive + counts.calendar + counts.other;
  const pendingReviewCount = dashboard.pending_review_count || FALLBACK_DASHBOARD.pending_review_count;

  return (
    <div className="reference-dashboard">
      <section className="page-heading reference-heading">
        <div>
          <h1>대시보드</h1>
          <p>연결된 채널에서 수집되는 모든 활동을 실시간으로 확인하세요.</p>
        </div>
      </section>

      <section className="source-card-grid">
        {sourceCards.map((card) => {
          const value = card.key === "all" ? totalSources : counts[card.key as keyof typeof counts] || card.value;
          return <SourceMetric key={card.label} card={{ ...card, value }} />;
        })}
      </section>

      <section className="reference-grid">
        <div className="reference-main">
          <Panel className="activity-panel-large">
            <div className="activity-toolbar">
              <div>
                <h2>실시간 활동 스트림</h2>
                <div className="filter-pills">
                  <span className="active">전체 <b>{totalSources}</b></span>
                  <span>미분석 <b>86</b></span>
                  <span>분석 중 <b>32</b></span>
                  <span>분석 완료 <b>130</b></span>
                </div>
              </div>
              <div className="toolbar-actions">
                <button type="button">
                  <Pause className="h-4 w-4" aria-hidden="true" />
                  일시 정지
                </button>
                <button type="button">
                  <Settings className="h-4 w-4" aria-hidden="true" />
                  스트림 설정
                </button>
              </div>
            </div>
            <div className="activity-stream">
              {activities.map((item) => (
                <ActivityRow key={`${item.time}-${item.title}`} item={item} />
              ))}
            </div>
            <div className="dashboard-pagination">
              <span>1-20 / {totalSources}</span>
              <span className="pager">‹ 1 2 3 ··· 13 ›</span>
            </div>
          </Panel>

          <Panel className="review-panel">
            <div className="panel-header compact">
              <PanelTitle title="검토 우선순위" count={`${pendingReviewCount}건`} />
              <Link href="/review" className="text-link">
                전체 검토 보기
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="review-table">
              <div className="review-table-head">
                <span>제목</span>
                <span>유형</span>
                <span>요청자</span>
                <span>요청일</span>
                <span>마감</span>
                <span>상태</span>
                <span>우선순위</span>
              </div>
              {reviewRows.map((row) => (
                <div className="review-table-row" key={row[0]}>
                  {row.map((cell, index) => (
                    <span key={`${row[0]}-${cell}`} className={index >= 4 ? "strong-cell" : ""}>
                      {cell}
                    </span>
                  ))}
                </div>
              ))}
            </div>
          </Panel>
        </div>

        <aside className="reference-aside">
          <Panel>
            <div className="side-title">
              <h2>활동 요약 (실시간)</h2>
              <span>업데이트: 11:45:30</span>
            </div>
            <div className="side-summary">
              <div>
                <strong>{totalSources}</strong>
                <span>총 활동</span>
              </div>
              <MiniBars />
            </div>
            <Legend rows={[["미분석", 86, "35%", "purple"], ["분석 중", 32, "13%", "blue"], ["분석 완료", 130, "52%", "green"]]} />
          </Panel>

          <Panel>
            <PanelTitle title="활동 소스별 현황" />
            <SourceBar label="Slack" value={counts.slack} percent="52%" tone="purple" />
            <SourceBar label="Gmail" value={counts.gmail} percent="25%" tone="blue" />
            <SourceBar label="Google Drive" value={counts.drive} percent="14%" tone="green" />
            <SourceBar label="Google Calendar" value={counts.calendar} percent="7%" tone="orange" />
            <SourceBar label="기타" value={counts.other} percent="2%" tone="gray" />
          </Panel>

          <Panel>
            <PanelTitle title="주요 키워드 (실시간)" />
            <div className="keyword-cloud">
              {["#project-orion 24", "보안 18", "API 15", "결재 12", "Oracle DB 10", "요구사항 8", "변경 8", "백엔드 6"].map((keyword) => (
                <span key={keyword}>{keyword}</span>
              ))}
            </div>
          </Panel>

          <Panel>
            <div className="side-title">
              <h2>에이전트 요약</h2>
              <Link href="/agent-runs">전체보기</Link>
            </div>
            <div className="agent-cost-line">
              <span>총 실행</span>
              <strong>{agentRuns.total_runs.toLocaleString()}회</strong>
            </div>
            <div className="agent-cost-line">
              <span>예상 비용</span>
              <strong>${agentRuns.estimated_cost_usd.toFixed(2)}</strong>
            </div>
            <Link href="/search" className="primary-action">
              <Bot className="h-4 w-4" aria-hidden="true" />
              Ask 워크스페이스로 이동
            </Link>
          </Panel>
        </aside>
      </section>
    </div>
  );
}

function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`panel reference-panel ${className}`}>{children}</section>;
}

function PanelTitle({ title, count }: { title: string; count?: string }) {
  return (
    <div className="reference-panel-title">
      <h2>{title}</h2>
      {count ? <span>{count}</span> : null}
    </div>
  );
}

function SourceMetric({ card }: { card: (typeof sourceCards)[number] }) {
  const Icon = card.icon;
  return (
    <article className="source-metric-card">
      <div>
        <span className={`source-logo ${card.tone}`}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <strong>{card.label}</strong>
      </div>
      <b>{card.value}</b>
      <p>{card.detail}</p>
    </article>
  );
}

function ActivityRow({ item }: { item: (typeof activities)[number] }) {
  const statusTone = item.status === "분석 완료" ? "green" : item.status === "분석 중" ? "blue" : "violet";
  const priorityTone = item.priority.startsWith("높은") ? "danger" : item.priority.startsWith("중간") ? "warning" : "success";
  return (
    <article className="activity-row">
      <time>{item.time}</time>
      <span className={`activity-line-dot ${item.tone}`} />
      <span className={`source-logo ${item.tone}`}>{item.source.slice(0, 1)}</span>
      <div>
        <h3>{item.title}</h3>
        <p>{item.detail}</p>
        <small>{item.meta}</small>
      </div>
      <span className={`badge ${statusTone}`}>{item.status}</span>
      <span className={`priority-badge ${priorityTone}`}>{item.priority}</span>
    </article>
  );
}

function MiniBars() {
  return (
    <div className="mini-bars" aria-hidden="true">
      {[34, 52, 46, 68, 42, 88, 54, 96].map((height, index) => (
        <span key={index} style={{ height: `${height}%` }} />
      ))}
    </div>
  );
}

function Legend({ rows }: { rows: [string, number, string, string][] }) {
  return (
    <div className="legend-list">
      {rows.map(([label, value, percent, tone]) => (
        <div key={label}>
          <span className={`legend-dot ${tone}`} />
          <span>{label}</span>
          <strong>{value}</strong>
          <em>({percent})</em>
        </div>
      ))}
    </div>
  );
}

function SourceBar({ label, value, percent, tone }: { label: string; value: number; percent: string; tone: string }) {
  return (
    <div className="source-bar-row">
      <span>{label}</span>
      <div>
        <i className={tone} style={{ width: percent }} />
      </div>
      <strong>{value}</strong>
      <em>({percent})</em>
    </div>
  );
}
