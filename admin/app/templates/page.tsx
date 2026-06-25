"use client";

import Editor from "@monaco-editor/react";
import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {Eye, Plus, Rocket} from "lucide-react";
import {FormEvent, useState} from "react";
import {Modal} from "@/components/modal";
import {EmptyState, ErrorState, LoadingState, Status} from "@/components/query-state";
import {useWorkspace} from "@/components/workspace";
import {api, Page, TemplateRecord} from "@/lib/api";

type Version = {id: string; template_id: string; version: number; state: string; content: Record<string,string>; validation_errors: string[]};

export default function TemplatesPage() {
  const {appId} = useWorkspace();
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<TemplateRecord | null>(null);
  const [content, setContent] = useState(JSON.stringify({subject: "Hello {{ name }}", html: "<p>Hello {{ name }}</p>", text: "Hello {{ name }}"}, null, 2));
  const [sample, setSample] = useState(JSON.stringify({name: "Ravi"}, null, 2));
  const queryClient = useQueryClient();
  const query = useQuery({queryKey: ["templates", appId], queryFn: () => api<Page<TemplateRecord>>(`/api/v1/apps/${appId}/templates`), enabled: Boolean(appId)});
  const versions = useQuery({queryKey: ["template-versions", selected?.id], queryFn: () => api<Page<Version>>(`/api/v1/templates/${selected!.id}/versions`), enabled: Boolean(selected)});
  const create = useMutation({
    mutationFn: ({eventKey, body}: {eventKey: string; body: object}) => api<Version>(`/api/v1/apps/${appId}/events/${eventKey}/templates`, {method: "POST", body: JSON.stringify(body)}),
    onSuccess: () => {queryClient.invalidateQueries({queryKey: ["templates", appId]}); setCreating(false);},
  });
  const action = useMutation({
    mutationFn: ({id, name}: {id: string; name: "validate"|"publish"}) => api<Version>(`/api/v1/template-versions/${id}/${name}`, {method: "POST"}),
    onSuccess: () => {queryClient.invalidateQueries({queryKey: ["template-versions", selected?.id]}); queryClient.invalidateQueries({queryKey: ["templates", appId]});},
  });
  const preview = useMutation({mutationFn: (id: string) => api<{rendered: Record<string,string>}>(`/api/v1/template-versions/${id}/preview`, {method: "POST", body: "{}"})});
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      create.mutate({eventKey: String(data.get("event_key")), body: {channel: data.get("channel"), locale: data.get("locale"), variant: data.get("variant"), content: JSON.parse(content), sample_data: JSON.parse(sample)}});
    } catch { /* Monaco content remains available for correction. */ }
  }
  return <>
    <header className="page-header"><div><h1>Templates</h1><p>Author, validate, preview, publish, and roll back immutable channel content.</p></div><button className="button primary" onClick={() => setCreating(true)} disabled={!appId}><Plus size={16} /> New template</button></header>
    {!appId ? <EmptyState title="Choose an application" detail="Templates are scoped to an application and event." /> : query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} /> : !query.data?.items.length ? <EmptyState title="No templates" detail="Create a draft from an event contract." /> :
      <div className="card table-wrap"><table><thead><tr><th>Channel</th><th>Locale / variant</th><th>Status</th><th>Published</th><th></th></tr></thead><tbody>{query.data.items.map((template) => <tr key={template.id}><td><strong>{template.channel}</strong><div className="mono muted">{template.id}</div></td><td>{template.locale} / {template.variant}</td><td><Status value={template.status} /></td><td>{template.published_version ? `v${template.published_version}` : "—"}</td><td><button className="button" onClick={() => setSelected(template)}>Version history</button></td></tr>)}</tbody></table></div>}
    {creating && <Modal title="Create template draft" onClose={() => setCreating(false)}><form onSubmit={submit}><div className="form-grid"><div className="field wide"><label htmlFor="event_key">Event key</label><input id="event_key" name="event_key" placeholder="account.welcome" required /></div><div className="field"><label htmlFor="channel">Channel</label><select id="channel" name="channel"><option>email</option><option>sms</option><option>webhook</option><option>push</option><option>telegram</option><option>whatsapp</option></select></div><div className="field"><label htmlFor="locale">Locale</label><input id="locale" name="locale" defaultValue="en" required /></div><div className="field"><label htmlFor="variant">Variant</label><input id="variant" name="variant" defaultValue="default" required /></div></div><div className="field" style={{marginTop: 14}}><label>Channel content</label><div style={{height: 270, border: "1px solid var(--border)"}}><Editor language="json" theme="vs-dark" value={content} onChange={(value) => setContent(value ?? "{}")} options={{minimap: {enabled: false}, automaticLayout: true, fontSize: 12}} /></div></div><div className="field" style={{marginTop: 14}}><label>Sample data</label><div style={{height: 160, border: "1px solid var(--border)"}}><Editor language="json" theme="vs-dark" value={sample} onChange={(value) => setSample(value ?? "{}")} options={{minimap: {enabled: false}, automaticLayout: true, fontSize: 12}} /></div></div>{create.error && <div className="error-box">{create.error.message}</div>}<div className="form-actions"><button type="button" className="button" onClick={() => setCreating(false)}>Cancel</button><button className="button primary" disabled={create.isPending}>Create draft</button></div></form></Modal>}
    {selected && <Modal title={`${selected.channel} · ${selected.locale} · ${selected.variant}`} onClose={() => {setSelected(null); preview.reset();}}>{versions.isLoading ? <LoadingState /> : versions.error ? <ErrorState error={versions.error} /> : <div className="table-wrap"><table><thead><tr><th>Version</th><th>State</th><th>Actions</th></tr></thead><tbody>{versions.data?.items.map((version) => <tr key={version.id}><td>v{version.version}</td><td><Status value={version.state} /></td><td><div className="toolbar"><button className="button" onClick={() => action.mutate({id: version.id, name: "validate"})} disabled={!["draft","validated"].includes(version.state)}>Validate</button><button className="button" onClick={() => preview.mutate(version.id)}><Eye size={14} /> Preview</button><button className="button primary" onClick={() => action.mutate({id: version.id, name: "publish"})} disabled={version.state !== "validated"}><Rocket size={14} /> Publish</button></div></td></tr>)}</tbody></table>{action.error && <div className="error-box">{action.error.message}</div>}{preview.data && <div className="card-body"><div className="success-box">Preview rendered successfully</div><pre className="secret-box">{JSON.stringify(preview.data.rendered, null, 2)}</pre></div>}</div>}</Modal>}
  </>;
}
