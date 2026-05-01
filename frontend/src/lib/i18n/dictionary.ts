export type Locale = "ko" | "en";

export const dictionaries = {
  ko: {
    shell: {
      subtitle: "데모 하네스",
      dashboard: "대시보드",
      integrations: "연동",
      messages: "메신저",
      review: "검토",
      search: "검색",
      language: "언어",
      korean: "한국어",
      english: "English",
    },
    messages: {
      eyebrow: "팀 메신저",
      title: "메신저",
      channels: "채널",
      recentActivity: "최근 활동",
      composerLabel: "메시지 작성",
      composerPlaceholder: "메시지를 입력하세요",
      send: "전송",
      sending: "전송 중",
      empty: "이 채널에는 아직 메시지가 없습니다.",
      loadError: "메시지를 불러오지 못했습니다.",
      sendError: "메시지를 전송하지 못했습니다.",
    },
  },
  en: {
    shell: {
      subtitle: "Demo Harness",
      dashboard: "Dashboard",
      integrations: "Integrations",
      messages: "Messenger",
      review: "Review",
      search: "Search",
      language: "Language",
      korean: "한국어",
      english: "English",
    },
    messages: {
      eyebrow: "Team messenger",
      title: "Messenger",
      channels: "Channels",
      recentActivity: "Recent activity",
      composerLabel: "Write a message",
      composerPlaceholder: "Type a message",
      send: "Send",
      sending: "Sending",
      empty: "This channel has no messages yet.",
      loadError: "Could not load messages.",
      sendError: "Could not send message.",
    },
  },
} as const;

export type Dictionary = (typeof dictionaries)[Locale];
