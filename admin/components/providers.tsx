"use client";

import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {useState} from "react";
import {WorkspaceProvider} from "@/components/workspace";

export function Providers({children}: {children: React.ReactNode}) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: {queries: {staleTime: 10_000, retry: 1}},
  }));
  return <QueryClientProvider client={client}><WorkspaceProvider>{children}</WorkspaceProvider></QueryClientProvider>;
}
