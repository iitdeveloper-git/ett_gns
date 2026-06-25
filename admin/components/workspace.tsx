"use client";

import {createContext, useContext, useEffect, useState} from "react";

type Workspace = {
  tenantId: string;
  appId: string;
  setTenantId: (value: string) => void;
  setAppId: (value: string) => void;
};
const WorkspaceContext = createContext<Workspace | null>(null);

export function WorkspaceProvider({children}: {children: React.ReactNode}) {
  const [tenantId, setTenantIdState] = useState(process.env.NEXT_PUBLIC_GNS_TENANT_ID ?? "");
  const [appId, setAppIdState] = useState(process.env.NEXT_PUBLIC_GNS_APP_ID ?? "");
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setTenantIdState((current) => localStorage.getItem("gns.tenantId") ?? current);
      setAppIdState((current) => localStorage.getItem("gns.appId") ?? current);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);
  const setTenantId = (value: string) => {
    setTenantIdState(value);
    localStorage.setItem("gns.tenantId", value);
  };
  const setAppId = (value: string) => {
    setAppIdState(value);
    localStorage.setItem("gns.appId", value);
  };
  return <WorkspaceContext.Provider value={{tenantId, appId, setTenantId, setAppId}}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("WorkspaceProvider missing");
  return value;
}
