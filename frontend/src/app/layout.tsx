import type { Metadata } from "next";
import { AppShell } from "@/components/layout/AppShell";
import "./globals.css";

/**
 * 어플리케이션의 메타데이터 설정 (SEO 및 브라우저 탭 제목)
 */
export const metadata: Metadata = {
  title: "Paraworks Company Memory",
  description: "AI-powered enterprise company memory dashboard",
};

/**
 * RootLayout 컴포넌트: 모든 페이지를 감싸는 최상위 레이아웃입니다.
 * HTML 구조를 정의하고, 테마 강제 설정 스크립트 및 AppShell을 포함합니다.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body>
        {/* 테마를 항상 'light'로 고정하기 위한 초기화 스크립트 (깜빡임 방지) */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
try {
  document.documentElement.dataset.theme = 'light';
  localStorage.setItem('paraworks-theme', 'light');
} catch (_) {
  document.documentElement.dataset.theme = 'light';
}
`,
          }}
        />
        {/* 공통 UI 레이아웃인 AppShell로 자식 요소들을 래핑 */}
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
