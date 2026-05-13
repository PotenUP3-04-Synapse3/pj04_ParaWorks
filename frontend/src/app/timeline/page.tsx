"use client";

import { ExternalLink, FileClock, GitBranch, X } from "lucide-react";
import { useMemo, useState } from "react";

type TimelineHistory = {
  id: string;
  time: string;
  source: "Slack" | "Gmail" | "Drive" | "Calendar";
  title: string;
  summary: string;
  history: string;
  status: "검토 필요" | "분석 중" | "분석 완료";
  sourceUrl: string;
  slackMessages: { author: string; body: string; time: string }[];
};

type ProjectTimeline = {
  id: string;
  name: string;
  histories: TimelineHistory[];
};

const projectTimelineSeedData: ProjectTimeline[] = [
  {
    id: "orion",
    name: "프로젝트 ORION",
    histories: [
      {
        id: "orion-requirement-change",
        time: "11:42",
        source: "Slack",
        title: "#project-orion 요구사항 변경 논의",
        summary: "고객사가 리포트 권한 분리와 감사 로그 보존 기간 확대를 요청했고, 일정 영향이 있는 변경으로 분류되었습니다.",
        history: "요구사항 변경안은 이번 주 검토사항에서 승인 여부를 결정하고, 승인 후 고객사 공유본에 반영합니다.",
        status: "검토 필요",
        sourceUrl: "paraworks://slack/project-orion/1746940920.000100",
        slackMessages: [
          { author: "김하나", time: "11:39", body: "고객사가 관리자 리포트 권한을 더 세분화해 달라고 요청했습니다." },
          { author: "이준호", time: "11:41", body: "권한 모델 변경이 필요해서 API 일정에 영향이 있습니다. 오늘 안에 영향 범위를 정리하겠습니다." },
          { author: "박지은", time: "11:42", body: "감사 로그 보존 기간도 같이 확인해야 합니다. 제한 권한 근거로 묶어 주세요." },
        ],
      },
      {
        id: "orion-db-selection",
        time: "11:31",
        source: "Gmail",
        title: "Oracle DB 선정 이유 메일 스레드",
        summary: "운영 안정성, 기존 라이선스, 장애 대응 경험을 이유로 Oracle DB 유지 의견이 우세했습니다.",
        history: "DB 선정 근거는 고객사 설명 자료에 들어갈 수 있도록 출처 메일과 함께 보존합니다.",
        status: "분석 완료",
        sourceUrl: "paraworks://gmail/thread/orion-db-selection",
        slackMessages: [
          { author: "정민철", time: "11:25", body: "메일 스레드 기준으로는 Oracle 유지가 가장 방어 가능한 선택입니다." },
          { author: "이준호", time: "11:28", body: "운영팀 장애 대응 경험까지 같이 적으면 근거가 더 명확합니다." },
        ],
      },
      {
        id: "orion-prd-update",
        time: "11:21",
        source: "Drive",
        title: "ORION_PRD_v2.docx 수정",
        summary: "PRD 2판에 권한 분리 요구사항과 고객사 공유 일정이 추가되었습니다.",
        history: "문서 버전, revision id, 변경 스니펫을 묶어 이후 RAG 답변 근거로 사용합니다.",
        status: "분석 중",
        sourceUrl: "paraworks://drive/orion-prd-v2",
        slackMessages: [
          { author: "최유리", time: "11:19", body: "PRD v2에 권한 분리 요구사항을 반영했습니다." },
          { author: "김하나", time: "11:21", body: "좋습니다. 고객 공유본에는 변경 사유도 같이 남겨 주세요." },
        ],
      },
      {
        id: "orion-calendar-check",
        time: "09:40",
        source: "Calendar",
        title: "고객사 공유 일정 확인",
        summary: "고객사 공유 회의 시간이 잡혔지만 아직 요약 가능한 대화 히스토리는 연결되지 않았습니다.",
        history: "",
        status: "분석 중",
        sourceUrl: "paraworks://calendar/orion-customer-share",
        slackMessages: [],
      },
    ],
  },
  {
    id: "nova",
    name: "Nova 보안 정책",
    histories: [
      {
        id: "nova-policy-review",
        time: "10:55",
        source: "Slack",
        title: "#security 정책 초안 리뷰",
        summary: "개인정보 접근 로그와 관리자 권한 변경 알림이 정책 초안의 핵심 검토 항목으로 올라왔습니다.",
        history: "보안 정책 초안은 제한 권한 근거를 유지한 채 리뷰어 승인 후 전사 공지로 이동합니다.",
        status: "검토 필요",
        sourceUrl: "paraworks://slack/security/1746938100.000200",
        slackMessages: [
          { author: "박지은", time: "10:51", body: "관리자 권한 변경은 알림과 감사 로그가 모두 필요합니다." },
          { author: "정민철", time: "10:54", body: "정책 초안에 제한 권한 근거를 붙여서 검토사항으로 보내겠습니다." },
        ],
      },
    ],
  },
  {
    id: "atlas",
    name: "Atlas API 개선",
    histories: [
      {
        id: "atlas-cache-policy",
        time: "10:33",
        source: "Slack",
        title: "#backend-team 캐시 정책 논의",
        summary: "검색 응답 지연을 줄이기 위해 권한 필터 이후 캐시하는 방향으로 의견이 모였습니다.",
        history: "캐시 정책은 권한 누출 가능성을 검토한 뒤 성능 개선 작업에 반영합니다.",
        status: "분석 완료",
        sourceUrl: "paraworks://slack/backend-team/1746936780.000300",
        slackMessages: [
          { author: "이준호", time: "10:29", body: "권한 필터 전 캐시는 위험합니다. 필터 후 결과만 캐시해야 합니다." },
          { author: "김하나", time: "10:33", body: "그 방향으로 릴리스 노트에 보안 근거를 남기겠습니다." },
        ],
      },
    ],
  },
];

const projectTimelines: ProjectTimeline[] = [];

export default function TimelinePage() {
  const [selectedProjectId, setSelectedProjectId] = useState(projectTimelines[0]?.id ?? "");
  const selectedProject = useMemo(
    () => projectTimelines.find((project) => project.id === selectedProjectId) ?? projectTimelines[0],
    [selectedProjectId],
  );
  const [selectedHistoryId, setSelectedHistoryId] = useState<string | undefined>();
  if (!selectedProject) {
    return (
      <div className="reference-dashboard space-y-4">
        <section className="page-heading reference-heading">
          <div>
            <p className="text-[13px] font-bold text-[var(--primary-dark)]">Timeline</p>
            <h1>타임라인</h1>
            <p>Slack 또는 Google을 연동하면 실제 근거에서 생성된 타임라인이 표시됩니다.</p>
          </div>
          <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold">
            <GitBranch className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
            0개 히스토리
          </div>
        </section>
      </div>
    );
  }
  const selectedHistory = selectedProject.histories.find((history) => history.id === selectedHistoryId);

  return (
    <div className="reference-dashboard space-y-4">
      <section className="page-heading reference-heading">
        <div>
          <p className="text-[13px] font-bold text-[var(--primary-dark)]">Timeline</p>
          <h1>타임라인</h1>
          <p>메일, Slack, 문서, 캘린더 근거에서 검토를 통과한 주요 사건을 시간 흐름으로 모읍니다.</p>
        </div>
        <div className="panel inline-flex h-fit w-fit items-center gap-2 px-4 py-3 text-[13px] font-bold">
          <GitBranch className="h-4 w-4 text-[var(--primary)]" aria-hidden="true" />
          {selectedProject.histories.length.toLocaleString()}개 히스토리
        </div>
      </section>

      <nav className="panel reference-panel flex gap-2 overflow-x-auto p-2" aria-label="프로젝트 선택">
        {projectTimelines.map((project) => (
          <button
            key={project.id}
            type="button"
            aria-pressed={project.id === selectedProjectId}
            className={`shrink-0 rounded-md px-3 py-2 text-left text-[13px] font-extrabold transition ${
              project.id === selectedProjectId
                ? "bg-[var(--primary)] text-white shadow-sm ring-2 ring-[var(--primary-soft)]"
                : "bg-[var(--glass-elevated)] text-ink hover:bg-[var(--glass-strong)]"
            }`}
            onClick={() => {
              setSelectedProjectId(project.id);
              setSelectedHistoryId(undefined);
            }}
          >
            {project.name}
          </button>
        ))}
      </nav>

      <section
        className={`timeline-history-layout ${selectedHistory ? "history-open" : ""}`}
      >
        <article className="panel reference-panel">
          <div className="border-b border-line pb-4">
            <h2 className="text-[16px] font-extrabold text-ink">{selectedProject.name} 타임라인</h2>
            <p className="mt-1 text-[13px] text-muted">각 사건의 히스토리 아이콘을 누르면 해당 근거 요약과 원문 흐름을 확인합니다.</p>
          </div>

          <div className="mt-4 space-y-3">
            {selectedProject.histories.map((item) => (
              <article key={item.id} className="rounded-lg border border-line bg-[var(--glass-elevated)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <time className="text-[12px] font-extrabold text-muted">{item.time}</time>
                    <span className="badge blue">{item.source}</span>
                    <span className={`badge ${item.status === "분석 완료" ? "green" : item.status === "분석 중" ? "blue" : "violet"}`}>
                      {item.status}
                    </span>
                  </div>
                  <button
                    type="button"
                    aria-pressed={selectedHistoryId === item.id}
                    className={`icon-button small ${selectedHistoryId === item.id ? "active" : ""}`}
                    aria-label={`${item.title} 히스토리 보기`}
                    onClick={() => setSelectedHistoryId((current) => (current === item.id ? undefined : item.id))}
                  >
                    <FileClock className="h-4 w-4" aria-hidden="true" />
                  </button>
                </div>
                <h3 className="mt-3 text-[15px] font-extrabold text-ink">{item.title}</h3>
                <p className="mt-1 text-[13px] leading-6 text-muted">{item.summary}</p>
                <div className="mt-3 rounded-md bg-surface-soft px-3 py-2 text-[12px] font-bold leading-5 text-muted">
                  히스토리: {item.history || "표시할 히스토리가 없습니다."}
                </div>
              </article>
            ))}
          </div>
        </article>

        {selectedHistory ? (
          <aside className="panel reference-panel timeline-history-panel h-fit">
            <div className="flex items-start justify-between gap-3 border-b border-line pb-4">
              <div>
                <p className="text-[12px] font-bold text-[var(--primary-dark)]">{selectedHistory.source} 히스토리</p>
                <h2 className="mt-1 text-[16px] font-extrabold text-ink">{selectedHistory.title}</h2>
              </div>
              <button type="button" className="icon-button small" aria-label="히스토리 닫기" onClick={() => setSelectedHistoryId(undefined)}>
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            <p className="mt-4 text-[13px] leading-6 text-muted">
              {selectedHistory.history || "표시할 히스토리가 없습니다. 연결된 대화나 문서 요약이 생기면 이곳에 표시됩니다."}
            </p>

            {selectedHistory.slackMessages.length > 0 ? (
              <div className="mt-4 space-y-3">
                {selectedHistory.slackMessages.map((message) => (
                  <div key={`${message.time}-${message.author}`} className="rounded-lg border border-line bg-surface-soft p-3">
                    <div className="flex items-center justify-between gap-2 text-[12px] font-bold text-muted">
                      <span>{message.author}</span>
                      <span>{message.time}</span>
                    </div>
                    <p className="mt-2 text-[13px] leading-6 text-ink">{message.body}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-4 rounded-lg border border-dashed border-line bg-surface-soft p-4 text-[13px] text-muted">
                표시할 원문 대화가 없습니다.
              </div>
            )}

            <a
              href={selectedHistory.sourceUrl}
              className="mt-4 inline-flex items-center gap-2 text-[12px] font-extrabold text-[var(--primary-dark)] underline-offset-4 hover:underline"
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              원문 열기
            </a>
          </aside>
        ) : null}
      </section>
    </div>
  );
}
