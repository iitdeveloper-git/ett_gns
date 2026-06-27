import http from "k6/http";
import {check, sleep} from "k6";

export const options = {
  scenarios: {
    unread_count: {executor: "constant-vus", vus: 20, duration: "30s"},
  },
};

const BASE = __ENV.GNS_BASE_URL || "http://127.0.0.1:5000";

export default function () {
  const headers = {
    Authorization: `Bearer ${__ENV.GNS_USER_TOKEN || "dev_user_usr_123"}`,
    "X-Tenant-ID": __ENV.GNS_TENANT_ID || "tnt_demo",
    "X-App-ID": __ENV.GNS_APP_ID || "app_demo",
    "X-Session-ID": `k6-${__VU}`,
  };
  const response = http.get(`${BASE}/api/v1/in-app/unread-count`, {headers});
  check(response, {"unread count ok": (r) => r.status === 200});
  sleep(1);
}
