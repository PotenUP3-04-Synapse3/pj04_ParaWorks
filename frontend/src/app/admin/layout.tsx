import Sidebar from '@/components/Sidebar';
import { Header } from '@/components/layout/Header';
import type { Metadata } from 'next';
export const metadata: Metadata = { title: 'ParaWorks — 관리자' };
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col min-w-0">
        <Header />
        <main className="flex-1 bg-gray-50">{children}</main>
      </div>
    </div>
  );
}
