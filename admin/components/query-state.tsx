"use client";

import {AlertTriangle, Inbox, LoaderCircle} from "lucide-react";

export function LoadingState({label = "Loading data"}: {label?: string}) {
  return <div className="state"><div><LoaderCircle aria-hidden className="spin" /><strong>{label}</strong><span>Connecting to GNS…</span></div></div>;
}

export function EmptyState({title, detail}: {title: string; detail: string}) {
  return <div className="state"><div><Inbox aria-hidden /><strong>{title}</strong><span>{detail}</span></div></div>;
}

export function ErrorState({error}: {error: Error}) {
  return <div className="state"><div><AlertTriangle aria-hidden /><strong>Couldn’t load this view</strong><span>{error.message}</span></div></div>;
}

export function Status({value}: {value: string}) {
  return <span className={`status ${value}`}>{value.replaceAll("_", " ")}</span>;
}
