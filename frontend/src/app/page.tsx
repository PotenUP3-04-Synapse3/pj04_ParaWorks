import { redirect } from "next/navigation";

/**
 * 홈페이지 접속 시 기본 페이지인 대시보드로 리다이렉트합니다.
 */
export default function HomePage() {
  redirect("/dashboard");
}
