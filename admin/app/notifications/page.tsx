"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {PlugZap, RefreshCw, RotateCcw, Search} from "lucide-react";
import {FormEvent, useState} from "react";
import {Modal} from "@/components/modal";
import {EmptyState, ErrorState, LoadingState, Status} from "@/components/query-state";
import {useWorkspace} from "@/components/workspace";
import {api, EventRecord, NotificationRecord, Page} from "@/lib/api";

type Timeline = {notification: NotificationRecord; recipient: Record<string,string>; attempts: {id:string; attempt_number:number; status:string; retryable:boolean; error_code:string|null; provider_message_id:string|null; duration_ms:number|null}[]; events: {id:string; status:string; occurred_at:string}[]};

export default function NotificationsPage() {
  const {appId} = useWorkspace();
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [recipient, setRecipient] = useState(JSON.stringify({email: "person@example.com"}, null, 2));
  const [data, setData] = useState(JSON.stringify({name: "Ravi"}, null, 2));
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState(() => `test-${crypto.randomUUID()}`);
  const [selected, setSelected] = useState<NotificationRecord | null>(null);
  const queryClient = useQueryClient();
  const query = useQuery({queryKey: ["notifications", status, search], queryFn: () => api<Page<NotificationRecord>>(`/api/v1/operations/notifications?status=${encodeURIComponent(status)}&search=${encodeURIComponent(search)}`)});
  const events = useQuery({queryKey: ["events", appId], queryFn: () => api<Page<EventRecord>>(`/api/v1/apps/${appId}/events`), enabled: Boolean(appId)});
  const timeline = useQuery({queryKey: ["timeline", selected?.id], queryFn: () => api<Timeline>(`/api/v1/operations/notifications/${selected!.id}`), enabled: Boolean(selected)});
  const action = useMutation({mutationFn: ({id, action}: {id: string; action: "retry"|"dlq-replay"}) => api(`/api/v1/operations/notifications/${id}/${action}`, {method: "POST"}), onSuccess: () => {queryClient.invalidateQueries({queryKey: ["notifications"]}); queryClient.invalidateQueries({queryKey: ["timeline", selected?.id]});}});
  const sendTest = useMutation({
    mutationFn: (body: object) => api<NotificationRecord>("/api/v1/notifications", {method: "POST", headers: {Authorization: `Bearer ${apiKey}`, "Idempotency-Key": idempotencyKey}, body: JSON.stringify(body)}),
    onSuccess: (notification) => {
      setSelected(notification);
      setSearch(notification.id);
      setIdempotencyKey(`test-${crypto.randomUUID()}`);
      queryClient.invalidateQueries({queryKey: ["notifications"]});
    },
  });
  function submitTest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    let parsedRecipient: Record<string, unknown>;
    let parsedData: Record<string, unknown>;
    try {
      parsedRecipient = JSON.parse(recipient);
      parsedData = JSON.parse(data);
    } catch (error) {
      setJsonError(error instanceof Error ? error.message : "Recipient and sample data must be valid JSON");
      return;
    }
    setJsonError(null);
    sendTest.mutate({
      event_key: form.get("event_key"),
      channel: form.get("channel"),
      recipient: parsedRecipient,
      data: parsedData,
      locale: form.get("locale") || null,
      variant: form.get("variant") || null,
      priority: Number(form.get("priority") || 5),
      metadata: {source: "admin-console-test", correlation_id: form.get("correlation_id") || undefined},
    });
  }
  return <>
    <header className="page-header"><div><h1>Notifications</h1><p>Search delivery state, inspect attempts, and safely retry or replay dead letters.</p></div><div className="toolbar"><button className="button" onClick={() => query.refetch()}><RefreshCw size={15} /> Refresh</button></div></header>
    <div className="card" style={{marginBottom: 14}}><div className="card-header"><h2><PlugZap size={16} /> Send test notification</h2></div><div className="card-body"><form onSubmit={submitTest}><div className="form-grid"><div className="field"><label htmlFor="bearer-key">Application bearer key</label><input id="bearer-key" value={apiKey} onChange={(event) => setApiKey(event.target.value)} type="password" placeholder="gns_..." autoComplete="off" /></div><div className="field"><label htmlFor="test-event">Published event</label><select id="test-event" name="event_key" required>{events.data?.items.map((event) => <option key={event.id} value={event.event_key}>{event.event_key}</option>)}</select></div><div className="field"><label htmlFor="test-channel">Channel</label><select id="test-channel" name="channel" onChange={(event) => setRecipient(JSON.stringify(event.target.value === "sms" || event.target.value === "whatsapp" ? {phone: "+15551234567"} : event.target.value === "webhook" ? {url: "https://example.com/webhook"} : event.target.value === "push" ? {token: "device-token"} : event.target.value === "telegram" ? {chat_id: "123456"} : event.target.value === "in_app" ? {type: "user", id: "usr_123"} : {email: "person@example.com"}, null, 2))}><option>email</option><option>sms</option><option>webhook</option><option>push</option><option>telegram</option><option>whatsapp</option><option>in_app</option></select></div><div className="field"><label htmlFor="priority">Priority</label><input id="priority" name="priority" type="number" min="1" max="10" defaultValue="5" /></div><div className="field"><label htmlFor="locale">Locale</label><input id="locale" name="locale" placeholder="en" /></div><div className="field"><label htmlFor="variant">Variant</label><input id="variant" name="variant" placeholder="default" /></div><div className="field"><label htmlFor="correlation_id">Correlation ID</label><input id="correlation_id" name="correlation_id" placeholder="Optional external trace ID" /></div><div className="field"><label htmlFor="idempotency_key">Idempotency key</label><input id="idempotency_key" value={idempotencyKey} onChange={(event) => setIdempotencyKey(event.target.value)} /></div></div><div className="form-grid" style={{marginTop: 14}}><div className="field"><label htmlFor="recipient">Recipient JSON</label><textarea id="recipient" value={recipient} onChange={(event) => setRecipient(event.target.value)} style={{minHeight: 120, fontFamily: "var(--font-mono)"}} /></div><div className="field"><label htmlFor="data">Sample data JSON</label><textarea id="data" value={data} onChange={(event) => setData(event.target.value)} style={{minHeight: 120, fontFamily: "var(--font-mono)"}} /></div></div>{jsonError && <div className="error-box">Invalid JSON: {jsonError}</div>}{sendTest.data && <div className="success-box" style={{marginTop: 14}}>Accepted {sendTest.data.id}. Timeline opened below.</div>}{sendTest.error && <div className="error-box">{sendTest.error.message}</div>}<div className="form-actions"><button className="button primary" disabled={!apiKey || !events.data?.items.length || sendTest.isPending}><PlugZap size={14} /> Send through real API</button></div></form></div></div>
    <div className="card" style={{marginBottom: 14}}><div className="card-body toolbar"><div style={{position: "relative", minWidth: 280}}><Search size={15} style={{position: "absolute", left: 10, top: 11, color: "var(--muted)"}} /><input aria-label="Search notifications" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="ID, correlation ID, or event" style={{paddingLeft: 32}} /></div><select aria-label="Filter by status" value={status} onChange={(event) => setStatus(event.target.value)} style={{width: 190}}><option value="">All statuses</option>{["accepted","queued","processing","sent","delivered","deferred","failed","dead_lettered","cancelled"].map((value) => <option key={value}>{value}</option>)}</select></div></div>
    {query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} /> : !query.data?.items.length ? <EmptyState title="No matching notifications" detail="Adjust filters or send a notification." /> :
      <div className="card table-wrap"><table><thead><tr><th>Notification</th><th>Event</th><th>Channel</th><th>Status</th><th>Created</th></tr></thead><tbody>{query.data.items.map((notification) => <tr key={notification.id} onClick={() => setSelected(notification)} style={{cursor: "pointer"}}><td className="mono">{notification.id}<div className="muted">{notification.correlation_id ?? "No correlation ID"}</div></td><td>{notification.event_key}</td><td>{notification.channel}</td><td><Status value={notification.status} /></td><td>{new Date(notification.created_at).toLocaleString()}</td></tr>)}</tbody></table></div>}
    {selected && <Modal title="Delivery timeline" onClose={() => setSelected(null)}>{timeline.isLoading ? <LoadingState /> : timeline.error ? <ErrorState error={timeline.error} /> : timeline.data ? <><div className="toolbar" style={{justifyContent: "space-between", marginBottom: 16}}><div><Status value={timeline.data.notification.status} /> <span className="mono muted">{selected.id}</span></div><div className="toolbar"><button className="button" onClick={() => action.mutate({id: selected.id, action: "retry"})}><RotateCcw size={14} /> Retry</button><button className="button" onClick={() => action.mutate({id: selected.id, action: "dlq-replay"})}>Replay DLQ</button></div></div><div className="card"><div className="card-header"><h2>Attempts</h2></div>{timeline.data.attempts.length ? <div className="table-wrap"><table><thead><tr><th>#</th><th>Status</th><th>Error</th><th>Latency</th></tr></thead><tbody>{timeline.data.attempts.map((attempt) => <tr key={attempt.id}><td>{attempt.attempt_number}</td><td><Status value={attempt.status} /></td><td>{attempt.error_code ?? "—"}</td><td>{attempt.duration_ms == null ? "—" : `${attempt.duration_ms} ms`}</td></tr>)}</tbody></table></div> : <EmptyState title="No attempts yet" detail="The notification has not reached a worker." />}</div>{action.error && <div className="error-box" style={{marginTop: 12}}>{action.error.message}</div>}</> : null}</Modal>}
  </>;
}
