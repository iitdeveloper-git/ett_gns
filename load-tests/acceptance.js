import http from "k6/http";
import {check} from "k6";

export const options = {
  scenarios: {
    acceptance: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RATE || 10),
      timeUnit: "1s",
      duration: __ENV.DURATION || "1m",
      preAllocatedVUs: Number(__ENV.VUS || 20),
      maxVUs: Number(__ENV.MAX_VUS || 100),
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<250"],
  },
};

export default function () {
  const id = `${__VU}-${__ITER}`;
  const response = http.post(
    `${__ENV.GNS_URL}/api/v1/notifications`,
    JSON.stringify({
      app_id: __ENV.GNS_APP_ID,
      event_key: __ENV.GNS_EVENT_KEY,
      channel: __ENV.GNS_CHANNEL || "email",
      recipient: {email: __ENV.GNS_RECIPIENT || "load@example.test"},
      data: JSON.parse(__ENV.GNS_EVENT_DATA || "{\"name\":\"Load Test\"}"),
      metadata: {source: "k6", correlation_id: `load-${id}`},
    }),
    {
      headers: {
        Authorization: `Bearer ${__ENV.GNS_API_KEY}`,
        "Content-Type": "application/json",
        "Idempotency-Key": `load-${id}`,
      },
    },
  );
  check(response, {"accepted": (result) => result.status === 202});
}
