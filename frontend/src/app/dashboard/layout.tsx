import Sidebar from '@/components/Sidebar';
import type { Metadata } from 'next';

export const metadata: Metadata = { title: 'ParaWorks' };

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 bg-gray-50">{children}</main>
    </div>
  );
}
