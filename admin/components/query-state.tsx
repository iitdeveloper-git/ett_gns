"use client";

import {AlertTriangle, Inbox, LoaderCircle} from "lucide-react";
import {ApiError} from "@/lib/api";

export function LoadingState({label = "Loading data"}: {label?: string}) {
  return <div className="state"><div><LoaderCircle aria-hidden className="spin" /><strong>{label}</strong><span>Connecting to GNS…</span></div></div>;
}

export function EmptyState({title, detail}: {title: string; detail: string}) {
  return <div className="state"><div><Inbox aria-hidden /><strong>{title}</strong><span>{detail}</span></div></div>;
}

export function ErrorState({error}: {error: Error}) {
  const apiError = error instanceof ApiError ? error : null;
  return <div className="state"><div><AlertTriangle aria-hidden /><strong>Couldn’t load this view</strong><span>{error.message}</span>{apiError?.code && <span className="mono">Code: {apiError.code}</span>}{apiError?.requestId && <span className="mono">Request: {apiError.requestId}</span>}<span>Try refreshing, checking workspace scope, or opening the related setup screen.</span></div></div>;
}

export function Status({value}: {value: string}) {
  return <span className={`status ${value}`}>{value.replaceAll("_", " ")}</span>;
}
