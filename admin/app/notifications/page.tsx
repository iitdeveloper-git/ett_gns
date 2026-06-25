"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {RefreshCw, RotateCcw, Search} from "lucide-react";
import {useState} from "react";
import {Modal} from "@/components/modal";
import {EmptyState, ErrorState, LoadingState, Status} from "@/components/query-state";
import {api, NotificationRecord, Page} from "@/lib/api";

type Timeline = {notification: NotificationRecord; recipient: Record<string,string>; attempts: {id:string; attempt_number:number; status:string; retryable:boolean; error_code:string|null; provider_message_id:string|null; duration_ms:number|null}[]; events: {id:string; status:string; occurred_at:string}[]};

export default function NotificationsPage() {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<NotificationRecord | null>(null);
  const queryClient = useQueryClient();
  const query = useQuery({queryKey: ["notifications", status, search], queryFn: () => api<Page<NotificationRecord>>(`/api/v1/operations/notifications?status=${encodeURIComponent(status)}&search=${encodeURIComponent(search)}`)});
  const timeline = useQuery({queryKey: ["timeline", selected?.id], queryFn: () => api<Timeline>(`/api/v1/operations/notifications/${selected!.id}`), enabled: Boolean(selected)});
  const action = useMutation({mutationFn: ({id, action}: {id: string; action: "retry"|"dlq-replay"}) => api(`/api/v1/operations/notifications/${id}/${action}`, {method: "POST"}), onSuccess: () => {queryClient.invalidateQueries({queryKey: ["notifications"]}); queryClient.invalidateQueries({queryKey: ["timeline", selected?.id]});}});
  return <>
    <header className="page-header"><div><h1>Notifications</h1><p>Search delivery state, inspect attempts, and safely retry or replay dead letters.</p></div><div className="toolbar"><button className="button" onClick={() => query.refetch()}><RefreshCw size={15} /> Refresh</button></div></header>
    <div className="card" style={{marginBottom: 14}}><div className="card-body toolbar"><div style={{position: "relative", minWidth: 280}}><Search size={15} style={{position: "absolute", left: 10, top: 11, color: "var(--muted)"}} /><input aria-label="Search notifications" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="ID, correlation ID, or event" style={{paddingLeft: 32}} /></div><select aria-label="Filter by status" value={status} onChange={(event) => setStatus(event.target.value)} style={{width: 190}}><option value="">All statuses</option>{["accepted","queued","processing","sent","delivered","deferred","failed","dead_lettered","cancelled"].map((value) => <option key={value}>{value}</option>)}</select></div></div>
    {query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} /> : !query.data?.items.length ? <EmptyState title="No matching notifications" detail="Adjust filters or send a notification." /> :
      <div className="card table-wrap"><table><thead><tr><th>Notification</th><th>Event</th><th>Channel</th><th>Status</th><th>Created</th></tr></thead><tbody>{query.data.items.map((notification) => <tr key={notification.id} onClick={() => setSelected(notification)} style={{cursor: "pointer"}}><td className="mono">{notification.id}<div className="muted">{notification.correlation_id ?? "No correlation ID"}</div></td><td>{notification.event_key}</td><td>{notification.channel}</td><td><Status value={notification.status} /></td><td>{new Date(notification.created_at).toLocaleString()}</td></tr>)}</tbody></table></div>}
    {selected && <Modal title="Delivery timeline" onClose={() => setSelected(null)}>{timeline.isLoading ? <LoadingState /> : timeline.error ? <ErrorState error={timeline.error} /> : timeline.data ? <><div className="toolbar" style={{justifyContent: "space-between", marginBottom: 16}}><div><Status value={timeline.data.notification.status} /> <span className="mono muted">{selected.id}</span></div><div className="toolbar"><button className="button" onClick={() => action.mutate({id: selected.id, action: "retry"})}><RotateCcw size={14} /> Retry</button><button className="button" onClick={() => action.mutate({id: selected.id, action: "dlq-replay"})}>Replay DLQ</button></div></div><div className="card"><div className="card-header"><h2>Attempts</h2></div>{timeline.data.attempts.length ? <div className="table-wrap"><table><thead><tr><th>#</th><th>Status</th><th>Error</th><th>Latency</th></tr></thead><tbody>{timeline.data.attempts.map((attempt) => <tr key={attempt.id}><td>{attempt.attempt_number}</td><td><Status value={attempt.status} /></td><td>{attempt.error_code ?? "—"}</td><td>{attempt.duration_ms == null ? "—" : `${attempt.duration_ms} ms`}</td></tr>)}</tbody></table></div> : <EmptyState title="No attempts yet" detail="The notification has not reached a worker." />}</div>{action.error && <div className="error-box" style={{marginTop: 12}}>{action.error.message}</div>}</> : null}</Modal>}
  </>;
}
