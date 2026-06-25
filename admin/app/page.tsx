"use client";

import {useQuery} from "@tanstack/react-query";
import {api} from "@/lib/api";
import {EmptyState, ErrorState, LoadingState, Status} from "@/components/query-state";

type Dashboard = {
  volume: number; queue_depth: number; retries: number; dlq: number;
  status_counts: Record<string, number>; channel_counts: Record<string, number>;
  provider_health: {channel: string; name: string; health: string; active: boolean}[];
};

export default function DashboardPage() {
  const query = useQuery({queryKey: ["dashboard"], queryFn: () => api<Dashboard>("/api/v1/operations/dashboard")});
  return <>
    <header className="page-header"><div><h1>Delivery overview</h1><p>Queue pressure, delivery outcomes, and provider health at a glance.</p></div></header>
    {query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} /> : query.data ? <>
      <section className="grid metric-grid" aria-label="Key delivery metrics">
        <div className="card metric"><div className="metric-label">Notification volume</div><div className="metric-value">{query.data.volume.toLocaleString()}</div><div className="metric-note">All recorded states</div></div>
        <div className="card metric"><div className="metric-label">Queue depth</div><div className="metric-value">{query.data.queue_depth.toLocaleString()}</div><div className="metric-note">Accepted, queued, and deferred</div></div>
        <div className="card metric"><div className="metric-label">Retries</div><div className="metric-value">{query.data.retries.toLocaleString()}</div><div className="metric-note">Currently deferred</div></div>
        <div className="card metric"><div className="metric-label">Dead letter</div><div className="metric-value">{query.data.dlq.toLocaleString()}</div><div className="metric-note">Operator action required</div></div>
      </section>
      <section className="grid two-col">
        <div className="card"><div className="card-header"><h2>Delivery states</h2></div>{Object.keys(query.data.status_counts).length ? <div className="table-wrap"><table><thead><tr><th>Status</th><th>Count</th></tr></thead><tbody>{Object.entries(query.data.status_counts).map(([status, count]) => <tr key={status}><td><Status value={status} /></td><td>{count.toLocaleString()}</td></tr>)}</tbody></table></div> : <EmptyState title="No notifications yet" detail="Accepted notifications will appear here." />}</div>
        <div className="card"><div className="card-header"><h2>Provider health</h2></div>{query.data.provider_health.length ? <div className="table-wrap"><table><thead><tr><th>Provider</th><th>Health</th></tr></thead><tbody>{query.data.provider_health.map((provider) => <tr key={`${provider.channel}-${provider.name}`}><td><strong>{provider.name}</strong><div className="muted">{provider.channel}</div></td><td><Status value={provider.health} /></td></tr>)}</tbody></table></div> : <EmptyState title="No providers configured" detail="Register and verify a provider before sending." />}</div>
      </section>
    </> : null}
  </>;
}
