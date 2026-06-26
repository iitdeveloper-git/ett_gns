"use client";

import {useQuery} from "@tanstack/react-query";
import Link from "next/link";
import {useWorkspace} from "@/components/workspace";
import {api, Credential, EventRecord, Page, Provider, TemplateRecord} from "@/lib/api";
import {EmptyState, ErrorState, LoadingState, Status} from "@/components/query-state";

type Dashboard = {
  volume: number; queue_depth: number; retries: number; dlq: number;
  status_counts: Record<string, number>; channel_counts: Record<string, number>;
  provider_health: {channel: string; name: string; health: string; active: boolean}[];
};

export default function DashboardPage() {
  const {tenantId, appId} = useWorkspace();
  const query = useQuery({queryKey: ["dashboard"], queryFn: () => api<Dashboard>("/api/v1/operations/dashboard")});
  const events = useQuery({queryKey: ["onboarding-events", appId], queryFn: () => api<Page<EventRecord>>(`/api/v1/apps/${appId}/events`), enabled: Boolean(appId)});
  const templates = useQuery({queryKey: ["onboarding-templates", appId], queryFn: () => api<Page<TemplateRecord>>(`/api/v1/apps/${appId}/templates`), enabled: Boolean(appId)});
  const providers = useQuery({queryKey: ["onboarding-providers", tenantId], queryFn: () => api<Page<Provider>>(`/api/v1/tenants/${tenantId}/providers`), enabled: Boolean(tenantId)});
  const credentials = useQuery({queryKey: ["onboarding-credentials", appId], queryFn: () => api<Page<Credential>>(`/api/v1/apps/${appId}/credentials`), enabled: Boolean(appId)});
  const onboarding = [
    {label: "Tenant", done: Boolean(tenantId), href: "/applications", action: "Create or select tenant"},
    {label: "Application", done: Boolean(appId), href: "/applications", action: "Create application"},
    {label: "Event", done: Boolean(events.data?.items.length), href: "/events", action: "Register event"},
    {label: "Template", done: Boolean(templates.data?.items.some((template) => template.published_version)), href: "/templates", action: "Validate and publish template"},
    {label: "Provider", done: Boolean(providers.data?.items.some((provider) => provider.active && provider.health_status === "healthy")), href: "/providers", action: "Test and activate provider"},
    {label: "Credential", done: Boolean(credentials.data?.items.length), href: "/credentials", action: "Create app key"},
    {label: "Test notification", done: Boolean(query.data?.volume), href: "/notifications", action: "Send and inspect status"},
  ];
  return <>
    <header className="page-header"><div><h1>Delivery overview</h1><p>Queue pressure, delivery outcomes, and provider health at a glance.</p></div></header>
    {query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} /> : query.data ? <>
      <section className="card" style={{marginBottom: 18}}><div className="card-header"><h2>Guided onboarding</h2><span className="muted">Tenant → Application → Event → Template → Provider → Credential → Test notification</span></div><div className="onboarding-steps">{onboarding.map((step) => <Link key={step.label} href={step.href} className={`onboarding-step ${step.done ? "done" : ""}`}><Status value={step.done ? "active" : "queued"} /><strong>{step.label}</strong><span>{step.done ? "Complete" : step.action}</span></Link>)}</div></section>
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
