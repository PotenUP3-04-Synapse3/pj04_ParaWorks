import { Activity, Database, ShieldAlert } from "lucide-react";
import { apiGet } from "@/lib/api/client";
import type { DashboardResponse } from "@/lib/api/types";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const dashboard = await apiGet<DashboardResponse>("/api/v1/dashboard");
  const totalSources = Object.values(dashboard.source_counts).reduce((sum, count) => sum + count, 0);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-muted">Overview</p>
        <h2 className="mt-1 text-2xl font-semibold tracking-normal">Dashboard</h2>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-md border border-line bg-white p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted">Sources</span>
            <Database className="h-4 w-4 text-muted" aria-hidden="true" />
          </div>
          <p className="mt-3 text-3xl font-semibold">{totalSources}</p>
        </div>
        <div className="rounded-md border border-line bg-white p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted">Pending Review</span>
            <ShieldAlert className="h-4 w-4 text-muted" aria-hidden="true" />
          </div>
          <p className="mt-3 text-3xl font-semibold">{dashboard.pending_review_count}</p>
        </div>
        <div className="rounded-md border border-line bg-white p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted">Recent Jobs</span>
            <Activity className="h-4 w-4 text-muted" aria-hidden="true" />
          </div>
          <p className="mt-3 text-3xl font-semibold">{dashboard.recent_jobs.length}</p>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3">
            <h3 className="text-sm font-semibold">Recent Sync Jobs</h3>
          </div>
          <div className="divide-y divide-line">
            {dashboard.recent_jobs.map((job) => (
              <div key={job.job_id} className="grid gap-3 px-4 py-3 sm:grid-cols-[1fr_110px_90px]">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{job.job_id}</p>
                  <p className="text-sm text-muted">{job.message}</p>
                </div>
                <span className="text-sm capitalize text-muted">{job.connector_type}</span>
                <span className="text-sm font-medium capitalize">{job.status}</span>
              </div>
            ))}
            {dashboard.recent_jobs.length === 0 ? (
              <p className="px-4 py-8 text-sm text-muted">No sync jobs have run yet.</p>
            ) : null}
          </div>
        </div>

        <div className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3">
            <h3 className="text-sm font-semibold">Sources by Type</h3>
          </div>
          <div className="divide-y divide-line">
            {Object.entries(dashboard.source_counts).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between px-4 py-3">
                <span className="text-sm font-medium capitalize">{type}</span>
                <span className="text-sm text-muted">{count}</span>
              </div>
            ))}
            {Object.keys(dashboard.source_counts).length === 0 ? (
              <p className="px-4 py-8 text-sm text-muted">No sources are indexed.</p>
            ) : null}
          </div>
        </div>
      </section>
    </div>
  );
}
