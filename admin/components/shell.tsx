"use client";

import {
  Activity, AppWindow, Bell, FileCode2, Gauge, KeyRound, RadioTower,
  ScrollText, ShieldCheck, Inbox,
} from "lucide-react";
import Link from "next/link";
import {usePathname} from "next/navigation";
import {WorkspaceSelectors} from "@/components/workspace-selectors";

const nav = [
  ["/", "Dashboard", Gauge],
  ["/applications", "Applications", AppWindow],
  ["/events", "Events", RadioTower],
  ["/templates", "Templates", FileCode2],
  ["/providers", "Providers", ShieldCheck],
  ["/in-app", "In-App", Inbox],
  ["/notifications", "Notifications", Bell],
  ["/credentials", "Credentials", KeyRound],
  ["/audits", "Audits", ScrollText],
] as const;

export function Shell({children}: {children: React.ReactNode}) {
  const pathname = usePathname();
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
          <WorkspaceSelectors />
        </div>
        <div className="identity"><span className="identity-dot" /><span>Local platform admin</span></div>
      </header>
      <div className="content">{children}</div>
    </main>
  </div>;
}
