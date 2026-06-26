"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {Archive, PlugZap, Plus, Star} from "lucide-react";
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
  return <>
    <header className="page-header"><div><h1>Providers</h1><p>Test SMTP before saving, keep secrets write-only, activate only healthy providers, and archive safely.</p></div><button className="button primary" onClick={() => {setCreating(true); setLastTest(null);}} disabled={!tenantId}><Plus size={16} /> Register provider</button></header>
    {!tenantId ? <EmptyState title="Choose a tenant" detail="Provider inventory is tenant-scoped." /> : query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} /> : !visibleProviders.length ? <EmptyState title="No providers" detail="Register an app provider or a policy-approved tenant default." /> :
      <div className="card table-wrap"><table><thead><tr><th>Provider</th><th>Scope</th><th>Channel</th><th>Health</th><th>Default</th><th>Actions</th></tr></thead><tbody>{visibleProviders.map((provider) => <tr key={provider.id}><td><strong>{provider.name}</strong><div className="mono muted">{provider.provider_type} · {provider.secret_configured ? "secret set" : "no secret"}</div></td><td>{provider.application_id ? "Application" : "Tenant"}</td><td>{provider.channel}</td><td><Status value={provider.health_status} /></td><td>{provider.is_default ? "Yes" : "No"}</td><td><div className="toolbar"><button className="button" onClick={() => action.mutate({id: provider.id, action: "test"})}><PlugZap size={14} /> Test</button><button className="button" onClick={() => action.mutate({id: provider.id, action: provider.active ? "deactivate" : "activate"})}>{provider.active ? "Deactivate" : "Activate"}</button>{!provider.application_id && <button className="button" onClick={() => action.mutate({id: provider.id, action: provider.is_default ? "unset-default" : "set-default"})}><Star size={14} /> {provider.is_default ? "Unset default" : "Set default"}</button>}<button className="button danger" onClick={() => action.mutate({id: provider.id, action: "archive"})} disabled={provider.active}><Archive size={14} /> Archive</button></div></td></tr>)}</tbody></table>{action.error && <div className="card-body"><div className="error-box">{action.error.message}</div></div>}</div>}
    {creating && <Modal title="Register provider" onClose={() => setCreating(false)}><form onSubmit={submit} onChange={() => setLastTest(null)}><div className="form-grid"><div className="field"><label htmlFor="scope">Scope</label><select id="scope" name="scope"><option value="app" disabled={!appId}>Application</option><option value="tenant">Tenant default</option></select></div><div className="field"><label htmlFor="provider_type">Adapter</label><select id="provider_type" name="provider_type"><option value="fake">Deterministic fake</option><option value="smtp">SMTP</option></select></div><div className="field"><label htmlFor="channel">Channel</label><select id="channel" name="channel"><option>email</option><option>sms</option><option>webhook</option><option>push</option><option>telegram</option><option>whatsapp</option></select></div><div className="field"><label htmlFor="name">Name</label><input id="name" name="name" required /></div><div className="field"><label htmlFor="host">SMTP host</label><input id="host" name="host" /></div><div className="field"><label htmlFor="port">SMTP port</label><input id="port" name="port" type="number" defaultValue="465" /></div><div className="field"><label htmlFor="security">Security</label><select id="security" name="security"><option value="ssl">SSL</option><option value="starttls">STARTTLS</option><option value="plain">Plain (local only)</option></select></div><div className="field"><label htmlFor="username">Username</label><input id="username" name="username" /></div><div className="field"><label htmlFor="from_email">Authenticated sender</label><input id="from_email" name="from_email" type="email" /></div><div className="field"><label htmlFor="password">Password (write-only)</label><input id="password" name="password" type="password" autoComplete="new-password" /></div></div>{preTest.data && <div className={preTest.data.valid ? "success-box" : "error-box"} style={{marginTop: 14}}>{preTest.data.valid ? "Connection test passed" : `${preTest.data.error_code ?? "CONFIG_INVALID"}: ${preTest.data.errors.join("; ")}`}</div>}{preTest.error && <div className="error-box">{preTest.error.message}</div>}{create.error && <div className="error-box">{create.error.message}</div>}<div className="form-actions"><button type="button" className="button" onClick={() => setCreating(false)}>Cancel</button><button type="button" className="button" onClick={(event) => testConnection(event.currentTarget.form!)} disabled={preTest.isPending}><PlugZap size={14} /> Test connection</button><button className="button primary" disabled={create.isPending || !lastTest?.valid || lastForm === ""}>Register provider</button></div></form></Modal>}
  </>;
}
