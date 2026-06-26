"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {BellRing, PlugZap, Send} from "lucide-react";
import {FormEvent, useState} from "react";
import {EmptyState, ErrorState, LoadingState, Status} from "@/components/query-state";
import {useWorkspace} from "@/components/workspace";
import {api, InAppAdminNotification, InAppConnection, Page} from "@/lib/api";

type Attempt = {id: string; notification_recipient_id: string; attempt_number: number; transport: string; status: string; error_code: string | null; created_at: string};

export default function InAppPage() {
  const {tenantId, appId} = useWorkspace();
  const [apiKey, setApiKey] = useState("");
  const queryClient = useQueryClient();
  const notifications = useQuery({queryKey: ["admin-in-app-notifications", tenantId, appId], queryFn: () => api<Page<InAppAdminNotification>>(`/api/v1/admin/in-app/notifications?tenant_id=${tenantId}&application_id=${appId}`), enabled: Boolean(tenantId && appId)});
  const connections = useQuery({queryKey: ["admin-in-app-connections"], queryFn: () => api<Page<InAppConnection>>("/api/v1/admin/in-app/connections")});
  const attempts = useQuery({queryKey: ["admin-in-app-attempts"], queryFn: () => api<Page<Attempt>>("/api/v1/admin/in-app/delivery-attempts?limit=20")});
  const test = useMutation({
    mutationFn: (body: object) => api<{notification_id: string}>("/api/v1/admin/in-app/test", {method: "POST", headers: {Authorization: `Bearer ${apiKey}`}, body: JSON.stringify(body)}),
    onSuccess: () => {queryClient.invalidateQueries({queryKey: ["admin-in-app-notifications"]}); queryClient.invalidateQueries({queryKey: ["admin-in-app-attempts"]});},
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    test.mutate({
      application_id: appId,
      event_key: data.get("event_key"),
      recipient: {type: "user", id: data.get("user_id")},
      data: JSON.parse(String(data.get("data") || "{}")),
      priority: Number(data.get("priority") || 5),
      metadata: {source: "admin-console", deduplication_key: data.get("deduplication_key") || undefined},
    });
  }
  return <>
    <header className="page-header"><div><h1>In-App Notifications</h1><p>Durable notification center records, SSE delivery, read state, connections, and test sends.</p></div></header>
    <section className="grid metric-grid" style={{marginBottom: 18}}>
      <div className="card metric"><div className="metric-label">Created</div><div className="metric-value">{notifications.data?.total ?? 0}</div><div className="metric-note">Selected workspace</div></div>
      <div className="card metric"><div className="metric-label">Active connections</div><div className="metric-value">{connections.data?.total ?? 0}</div><div className="metric-note">SSE sessions</div></div>
      <div className="card metric"><div className="metric-label">Delivery attempts</div><div className="metric-value">{attempts.data?.total ?? 0}</div><div className="metric-note">Recent tracked events</div></div>
      <div className="card metric"><div className="metric-label">Transport</div><div className="metric-value">SSE</div><div className="metric-note">HTTP actions for read/dismiss</div></div>
    </section>
    <section className="grid two-col">
      <div className="card"><div className="card-header"><h2><BellRing size={16} /> Notification inventory</h2></div>{!appId ? <EmptyState title="Choose an application" detail="In-app records are application-scoped." /> : notifications.isLoading ? <LoadingState /> : notifications.error ? <ErrorState error={notifications.error} /> : !notifications.data?.items.length ? <EmptyState title="No in-app notifications" detail="Send a test notification or process an in-app event." /> : <div className="table-wrap"><table><thead><tr><th>Title</th><th>Event</th><th>Severity</th><th>Priority</th><th>Created</th></tr></thead><tbody>{notifications.data.items.map((item) => <tr key={item.id}><td><strong>{item.title}</strong><div className="mono muted">{item.id}</div></td><td>{item.event_key}</td><td><Status value={item.severity} /></td><td>{item.priority}</td><td>{new Date(item.created_at).toLocaleString()}</td></tr>)}</tbody></table></div>}</div>
      <div className="card"><div className="card-header"><h2><Send size={16} /> Send test notification</h2></div><div className="card-body"><form onSubmit={submit}><div className="field"><label htmlFor="api-key">Application bearer key</label><input id="api-key" value={apiKey} onChange={(event) => setApiKey(event.target.value)} type="password" placeholder="gns_..." autoComplete="off" /></div><div className="field" style={{marginTop: 12}}><label htmlFor="event_key">Event key</label><input id="event_key" name="event_key" placeholder="payment.pending" required /></div><div className="field" style={{marginTop: 12}}><label htmlFor="user_id">User ID</label><input id="user_id" name="user_id" placeholder="usr_123" required /></div><div className="field" style={{marginTop: 12}}><label htmlFor="priority">Priority</label><input id="priority" name="priority" type="number" min="1" max="10" defaultValue="5" /></div><div className="field" style={{marginTop: 12}}><label htmlFor="deduplication_key">Deduplication key</label><input id="deduplication_key" name="deduplication_key" placeholder="payment-pending-INV-1024" /></div><div className="field" style={{marginTop: 12}}><label htmlFor="data">Sample data</label><textarea id="data" name="data" defaultValue={'{"invoice_id":"INV-1024","amount":"2500"}'} /></div>{test.data && <div className="success-box">Accepted notification {test.data.notification_id}</div>}{test.error && <div className="error-box">{test.error.message}</div>}<div className="form-actions"><button className="button primary" disabled={!appId || !apiKey || test.isPending}><PlugZap size={14} /> Send test</button></div></form></div></div>
    </section>
    <section className="card" style={{marginTop: 18}}><div className="card-header"><h2>Connections and attempts</h2></div><div className="table-wrap"><table><thead><tr><th>Kind</th><th>ID</th><th>Status</th><th>Detail</th></tr></thead><tbody>{connections.data?.items.map((connection) => <tr key={connection.connection_id}><td>Connection</td><td className="mono">{connection.connection_id}</td><td><Status value={connection.transport} /></td><td>{connection.user_id} · {connection.session_id}</td></tr>)}{attempts.data?.items.map((attempt) => <tr key={attempt.id}><td>Attempt</td><td className="mono">{attempt.id}</td><td><Status value={attempt.status} /></td><td>{attempt.transport} · #{attempt.attempt_number} {attempt.error_code ?? ""}</td></tr>)}</tbody></table></div></section>
  </>;
}
