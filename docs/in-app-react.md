# In-App React Example

```tsx
<GnsProvider options={{
  apiUrl: "https://gns.example.com",
  tenantId: "tnt_...",
  applicationId: "app_...",
  getAccessToken: async () => accessToken,
  sessionId: "ses_web"
}}>
  <GnsNotificationBell />
  <GnsNotificationCenter />
  <GnsToastContainer />
</GnsProvider>
```

The demo app is in `examples/nextjs-in-app-demo`.

