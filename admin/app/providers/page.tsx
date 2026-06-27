"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {Archive, Edit3, KeyRound, PlugZap, Plus, Star} from "lucide-react";
import {FormEvent, useMemo, useState} from "react";
import {Modal} from "@/components/modal";
import {EmptyState, ErrorState, LoadingState, Status} from "@/components/query-state";
import {useWorkspace} from "@/components/workspace";
import {api, Page, Provider} from "@/lib/api";

type TestResult = {valid: boolean; health_status: string; errors: string[]; error_code?: string | null; message?: string | null; latency_ms?: number | null};

function providerBody(data: FormData) {
  const appScoped = data.get("scope") === "app";
  const type = String(data.get("provider_type"));
  if (type === "fake") {
    return {
      appScoped,
      body: {channel: data.get("channel"), provider_type: "fake", name: data.get("name"), public_config: {from_email: data.get("from_email") || undefined}, secret_config: {}},
      test: {channel: data.get("channel"), provider_type: "fake", public_config: {from_email: data.get("from_email") || undefined}, secret_config: {}},
    };
  }
  const public_config = {host: data.get("host"), port: Number(data.get("port")), security: data.get("security"), username: data.get("username"), from_email: data.get("from_email"), timeout_seconds: 5};
  const secret_config = {password: data.get("password")};
  return {
    appScoped,
    body: {channel: "email", provider_type: "smtp", name: data.get("name"), public_config, secret_config, is_default: !appScoped, fallback_policy: appScoped ? "none" : "default_if_absent"},
    test: {channel: "email", provider_type: "smtp", public_config, secret_config},
  };
}

export default function ProvidersPage() {
  const {tenantId, appId} = useWorkspace();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Provider | null>(null);
  const [replacingSecret, setReplacingSecret] = useState<Provider | null>(null);
  const [editJsonError, setEditJsonError] = useState<string | null>(null);
  const [lastTest, setLastTest] = useState<TestResult | null>(null);
  const [lastForm, setLastForm] = useState<string>("");
  const queryClient = useQueryClient();
  const query = useQuery({queryKey: ["providers", tenantId], queryFn: () => api<Page<Provider>>(`/api/v1/tenants/${tenantId}/providers`), enabled: Boolean(tenantId)});
  const visibleProviders = useMemo(() => query.data?.items.filter((provider) => provider.health_status !== "archived") ?? [], [query.data?.items]);
  const create = useMutation({
    mutationFn: ({scope, body}: {scope: string; body: object}) => api<Provider>(scope, {method: "POST", body: JSON.stringify(body)}),
    onSuccess: () => {queryClient.invalidateQueries({queryKey: ["providers", tenantId]}); setCreating(false); setLastTest(null);},
  });
  const preTest = useMutation({
    mutationFn: (body: object) => api<TestResult>("/api/v1/provider-configs/test-connection", {method: "POST", body: JSON.stringify(body)}),
    onSuccess: (result) => setLastTest(result),
  });
  const action = useMutation({
    mutationFn: ({id, action}: {id: string; action: "test"|"activate"|"deactivate"|"set-default"|"unset-default"|"archive"}) => {
      if (action === "archive") return api(`/api/v1/provider-configs/${id}`, {method: "DELETE"});
      return api(`/api/v1/provider-configs/${id}/${action}`, {method: "POST"});
    },
    onSuccess: () => queryClient.invalidateQueries({queryKey: ["providers", tenantId]}),
  });
  const update = useMutation({
    mutationFn: ({id, body}: {id: string; body: object}) => api<Provider>(`/api/v1/provider-configs/${id}`, {method: "PATCH", body: JSON.stringify(body)}),
    onSuccess: () => {queryClient.invalidateQueries({queryKey: ["providers", tenantId]}); setEditing(null);},
  });
  const replaceSecret = useMutation({
    mutationFn: ({id, secret_config}: {id: string; secret_config: object}) => api<Provider>(`/api/v1/provider-configs/${id}/replace-secret`, {method: "POST", body: JSON.stringify({secret_config})}),
    onSuccess: () => {queryClient.invalidateQueries({queryKey: ["providers", tenantId]}); setReplacingSecret(null);},
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const {appScoped, body} = providerBody(data);
    const scope = appScoped ? `/api/v1/apps/${appId}/providers` : `/api/v1/tenants/${tenantId}/providers`;
    create.mutate({scope, body});
  }
  function testConnection(form: HTMLFormElement) {
    const data = new FormData(form);
    const {appScoped, test} = providerBody(data);
    const signature = JSON.stringify(test);
    setLastForm(signature);
    preTest.mutate({...test, tenant_id: tenantId, application_id: appScoped ? appId : null});
  }
  function submitEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editing) return;
    const data = new FormData(event.currentTarget);
    let public_config: Record<string, unknown>;
    try {
      public_config = JSON.parse(String(data.get("public_config") || "{}"));
    } catch (error) {
      setEditJsonError(error instanceof Error ? error.message : "Public configuration must be valid JSON");
      return;
    }
    setEditJsonError(null);
    update.mutate({
      id: editing.id,
      body: {
        name: data.get("name"),
        public_config,
        fallback_policy: data.get("fallback_policy"),
        fallback_provider_id: data.get("fallback_provider_id") || null,
      },
    });
  }
  function submitSecret(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!replacingSecret) return;
    const data = new FormData(event.currentTarget);
    replaceSecret.mutate({id: replacingSecret.id, secret_config: {password: data.get("password")}});
  }
  return <>
    <header className="page-header"><div><h1>Providers</h1><p>Test SMTP before saving, keep secrets write-only, activate only healthy providers, and archive safely.</p></div><button className="button primary" onClick={() => {setCreating(true); setLastTest(null);}} disabled={!tenantId}><Plus size={16} /> Register provider</button></header>
    {!tenantId ? <EmptyState title="Choose a tenant" detail="Provider inventory is tenant-scoped." /> : query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} /> : !visibleProviders.length ? <EmptyState title="No providers" detail="Register an app provider or a policy-approved tenant default." /> :
      <div className="card table-wrap"><table><thead><tr><th>Provider</th><th>Scope</th><th>Channel</th><th>Health</th><th>Default</th><th>Diagnostics</th><th>Actions</th></tr></thead><tbody>{visibleProviders.map((provider) => <tr key={provider.id}><td><strong>{provider.name}</strong><div className="mono muted">{provider.provider_type} · {provider.secret_configured ? "secret set" : "no secret"}</div></td><td>{provider.application_id ? "Application" : "Tenant"}</td><td>{provider.channel}</td><td><Status value={provider.health_status} /></td><td>{provider.is_default ? "Yes" : "No"}</td><td><div className="muted">{provider.verified_at ? `Verified ${new Date(provider.verified_at).toLocaleString()}` : "Not verified"}</div><div className="mono muted">{provider.last_error_code ?? "No error code"}</div></td><td><div className="toolbar"><button className="button" onClick={() => action.mutate({id: provider.id, action: "test"})}><PlugZap size={14} /> Test</button><button className="button" onClick={() => {setEditing(provider); setEditJsonError(null);}}><Edit3 size={14} /> Edit</button><button className="button" onClick={() => setReplacingSecret(provider)}><KeyRound size={14} /> Replace secret</button><button className="button" onClick={() => action.mutate({id: provider.id, action: provider.active ? "deactivate" : "activate"})} disabled={!provider.active && provider.health_status !== "healthy"}>{provider.active ? "Deactivate" : "Activate"}</button>{!provider.application_id && <button className="button" onClick={() => action.mutate({id: provider.id, action: provider.is_default ? "unset-default" : "set-default"})} disabled={!provider.is_default && (!provider.active || provider.health_status !== "healthy")}><Star size={14} /> {provider.is_default ? "Unset default" : "Set default"}</button>}<button className="button danger" onClick={() => action.mutate({id: provider.id, action: "archive"})} disabled={provider.active || provider.is_default}><Archive size={14} /> Archive</button></div></td></tr>)}</tbody></table>{action.error && <div className="card-body"><div className="error-box">{action.error.message}</div></div>}</div>}
    {creating && <Modal title="Register provider" onClose={() => setCreating(false)}><form onSubmit={submit} onChange={() => setLastTest(null)}><div className="form-grid"><div className="field"><label htmlFor="scope">Scope</label><select id="scope" name="scope"><option value="app" disabled={!appId}>Application</option><option value="tenant">Tenant default</option></select></div><div className="field"><label htmlFor="provider_type">Adapter</label><select id="provider_type" name="provider_type"><option value="fake">Deterministic fake</option><option value="smtp">SMTP</option></select></div><div className="field"><label htmlFor="channel">Channel</label><select id="channel" name="channel"><option>email</option><option>sms</option><option>webhook</option><option>push</option><option>telegram</option><option>whatsapp</option></select></div><div className="field"><label htmlFor="name">Name</label><input id="name" name="name" required /></div><div className="field"><label htmlFor="host">SMTP host</label><input id="host" name="host" /></div><div className="field"><label htmlFor="port">SMTP port</label><input id="port" name="port" type="number" defaultValue="465" /></div><div className="field"><label htmlFor="security">Security</label><select id="security" name="security"><option value="ssl">SSL</option><option value="starttls">STARTTLS</option><option value="plain">Plain (local only)</option></select></div><div className="field"><label htmlFor="username">Username</label><input id="username" name="username" /></div><div className="field"><label htmlFor="from_email">Authenticated sender</label><input id="from_email" name="from_email" type="email" /></div><div className="field"><label htmlFor="password">Password (write-only)</label><input id="password" name="password" type="password" autoComplete="new-password" /></div></div>{preTest.data && <div className={preTest.data.valid ? "success-box" : "error-box"} style={{marginTop: 14}}>{preTest.data.valid ? "Connection test passed" : `${preTest.data.error_code ?? "CONFIG_INVALID"}: ${preTest.data.errors.join("; ")}`}</div>}{preTest.error && <div className="error-box">{preTest.error.message}</div>}{create.error && <div className="error-box">{create.error.message}</div>}<div className="form-actions"><button type="button" className="button" onClick={() => setCreating(false)}>Cancel</button><button type="button" className="button" onClick={(event) => testConnection(event.currentTarget.form!)} disabled={preTest.isPending}><PlugZap size={14} /> Test connection</button><button className="button primary" disabled={create.isPending || !lastTest?.valid || lastForm === ""}>Register provider</button></div></form></Modal>}
    {editing && <Modal title={`Edit ${editing.name}`} onClose={() => setEditing(null)}><form onSubmit={submitEdit}><div className="field"><label htmlFor="edit-name">Name</label><input id="edit-name" name="name" defaultValue={editing.name} required /></div><div className="field" style={{marginTop: 14}}><label htmlFor="edit-public-config">Public configuration</label><textarea id="edit-public-config" name="public_config" defaultValue={JSON.stringify(editing.public_config ?? {}, null, 2)} style={{minHeight: 180, fontFamily: "var(--font-mono)"}} /></div><div className="form-grid" style={{marginTop: 14}}><div className="field"><label htmlFor="fallback_policy">Fallback policy</label><select id="fallback_policy" name="fallback_policy" defaultValue={editing.fallback_policy}><option value="none">none</option><option value="default_if_absent">default_if_absent</option><option value="explicit_failover">explicit_failover</option></select></div><div className="field"><label htmlFor="fallback_provider_id">Fallback provider ID</label><input id="fallback_provider_id" name="fallback_provider_id" defaultValue={editing.fallback_provider_id ?? ""} placeholder="Optional provider ID" /></div></div><div className="success-box" style={{marginTop: 14}}>Saving public config resets health to unknown. Run Test before activating or setting default.</div>{editJsonError && <div className="error-box">Invalid public configuration JSON: {editJsonError}</div>}{update.error && <div className="error-box">{update.error.message}</div>}<div className="form-actions"><button type="button" className="button" onClick={() => setEditing(null)}>Cancel</button><button className="button primary" disabled={update.isPending}><Edit3 size={14} /> Save changes</button></div></form></Modal>}
    {replacingSecret && <Modal title={`Replace secret for ${replacingSecret.name}`} onClose={() => setReplacingSecret(null)}><form onSubmit={submitSecret}><div className="error-box">Secret fields are write-only. The old secret will never be shown here, and this action resets provider health to unknown until the next successful test.</div><div className="field" style={{marginTop: 14}}><label htmlFor="replace-password">SMTP password</label><input id="replace-password" name="password" type="password" autoComplete="new-password" required /></div>{replaceSecret.error && <div className="error-box">{replaceSecret.error.message}</div>}<div className="form-actions"><button type="button" className="button" onClick={() => setReplacingSecret(null)}>Cancel</button><button className="button primary" disabled={replaceSecret.isPending}><KeyRound size={14} /> Replace secret</button></div></form></Modal>}
  </>;
}
