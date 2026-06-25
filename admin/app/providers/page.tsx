"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {PlugZap, Plus} from "lucide-react";
import {FormEvent, useState} from "react";
import {Modal} from "@/components/modal";
import {EmptyState, ErrorState, LoadingState, Status} from "@/components/query-state";
import {useWorkspace} from "@/components/workspace";
import {api, Page, Provider} from "@/lib/api";

export default function ProvidersPage() {
  const {tenantId, appId} = useWorkspace();
  const [creating, setCreating] = useState(false);
  const queryClient = useQueryClient();
  const query = useQuery({queryKey: ["providers", tenantId], queryFn: () => api<Page<Provider>>(`/api/v1/tenants/${tenantId}/providers`), enabled: Boolean(tenantId)});
  const create = useMutation({
    mutationFn: ({scope, body}: {scope: string; body: object}) => api<Provider>(scope, {method: "POST", body: JSON.stringify(body)}),
    onSuccess: () => {queryClient.invalidateQueries({queryKey: ["providers", tenantId]}); setCreating(false);},
  });
  const action = useMutation({
    mutationFn: ({id, action}: {id: string; action: "test"|"activate"|"deactivate"}) => api(`/api/v1/providers/${id}/${action}`, {method: "POST"}),
    onSuccess: () => queryClient.invalidateQueries({queryKey: ["providers", tenantId]}),
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const appScoped = data.get("scope") === "app";
    const type = String(data.get("provider_type"));
    const body = type === "fake"
      ? {channel: data.get("channel"), provider_type: "fake", name: data.get("name"), public_config: {from_email: data.get("from_email") || undefined}, secret: {}}
      : {channel: "email", provider_type: "smtp", name: data.get("name"), public_config: {host: data.get("host"), port: Number(data.get("port")), security: data.get("security"), username: data.get("username"), from_email: data.get("from_email")}, secret: {password: data.get("password")}, is_default: !appScoped, fallback_policy: appScoped ? "none" : "default_if_absent"};
    const scope = appScoped ? `/api/v1/apps/${appId}/providers` : `/api/v1/tenants/${tenantId}/providers`;
    create.mutate({scope, body});
  }
  return <>
    <header className="page-header"><div><h1>Providers</h1><p>Write-only secrets, connectivity health, sender scope, and explicit fallback policy.</p></div><button className="button primary" onClick={() => setCreating(true)} disabled={!tenantId}><Plus size={16} /> Register provider</button></header>
    {!tenantId ? <EmptyState title="Choose a tenant" detail="Provider inventory is tenant-scoped." /> : query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} /> : !query.data?.items.length ? <EmptyState title="No providers" detail="Register an app provider or a policy-approved default." /> :
      <div className="card table-wrap"><table><thead><tr><th>Provider</th><th>Scope</th><th>Channel</th><th>Health</th><th>Policy</th><th>Actions</th></tr></thead><tbody>{query.data.items.map((provider) => <tr key={provider.id}><td><strong>{provider.name}</strong><div className="mono muted">{provider.provider_type} · {provider.secret_configured ? "secret set" : "no secret"}</div></td><td>{provider.application_id ? "Application" : "Tenant default"}</td><td>{provider.channel}</td><td><Status value={provider.health_status} /></td><td>{provider.fallback_policy}</td><td><div className="toolbar"><button className="button" onClick={() => action.mutate({id: provider.id, action: "test"})}><PlugZap size={14} /> Test</button><button className="button" onClick={() => action.mutate({id: provider.id, action: provider.active ? "deactivate" : "activate"})}>{provider.active ? "Deactivate" : "Activate"}</button></div></td></tr>)}</tbody></table>{action.error && <div className="card-body"><div className="error-box">{action.error.message}</div></div>}</div>}
    {creating && <Modal title="Register provider" onClose={() => setCreating(false)}><form onSubmit={submit}><div className="form-grid"><div className="field"><label htmlFor="scope">Scope</label><select id="scope" name="scope"><option value="app" disabled={!appId}>Application</option><option value="tenant">Tenant default</option></select></div><div className="field"><label htmlFor="provider_type">Adapter</label><select id="provider_type" name="provider_type"><option value="fake">Deterministic fake</option><option value="smtp">SMTP</option></select></div><div className="field"><label htmlFor="channel">Channel</label><select id="channel" name="channel"><option>email</option><option>sms</option><option>webhook</option><option>push</option><option>telegram</option><option>whatsapp</option></select></div><div className="field"><label htmlFor="name">Name</label><input id="name" name="name" required /></div><div className="field"><label htmlFor="host">SMTP host</label><input id="host" name="host" /></div><div className="field"><label htmlFor="port">SMTP port</label><input id="port" name="port" type="number" defaultValue="465" /></div><div className="field"><label htmlFor="security">Security</label><select id="security" name="security"><option value="ssl">SSL</option><option value="starttls">STARTTLS</option><option value="plain">Plain (local only)</option></select></div><div className="field"><label htmlFor="username">Username</label><input id="username" name="username" /></div><div className="field"><label htmlFor="from_email">Authenticated sender</label><input id="from_email" name="from_email" type="email" /></div><div className="field"><label htmlFor="password">Password (write-only)</label><input id="password" name="password" type="password" autoComplete="new-password" /></div></div>{create.error && <div className="error-box">{create.error.message}</div>}<div className="form-actions"><button type="button" className="button" onClick={() => setCreating(false)}>Cancel</button><button className="button primary" disabled={create.isPending}>Register provider</button></div></form></Modal>}
  </>;
}
