"use client";

import Editor from "@monaco-editor/react";
import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {Plus} from "lucide-react";
import {FormEvent, useState} from "react";
import {Modal} from "@/components/modal";
import {EmptyState, ErrorState, LoadingState, Status} from "@/components/query-state";
import {useWorkspace} from "@/components/workspace";
import {api, EventRecord, Page} from "@/lib/api";

const initialSchema = JSON.stringify({type: "object", required: ["name"], properties: {name: {type: "string"}}, additionalProperties: false}, null, 2);

export default function EventsPage() {
  const {appId} = useWorkspace();
  const [creating, setCreating] = useState(false);
  const [schema, setSchema] = useState(initialSchema);
  const queryClient = useQueryClient();
  const query = useQuery({queryKey: ["events", appId], queryFn: () => api<Page<EventRecord>>(`/api/v1/apps/${appId}/events`), enabled: Boolean(appId)});
  const create = useMutation({
    mutationFn: (body: object) => api<EventRecord>(`/api/v1/apps/${appId}/events`, {method: "POST", body: JSON.stringify(body)}),
    onSuccess: () => {queryClient.invalidateQueries({queryKey: ["events", appId]}); setCreating(false);},
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      create.mutate({event_key: data.get("event_key"), allowed_channels: data.getAll("channels"), recipient_policy: {}, schema: JSON.parse(schema)});
    } catch { create.reset(); }
  }
  return <>
    <header className="page-header"><div><h1>Events</h1><p>Versioned contracts define valid event data, recipients, and allowed channels.</p></div><button className="button primary" onClick={() => setCreating(true)} disabled={!appId}><Plus size={16} /> New event</button></header>
    {!appId ? <EmptyState title="Choose an application" detail="Enter or select an app ID in the workspace bar." /> : query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} /> : !query.data?.items.length ? <EmptyState title="No events" detail="Register an event contract to begin template authoring." /> :
      <div className="card table-wrap"><table><thead><tr><th>Event key</th><th>Status</th><th>Channels</th><th>Schema version</th></tr></thead><tbody>{query.data.items.map((event) => <tr key={event.id}><td><strong className="mono">{event.event_key}</strong><div className="mono muted">{event.id}</div></td><td><Status value={event.status} /></td><td>{event.allowed_channels.join(", ")}</td><td>v{event.current_schema_version}</td></tr>)}</tbody></table></div>}
    {creating && <Modal title="Register event" onClose={() => setCreating(false)}><form onSubmit={submit}><div className="field"><label htmlFor="event_key">Event key</label><input id="event_key" name="event_key" placeholder="invoice.ready" required /></div><div className="field" style={{marginTop: 14}}><label>Allowed channels</label><div className="toolbar">{["email","sms","webhook","push","telegram","whatsapp"].map((channel) => <label key={channel}><input type="checkbox" name="channels" value={channel} defaultChecked={channel === "email"} style={{width: "auto"}} /> {channel}</label>)}</div></div><div className="field" style={{marginTop: 14}}><label>JSON Schema</label><div style={{height: 300, border: "1px solid var(--border)"}}><Editor language="json" theme="vs-dark" value={schema} onChange={(value) => setSchema(value ?? "{}")} options={{minimap: {enabled: false}, fontSize: 12, automaticLayout: true}} /></div></div>{create.error && <div className="error-box">{create.error.message}</div>}<div className="form-actions"><button type="button" className="button" onClick={() => setCreating(false)}>Cancel</button><button className="button primary" disabled={create.isPending}>Register event</button></div></form></Modal>}
  </>;
}
