import {
  AlertTriangle,
  ArrowRight,
  Bell,
  Bot,
  Brain,
  CheckCircle2,
  FileCheck2,
  FileText,
  Inbox,
  Mail,
  MessageSquare,
  Plus,
  ShieldCheck,
  Workflow,
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
  total_runs: 286,
  total_tokens: 1240000,
  estimated_cost_usd: 124.58,
  recent_runs: [],
};

const workflowSteps = [
  { label: "수집됨", value: 128, detail: "오늘 9:15 기준", icon: Workflow, tone: "blue" },
  { label: "분석 완료", value: 26, detail: "어제 대비 +6", icon: Brain, tone: "violet" },
  { label: "검토 대기", value: 12, detail: "높은 우선순위 3건", icon: Inbox, tone: "red" },
  { label: "승인 완료", value: 8, detail: "어제 대비 +2", icon: CheckCircle2, tone: "green" },
  { label: "지식으로 저장됨", value: 8, detail: "전체 지식 1,248개", icon: ShieldCheck, tone: "blue" },
];

const criticalItems = [
  { title: "검토 대기", value: "12건", detail: "오늘 마감 18:00", action: "검토하러 가기", icon: AlertTriangle, tone: "red" },
  { title: "높은 신뢰도 의사결정 후보", value: "3건", detail: "신뢰도 80% 이상", action: "확인하기", icon: ShieldCheck, tone: "orange" },
  { title: "위험/지연 감지", value: "2건", detail: "즉시 확인 필요", action: "상세 보기", icon: AlertTriangle, tone: "yellow" },
  { title: "실패한 에이전트 실행", value: "1건", detail: "재실행 필요", action: "확인하기", icon: Bot, tone: "violet" },
  { title: "새 알림", value: "3건", detail: "읽지 않은 알림", action: "알림 보기", icon: Bell, tone: "blue" },
];

const reviewRows = [
  {
    title: "Oracle DB 채택 결정",
    summary: "MSSQL 대신 Oracle DB를 선택한 결정에 대한 근거가 감지되었습니다.",
    type: "의사결정",
    confidence: "87%",
    evidence: "근거 15개",
    source: "Project Orion · 2026.04.30 · Slack",
    tone: "violet",
  },
  {
    title: "결제 모듈 보안 이슈 대응",
    summary: "결제 모듈 보안 취약점 발견 및 대응 과정이 기록되었습니다.",
    type: "히스토리",
    confidence: "82%",
    evidence: "근거 9개",
    source: "Project Pay · 2026.04.29 · Gmail",
    tone: "green",
  },
  {
    title: "API 성능 개선 배포",
    summary: "v2.1.0 배포 및 성능 개선 작업이 감지되었습니다.",
    type: "타임라인",
    confidence: "78%",
    evidence: "근거 6개",
    source: "Project Orion · 2026.04.29 · GitHub",
    tone: "blue",
  },
  {
    title: "테스트 환경 구성 문서화",
    summary: "테스트 환경 구성 문서화가 필요하다는 논의가 감지되었습니다.",
    type: "할 일 후보",
    confidence: "65%",
    evidence: "근거 5개",
    source: "Project Pay · 2026.04.28 · Slack",
    tone: "orange",
  },
];

const liveActivity = [
  { time: "11:42", title: "#project-orion 스레드 수집", detail: "새로운 메시지 12개", icon: MessageSquare },
  { time: "11:31", title: "FW: Oracle DB 선정 이유", detail: "이메일 스레드 수집", icon: Mail },
  { time: "11:21", title: "ORION_PRD_v2.docx 수정됨", detail: "Google Drive 변경 감지", icon: FileText },
  { time: "11:15", title: "주간 프로젝트 회의", detail: "일정 이벤트 수집", icon: FileCheck2 },
];

const agents = [
  { name: "Slack Agent", rate: "98%", runs: 24, icon: MessageSquare },
  { name: "Mail/Docs Agent", rate: "96%", runs: 18, icon: Mail },
  { name: "RAG Orchestrator", rate: "95%", runs: 12, icon: Brain },
];

const insights = [
  { title: "중요 의사결정 감지", body: "Oracle DB 도입 결정", tone: "green" },
  { title: "위험 감지", body: "결제 모듈 보안 취약점", tone: "orange" },
  { title: "트렌드", body: "API 성능 개선 추세", tone: "blue" },
];

export default async function DashboardPage() {
  const [dashboard, agentRuns] = await Promise.all([
    serverApiGet<DashboardResponse>("/api/v1/dashboard").catch(() => FALLBACK_DASHBOARD),
    serverApiGet<AgentRunsResponse>("/api/v1/agent-runs").catch(() => FALLBACK_AGENT_RUNS),
  ]);
  const pendingReviewCount = dashboard.pending_review_count || FALLBACK_DASHBOARD.pending_review_count;

  return (
    <div className="reference-dashboard">
      <section className="page-heading reference-heading">
        <div>
          <h1>안녕하세요, 김하나님 👋</h1>
          <p>AI가 수집하고 분석한 오늘의 업무 인사이트입니다. 중요한 항목을 먼저 확인해보세요.</p>
        </div>
      </section>

      <section className="reference-grid">
        <div className="reference-main">
          <Panel className="workflow-panel">
            <PanelTitle title="오늘의 업무 흐름" />
            <div className="workflow-steps">
              {workflowSteps.map((step, index) => (
                <WorkflowStep key={step.label} step={step} showArrow={index < workflowSteps.length - 1} />
              ))}
            </div>
          </Panel>

          <Panel>
            <PanelTitle title="오늘 반드시 확인할 항목" count="5건" />
            <div className="critical-grid">
              {criticalItems.map((item) => (
                <CriticalCard key={item.title} item={item} />
              ))}
            </div>
          </Panel>

          <Panel className="review-panel">
            <div className="panel-header compact">
              <PanelTitle title="검토 사항" count={`${pendingReviewCount}건`} />
              <Link href="/review" className="text-link">
                전체 검토 사항 보기
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="dashboard-review-list">
              {reviewRows.map((row) => (
                <ReviewRow key={row.title} row={row} />
              ))}
            </div>
            <div className="dashboard-pagination">
              <span>총 {pendingReviewCount}개 항목</span>
              <span>1-4 / {pendingReviewCount}</span>
            </div>
          </Panel>

          <Panel>
            <div className="insight-header">
              <PanelTitle title="AI 인사이트" />
              <span>오늘의 주요 인사이트입니다.</span>
            </div>
            <div className="insight-grid">
              {insights.map((insight) => (
                <InsightCard key={insight.title} insight={insight} />
              ))}
              <Link href="/search" className="more-insight">
                <Plus className="h-7 w-7" aria-hidden="true" />
                <strong>더 많은 인사이트</strong>
                <span>모든 인사이트 보기</span>
              </Link>
            </div>
          </Panel>
        </div>

        <aside className="reference-aside">
          <Panel>
            <div className="panel-header compact">
              <PanelTitle title="실시간 활동" />
              <Link href="/messages" className="text-link">
                전체 보기
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="side-activity-list">
              {liveActivity.map((item) => (
                <SideActivity key={`${item.time}-${item.title}`} item={item} />
              ))}
            </div>
            <div className="connection-status">
              <span className="status-dot" />
              연결 상태: 모든 연동 정상
            </div>
          </Panel>

          <Panel>
            <div className="panel-header compact">
              <PanelTitle title="에이전트 실행 요약" />
              <Link href="/agent-runs" className="text-link">
                전체 보기
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="agent-summary-list">
              {agents.map((agent) => (
                <AgentSummary key={agent.name} agent={agent} />
              ))}
            </div>
            <div className="agent-cost-line">
              <span>예상 비용</span>
              <strong>${agentRuns.estimated_cost_usd.toFixed(2)}</strong>
            </div>
          </Panel>

          <Panel>
            <div className="panel-header compact">
              <PanelTitle title="빠른 Ask" />
              <Link href="/search" className="text-link">
                Ask 워크스페이스로 이동
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="quick-ask-box">무엇이든 질문해보세요</div>
            <div className="quick-prompts">
              <span>Oracle DB 선택 이유는?</span>
              <span>지난 주 배포 내역 요약해줘</span>
              <span>결제 모듈 보안 이슈 대응 과정은?</span>
            </div>
            <Link href="/search" className="send-ask" aria-label="Ask로 이동">
              <Bot className="h-4 w-4" aria-hidden="true" />
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

function WorkflowStep({ step, showArrow }: { step: (typeof workflowSteps)[number]; showArrow: boolean }) {
  const Icon = step.icon;
  return (
    <>
      <article className="workflow-step">
        <span className={`workflow-icon ${step.tone}`}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <p>{step.label}</p>
          <strong>{step.value}</strong>
          <span>{step.detail}</span>
        </div>
      </article>
      {showArrow ? <ArrowRight className="workflow-arrow h-5 w-5" aria-hidden="true" /> : null}
    </>
  );
}

function CriticalCard({ item }: { item: (typeof criticalItems)[number] }) {
  const Icon = item.icon;
  return (
    <article className={`critical-card ${item.tone}`}>
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4" aria-hidden="true" />
        <span>{item.title}</span>
      </div>
      <strong>{item.value}</strong>
      <p>{item.detail}</p>
      <Link href="/review">
        {item.action}
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Link>
    </article>
  );
}

function ReviewRow({ row }: { row: (typeof reviewRows)[number] }) {
  return (
    <article className="dashboard-review-row">
      <span className={`review-icon ${row.tone}`}>
        <ShieldCheck className="h-4 w-4" aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3>{row.title}</h3>
          <span className={`mini-badge ${row.tone}`}>{row.type}</span>
        </div>
        <p>{row.summary}</p>
        <small>{row.source}</small>
      </div>
      <div className="row-metric">
        <span>신뢰도</span>
        <strong>{row.confidence}</strong>
      </div>
      <div className="row-metric evidence">
        <span>{row.evidence}</span>
      </div>
      <Link href="/review" className="row-action">
        검토
      </Link>
    </article>
  );
}

function SideActivity({ item }: { item: (typeof liveActivity)[number] }) {
  const Icon = item.icon;
  return (
    <article className="side-activity-row">
      <time>{item.time}</time>
      <Icon className="h-5 w-5 text-[var(--primary)]" aria-hidden="true" />
      <div>
        <h3>{item.title}</h3>
        <p>{item.detail}</p>
      </div>
    </article>
  );
}

function AgentSummary({ agent }: { agent: (typeof agents)[number] }) {
  const Icon = agent.icon;
  return (
    <article className="agent-summary-row">
      <Icon className="h-6 w-6 text-[var(--primary)]" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <h3>{agent.name}</h3>
        <p>최근 실행: 5분 전</p>
      </div>
      <div>
        <span>성공률</span>
        <strong>{agent.rate}</strong>
      </div>
      <div>
        <span>오늘 실행</span>
        <strong>{agent.runs}</strong>
      </div>
    </article>
  );
}

function InsightCard({ insight }: { insight: (typeof insights)[number] }) {
  return (
    <article className={`insight-card ${insight.tone}`}>
      <strong>{insight.title}</strong>
      <p>{insight.body}</p>
      <Link href="/search">
        자세히 보기
        <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
      </Link>
    </article>
  );
}
