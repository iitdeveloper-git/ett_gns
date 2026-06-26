export const API_URL = process.env.NEXT_PUBLIC_GNS_API_URL ?? "http://127.0.0.1:5000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
    readonly requestId?: string,
  ) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-User": "gns-local-admin",
      "X-Admin-Roles": "platform_admin",
      ...(options.headers ?? {}),
    },
  });
  if (response.status === 204) return undefined as T;
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail ?? payload.error ?? {};
    throw new ApiError(
      detail.message ?? `Request failed with HTTP ${response.status}`,
      response.status,
      detail.code,
      detail.request_id,
    );
  }
  return payload as T;
}

export type Page<T> = {items: T[]; total: number; limit: number; offset: number};
export type Tenant = {
  id: string; name: string; slug: string; status: string; created_at: string; updated_at: string;
};
export type Application = {
  id: string; tenant_id: string; name: string; slug: string; status: string;
  default_locale: string; timezone: string; quota_per_minute: number; quota_per_day: number;
};
export type EventRecord = {
  id: string; application_id: string; event_key: string; status: string;
  allowed_channels: string[]; current_schema_version: number;
};
export type TemplateRecord = {
  id: string; application_id: string; event_id: string; channel: string;
  locale: string; variant: string; status: string; published_version: number | null;
};
export type Provider = {
  id: string; application_id: string | null; channel: string; provider_type: string;
  name: string; active: boolean; is_default: boolean; health_status: string;
  fallback_policy: string; secret_configured: boolean;
};
export type NotificationRecord = {
  id: string; application_id: string; event_key: string; channel: string;
  status: string; correlation_id: string | null; created_at: string; failure_code: string | null;
};
export type Credential = {
  id: string; application_id: string; name: string; key_prefix: string;
  permissions: string[]; expires_at: string | null; last_used_at: string | null;
  revoked_at: string | null;
};
