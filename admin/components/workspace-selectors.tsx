"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {Plus} from "lucide-react";
import {FormEvent, useEffect, useMemo, useState} from "react";
import {Modal} from "@/components/modal";
import {useWorkspace} from "@/components/workspace";
import {api, Application, Page, Tenant} from "@/lib/api";

function slugify(value: string) {
  return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "gns";
}

export function WorkspaceSelectors() {
  const {tenantId, appId, setTenantId, setAppId} = useWorkspace();
  const [tenantSearch, setTenantSearch] = useState("");
  const [appSearch, setAppSearch] = useState("");
  const [creatingTenant, setCreatingTenant] = useState(false);
  const [creatingApp, setCreatingApp] = useState(false);
  const queryClient = useQueryClient();
  const tenants = useQuery({queryKey: ["workspace-tenants"], queryFn: () => api<Page<Tenant>>("/api/v1/tenants?limit=200")});
  const apps = useQuery({
    queryKey: ["workspace-apps", tenantId],
    queryFn: () => api<Page<Application>>(`/api/v1/tenants/${tenantId}/apps?limit=200`),
    enabled: Boolean(tenantId),
  });
  const tenantItems = useMemo(() => tenants.data?.items ?? [], [tenants.data?.items]);
  const appItems = useMemo(() => apps.data?.items ?? [], [apps.data?.items]);
  const filteredTenants = useMemo(() => tenantItems.filter((tenant) => `${tenant.name} ${tenant.slug}`.toLowerCase().includes(tenantSearch.toLowerCase())), [tenantItems, tenantSearch]);
  const filteredApps = useMemo(() => appItems.filter((app) => `${app.name} ${app.slug}`.toLowerCase().includes(appSearch.toLowerCase())), [appItems, appSearch]);
  const staleTenant = Boolean(tenantId && tenants.isSuccess && !tenantItems.some((tenant) => tenant.id === tenantId));
  const staleApp = Boolean(appId && apps.isSuccess && !appItems.some((app) => app.id === appId));

  useEffect(() => {
    if (staleTenant) {
      setTenantId("");
      setAppId("");
    }
  }, [setAppId, setTenantId, staleTenant]);
  useEffect(() => {
    if (staleApp) setAppId("");
  }, [setAppId, staleApp]);

  const createTenant = useMutation({
    mutationFn: (body: object) => api<Tenant>("/api/v1/tenants", {method: "POST", body: JSON.stringify(body)}),
    onSuccess: (tenant) => {
      queryClient.invalidateQueries({queryKey: ["workspace-tenants"]});
      setTenantId(tenant.id);
      setAppId("");
      setCreatingTenant(false);
    },
  });
  const createApp = useMutation({
    mutationFn: (body: object) => api<Application>(`/api/v1/tenants/${tenantId}/apps`, {method: "POST", body: JSON.stringify(body)}),
    onSuccess: (app) => {
      queryClient.invalidateQueries({queryKey: ["workspace-apps", tenantId]});
      setAppId(app.id);
      setCreatingApp(false);
    },
  });

  function submitTenant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const name = String(data.get("name"));
    createTenant.mutate({name, slug: String(data.get("slug")) || slugify(name)});
  }
  function submitApp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const name = String(data.get("name"));
    createApp.mutate({name, slug: String(data.get("slug")) || slugify(name), default_locale: "en", timezone: "UTC"});
  }

  return <div className="workspace-selector-wrap">
    <div className="workspace-select">
      <label htmlFor="tenant-selector">Tenant</label>
      <input aria-label="Search tenants" value={tenantSearch} onChange={(event) => setTenantSearch(event.target.value)} placeholder="Search tenants…" />
      <select id="tenant-selector" value={tenantId} onChange={(event) => {setTenantId(event.target.value); setAppId("");}}>
        <option value="">{tenants.isLoading ? "Loading tenants…" : tenantItems.length ? "Choose tenant" : "No tenants yet"}</option>
        {filteredTenants.map((tenant) => <option key={tenant.id} value={tenant.id}>{tenant.name}</option>)}
      </select>
      <button type="button" className="button" onClick={() => setCreatingTenant(true)}><Plus size={14} /> Tenant</button>
    </div>
    <div className="workspace-select">
      <label htmlFor="app-selector">Application</label>
      <input aria-label="Search applications" value={appSearch} onChange={(event) => setAppSearch(event.target.value)} placeholder={tenantId ? "Search apps…" : "Choose tenant first"} disabled={!tenantId} />
      <select id="app-selector" value={appId} onChange={(event) => setAppId(event.target.value)} disabled={!tenantId}>
        <option value="">{!tenantId ? "Choose tenant first" : apps.isLoading ? "Loading apps…" : appItems.length ? "Choose application" : "No applications yet"}</option>
        {filteredApps.map((app) => <option key={app.id} value={app.id}>{app.name}</option>)}
      </select>
      <button type="button" className="button" onClick={() => setCreatingApp(true)} disabled={!tenantId}><Plus size={14} /> App</button>
    </div>
    {creatingTenant && <Modal title="Create tenant" onClose={() => setCreatingTenant(false)}><form onSubmit={submitTenant}><div className="form-grid"><div className="field"><label htmlFor="tenant-name">Name</label><input id="tenant-name" name="name" placeholder="IITDEVELOPER" required /></div><div className="field"><label htmlFor="tenant-slug">Slug</label><input id="tenant-slug" name="slug" placeholder="iitdeveloper" /></div></div>{createTenant.error && <div className="error-box">{createTenant.error.message}</div>}<div className="form-actions"><button className="button" type="button" onClick={() => setCreatingTenant(false)}>Cancel</button><button className="button primary" disabled={createTenant.isPending}>Create tenant</button></div></form></Modal>}
    {creatingApp && <Modal title="Create application" onClose={() => setCreatingApp(false)}><form onSubmit={submitApp}><div className="form-grid"><div className="field"><label htmlFor="app-name">Name</label><input id="app-name" name="name" placeholder="IITDEVELOPER App" required /></div><div className="field"><label htmlFor="app-slug">Slug</label><input id="app-slug" name="slug" placeholder="iitdeveloper-app" /></div></div>{createApp.error && <div className="error-box">{createApp.error.message}</div>}<div className="form-actions"><button className="button" type="button" onClick={() => setCreatingApp(false)}>Cancel</button><button className="button primary" disabled={createApp.isPending}>Create application</button></div></form></Modal>}
  </div>;
}
