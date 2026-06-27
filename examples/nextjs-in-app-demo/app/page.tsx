"use client";

import {GnsNotificationBell, GnsNotificationCenter, GnsProvider, GnsToastContainer} from "@iitdeveloper/gns-in-app";

export default function DemoPage() {
  return <GnsProvider options={{
    apiUrl: process.env.NEXT_PUBLIC_GNS_API_URL ?? "http://127.0.0.1:5000",
    tenantId: process.env.NEXT_PUBLIC_GNS_TENANT_ID ?? "tnt_demo",
    applicationId: process.env.NEXT_PUBLIC_GNS_APP_ID ?? "app_demo",
    getAccessToken: () => "dev_user_usr_123",
    sessionId: "demo-web",
  }}>
    <main style={{fontFamily: "system-ui", padding: 32}}>
      <h1>GNS In-App Demo</h1>
      <GnsNotificationBell />
      <GnsNotificationCenter />
      <GnsToastContainer />
    </main>
  </GnsProvider>;
}
