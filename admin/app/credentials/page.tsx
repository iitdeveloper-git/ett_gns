"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {KeyRound, Plus, RefreshCw, ShieldX} from "lucide-react";
import {FormEvent, useState} from "react";
import {Modal} from "@/components/modal";
import {EmptyState, ErrorState, LoadingState, Status} from "@/components/query-state";
import {useWorkspace} from "@/components/workspace";
import {api, Credential, Page} from "@/lib/api";

type SecretCredential = Credential & {secret: string};

export default function CredentialsPage() {
  const {appId} = useWorkspace();
  const [creating, setCreating] = useState(false);
  const [revealed, setRevealed] = useState<SecretCredential | null>(null);
  const queryClient = useQueryClient();
  const query = useQuery({queryKey: ["credentials", appId], queryFn: () => api<Page<Credential>>(`/api/v1/apps/${appId}/credentials`), enabled: Boolean(appId)});
  const create = useMutation({
    mutationFn: (body: object) => api<SecretCredential>(`/api/v1/apps/${appId}/credentials`, {method: "POST", body: JSON.stringify(body)}),
    onSuccess: (credential) => {setCreating(false); setRevealed(credential); queryClient.invalidateQueries({queryKey: ["credentials", appId]});},
  });
  const rotate = useMutation({
    mutationFn: (id: string) => api<SecretCredential>(`/api/v1/credentials/${id}/rotate`, {method: "POST", body: JSON.stringify({overlap_seconds: 3600})}),
    onSuccess: (credential) => {setRevealed(credential); queryClient.invalidateQueries({queryKey: ["credentials", appId]});},
  });
  const revoke = useMutation({
    mutationFn: (id: string) => api(`/api/v1/credentials/${id}/revoke`, {method: "POST"}),
    onSuccess: () => queryClient.invalidateQueries({queryKey: ["credentials", appId]}),
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    create.mutate({name: data.get("name"), permissions: data.getAll("permissions"), expires_at: data.get("expires_at") || null});
  }
  return <>
    <header className="page-header"><div><h1>Credentials</h1><p>Create, rotate with overlap, monitor last use, and revoke application keys.</p></div><button className="button primary" onClick={() => setCreating(true)} disabled={!appId}><Plus size={16} /> Create key</button></header>
    {!appId ? <EmptyState title="Choose an application" detail="Credentials are issued to one application." /> : query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} /> : !query.data?.items.length ? <EmptyState title="No application keys" detail="Create a scoped key; its secret is shown only once." /> :
      <div className="card table-wrap"><table><thead><tr><th>Credential</th><th>Permissions</th><th>Last used</th><th>Status</th><th>Actions</th></tr></thead><tbody>{query.data.items.map((credential) => <tr key={credential.id}><td><strong>{credential.name}</strong><div className="mono muted">gns_{credential.key_prefix}.••••••••</div></td><td className="truncate">{credential.permissions.join(", ")}</td><td>{credential.last_used_at ? new Date(credential.last_used_at).toLocaleString() : "Never"}</td><td><Status value={credential.revoked_at ? "disabled" : "active"} /></td><td><div className="toolbar"><button className="button" onClick={() => rotate.mutate(credential.id)} disabled={Boolean(credential.revoked_at)}><RefreshCw size={14} /> Rotate</button><button className="button danger" onClick={() => revoke.mutate(credential.id)} disabled={Boolean(credential.revoked_at)}><ShieldX size={14} /> Revoke</button></div></td></tr>)}</tbody></table></div>}
    {creating && <Modal title="Create application key" onClose={() => setCreating(false)}><form onSubmit={submit}><div className="field"><label htmlFor="name">Key name</label><input id="name" name="name" placeholder="Production backend" required /></div><div className="field" style={{marginTop: 14}}><label>Permissions</label>{["notifications:send","notifications:read","notifications:cancel"].map((permission) => <label key={permission}><input type="checkbox" name="permissions" value={permission} defaultChecked={permission !== "notifications:cancel"} style={{width: "auto"}} /> {permission}</label>)}</div><div className="field" style={{marginTop: 14}}><label htmlFor="expires_at">Expires at (optional)</label><input id="expires_at" name="expires_at" type="datetime-local" /></div>{create.error && <div className="error-box">{create.error.message}</div>}<div className="form-actions"><button type="button" className="button" onClick={() => setCreating(false)}>Cancel</button><button className="button primary" disabled={create.isPending}><KeyRound size={14} /> Create key</button></div></form></Modal>}
    {revealed && <Modal title="Copy this secret now" onClose={() => setRevealed(null)}><div className="error-box">This application key will not be shown again. Store it in your secret manager. Do not paste it into chat, screenshots, logs, tickets, source control, or frontend code.</div><pre className="secret-box mono">{revealed.secret}</pre><div className="form-actions"><button className="button primary" onClick={() => navigator.clipboard.writeText(revealed.secret)}>Copy secret</button><button className="button" onClick={() => setRevealed(null)}>I stored it</button></div></Modal>}
  </>;
}
