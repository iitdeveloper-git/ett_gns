"use client";

import {
  Activity, AppWindow, Bell, FileCode2, Gauge, KeyRound, RadioTower,
  ScrollText, ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import {usePathname} from "next/navigation";
import {useWorkspace} from "@/components/workspace";

const nav = [
  ["/", "Dashboard", Gauge],
  ["/applications", "Applications", AppWindow],
  ["/events", "Events", RadioTower],
  ["/templates", "Templates", FileCode2],
  ["/providers", "Providers", ShieldCheck],
  ["/notifications", "Notifications", Bell],
  ["/credentials", "Credentials", KeyRound],
  ["/audits", "Audits", ScrollText],
] as const;

export function Shell({children}: {children: React.ReactNode}) {
  const pathname = usePathname();
  const {tenantId, appId, setTenantId, setAppId} = useWorkspace();
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">G</div><div><strong>GNS Console</strong><span>Operations control plane</span></div></div>
      <div className="nav-label">Workspace</div>
      <nav aria-label="Primary navigation">
        {nav.map(([href, label, Icon]) => <Link key={href} href={href} className={`nav-link ${pathname === href ? "active" : ""}`}><Icon aria-hidden /><span>{label}</span></Link>)}
      </nav>
    </aside>
    <main className="main">
      <header className="topbar">
        <div className="workspace-fields">
          <Activity aria-hidden size={17} color="var(--accent)" />
          <label htmlFor="tenant-id">Tenant</label>
          <input id="tenant-id" className="workspace-input mono" value={tenantId} onChange={(event) => setTenantId(event.target.value)} placeholder="tnt_…" />
          <label htmlFor="app-id">App</label>
          <input id="app-id" className="workspace-input mono" value={appId} onChange={(event) => setAppId(event.target.value)} placeholder="app_…" />
        </div>
        <div className="identity"><span className="identity-dot" /><span>Local platform admin</span></div>
      </header>
      <div className="content">{children}</div>
    </main>
  </div>;
}
