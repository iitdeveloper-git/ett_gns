"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {Plus} from "lucide-react";
import {FormEvent, useState} from "react";
import {Modal} from "@/components/modal";
import {EmptyState, ErrorState, LoadingState, Status} from "@/components/query-state";
import {useWorkspace} from "@/components/workspace";
import {api, Application, Page} from "@/lib/api";

export default function ApplicationsPage() {
  const {tenantId, setAppId} = useWorkspace();
  const [creating, setCreating] = useState(false);
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["applications", tenantId],
    queryFn: () => api<Page<Application>>(`/api/v1/tenants/${tenantId}/apps`),
    enabled: Boolean(tenantId),
  });
  const create = useMutation({
    mutationFn: (body: object) => api<Application>(`/api/v1/tenants/${tenantId}/apps`, {method: "POST", body: JSON.stringify(body)}),
    onSuccess: (application) => {queryClient.invalidateQueries({queryKey: ["applications", tenantId]}); setAppId(application.id); setCreating(false);},
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    create.mutate({name: data.get("name"), slug: data.get("slug"), default_locale: data.get("locale"), timezone: data.get("timezone")});
  }
  return <>
    <header className="page-header"><div><h1>Applications</h1><p>Service identities, delivery defaults, locale, timezone, and quotas.</p></div><div className="toolbar"><button className="button primary" onClick={() => setCreating(true)} disabled={!tenantId}><Plus size={16} /> New application</button></div></header>
    {!tenantId ? <EmptyState title="Choose a tenant" detail="Enter a tenant ID in the workspace bar." /> : query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} /> : !query.data?.items.length ? <EmptyState title="No applications" detail="Create the first application for this tenant." /> :
      <div className="card table-wrap"><table><thead><tr><th>Application</th><th>Status</th><th>Locale</th><th>Timezone</th><th>Minute quota</th></tr></thead><tbody>{query.data.items.map((application) => <tr key={application.id} onClick={() => setAppId(application.id)} style={{cursor: "pointer"}}><td><strong>{application.name}</strong><div className="mono muted">{application.id}</div></td><td><Status value={application.status} /></td><td>{application.default_locale}</td><td>{application.timezone}</td><td>{application.quota_per_minute.toLocaleString()}</td></tr>)}</tbody></table></div>}
    {creating && <Modal title="Create application" onClose={() => setCreating(false)}><form onSubmit={submit}><div className="form-grid"><div className="field"><label htmlFor="name">Name</label><input id="name" name="name" required /></div><div className="field"><label htmlFor="slug">Slug</label><input id="slug" name="slug" pattern="[a-z0-9][a-z0-9-]+[a-z0-9]" required /></div><div className="field"><label htmlFor="locale">Default locale</label><input id="locale" name="locale" defaultValue="en" required /></div><div className="field"><label htmlFor="timezone">Timezone</label><input id="timezone" name="timezone" defaultValue="UTC" required /></div></div>{create.error && <div className="error-box">{create.error.message}</div>}<div className="form-actions"><button type="button" className="button" onClick={() => setCreating(false)}>Cancel</button><button className="button primary" disabled={create.isPending}>{create.isPending ? "Creating…" : "Create application"}</button></div></form></Modal>}
  </>;
}
