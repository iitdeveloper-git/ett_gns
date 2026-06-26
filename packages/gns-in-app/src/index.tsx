"use client";

import React, {createContext, useCallback, useContext, useEffect, useMemo, useState} from "react";
import "./styles.css";

export type GnsNotification = {
  id: string;
  event_key: string;
  title: string;
  message: string;
  severity: "info" | "success" | "warning" | "error" | "critical";
  priority: number;
  action_payload: {label?: string; url?: string; type?: "deep_link"};
  toast_payload: {enabled?: boolean; auto_dismiss_ms?: number};
  created_at: string;
  read: boolean;
};

type GnsClientOptions = {
  apiUrl: string;
  getAccessToken: () => Promise<string> | string;
  tenantId: string;
  applicationId: string;
  sessionId?: string;
  userId?: string;
};

type GnsContextValue = {
  notifications: GnsNotification[];
  unread: number;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
  dismiss: (id: string) => Promise<void>;
};

const GnsContext = createContext<GnsContextValue | null>(null);

async function authHeaders(options: GnsClientOptions) {
  const token = await options.getAccessToken();
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
    "X-Tenant-ID": options.tenantId,
    "X-App-ID": options.applicationId,
    "X-Session-ID": options.sessionId ?? "web",
  };
}

export function GnsProvider({children, options}: {children: React.ReactNode; options: GnsClientOptions}) {
  const [notifications, setNotifications] = useState<GnsNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const headers = await authHeaders(options);
      const [list, count] = await Promise.all([
        fetch(`${options.apiUrl}/api/v1/in-app/notifications`, {headers}).then((response) => response.json()),
        fetch(`${options.apiUrl}/api/v1/in-app/unread-count`, {headers}).then((response) => response.json()),
      ]);
      setNotifications(list.items ?? []);
      setUnread(count.unread ?? 0);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error("Failed to fetch notifications"));
    } finally {
      setLoading(false);
    }
  }, [options]);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    void (async () => {
      const headers = await authHeaders(options);
      const response = await fetch(`${options.apiUrl}/api/v1/in-app/stream`, {headers, signal: controller.signal});
      const reader = response.body?.getReader();
      if (!reader) return;
      const decoder = new TextDecoder();
      let buffer = "";
      while (!cancelled) {
        const {done, value} = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, {stream: true});
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";
        for (const chunk of chunks) {
          const event = chunk.split("\n").find((line) => line.startsWith("event: "))?.slice(7);
          const data = chunk.split("\n").find((line) => line.startsWith("data: "))?.slice(6);
          if (!data || !event?.startsWith("notification.")) continue;
          const item = JSON.parse(data) as GnsNotification;
          setNotifications((current: GnsNotification[]) => event === "notification.created" ? [item, ...current.filter((existing: GnsNotification) => existing.id !== item.id)] : current.map((existing: GnsNotification) => existing.id === item.id ? item : existing));
          void refresh();
        }
      }
    })();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [options, refresh]);
  const markRead = useCallback(async (id: string) => {
    const headers = await authHeaders(options);
    await fetch(`${options.apiUrl}/api/v1/in-app/notifications/${id}/read`, {method: "POST", headers});
    await refresh();
  }, [options, refresh]);
  const markAllRead = useCallback(async () => {
    const headers = await authHeaders(options);
    await fetch(`${options.apiUrl}/api/v1/in-app/notifications/read-all`, {method: "POST", headers});
    await refresh();
  }, [options, refresh]);
  const dismiss = useCallback(async (id: string) => {
    const headers = await authHeaders(options);
    await fetch(`${options.apiUrl}/api/v1/in-app/notifications/${id}/dismiss`, {method: "POST", headers});
    await refresh();
  }, [options, refresh]);
  const value = useMemo(() => ({notifications, unread, loading, error, refresh, markRead, markAllRead, dismiss}), [notifications, unread, loading, error, refresh, markRead, markAllRead, dismiss]);
  return <GnsContext.Provider value={value}>{children}</GnsContext.Provider>;
}

export function useGnsNotifications() {
  const context = useContext(GnsContext);
  if (!context) throw new Error("GnsProvider is missing");
  return context;
}

export const useGnsUnreadCount = () => useGnsNotifications().unread;
export const useGnsNotificationStream = useGnsNotifications;
export const useGnsNotificationPreferences = useGnsNotifications;

export function GnsNotificationBell() {
  const {unread} = useGnsNotifications();
  return <button className="gns-bell" aria-label={`${unread} unread notifications`}>🔔<span>{unread > 99 ? "99+" : unread}</span></button>;
}

export function GnsNotificationCenter() {
  const {notifications, loading, error, markRead, markAllRead, dismiss} = useGnsNotifications();
  if (loading) return <div className="gns-center">Loading notifications…</div>;
  if (error) return <div className="gns-center" role="alert">{error.message}</div>;
  return <section className="gns-center"><header><h2>Notifications</h2><button onClick={markAllRead}>Mark all read</button></header>{notifications.length === 0 ? <p>No notifications.</p> : notifications.map((item) => <GnsNotificationItem key={item.id} notification={item} onRead={() => markRead(item.id)} onDismiss={() => dismiss(item.id)} />)}</section>;
}

export function GnsNotificationItem({notification, onRead, onDismiss}: {notification: GnsNotification; onRead: () => void; onDismiss: () => void}) {
  return <article className={`gns-item ${notification.severity} ${notification.read ? "read" : "unread"}`}><div><strong>{notification.title}</strong><p>{notification.message}</p><time>{new Date(notification.created_at).toLocaleString()}</time></div><div className="gns-actions">{notification.action_payload?.url && <a href={notification.action_payload.url}>{notification.action_payload.label ?? "Open"}</a>}<button onClick={onRead}>Read</button><button onClick={onDismiss}>Dismiss</button></div></article>;
}

export function GnsToastContainer() {
  const {notifications, dismiss} = useGnsNotifications();
  const visible = notifications.filter((item) => !item.read && item.toast_payload?.enabled !== false).slice(0, 4);
  return <div className="gns-toasts" aria-live="polite">{visible.map((item) => <div key={item.id} className={`gns-toast ${item.severity}`}><strong>{item.title}</strong><p>{item.message}</p><button aria-label="Dismiss notification" onClick={() => dismiss(item.id)}>×</button></div>)}</div>;
}
