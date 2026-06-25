"use client";

import {useQuery} from "@tanstack/react-query";
import {EmptyState, ErrorState, LoadingState} from "@/components/query-state";
import {api, Page} from "@/lib/api";

type Audit = {id:string; actor_id:string; actor_type:string; action:string; target_type:string; target_id:string; request_id:string|null; changes:Record<string,unknown>; created_at:string};

export default function AuditsPage() {
  const query = useQuery({queryKey: ["audits"], queryFn: () => api<Page<Audit>>("/api/v1/audits")});
  return <>
    <header className="page-header"><div><h1>Audit trail</h1><p>Tenant-sensitive control-plane actions with actor, target, request, and change summary.</p></div></header>
    {query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} /> : !query.data?.items.length ? <EmptyState title="No audit events" detail="Administrative changes will be recorded here." /> :
      <div className="card table-wrap"><table><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Target</th><th>Request</th><th>Changes</th></tr></thead><tbody>{query.data.items.map((audit) => <tr key={audit.id}><td>{new Date(audit.created_at).toLocaleString()}</td><td><strong>{audit.actor_id}</strong><div className="muted">{audit.actor_type}</div></td><td className="mono">{audit.action}</td><td>{audit.target_type}<div className="mono muted">{audit.target_id}</div></td><td className="mono">{audit.request_id ?? "—"}</td><td className="mono truncate">{JSON.stringify(audit.changes)}</td></tr>)}</tbody></table></div>}
  </>;
}
