import http from "k6/http";
import {check} from "k6";

export const options = {vus: 20, iterations: 200};
const key = `duplicate-${Date.now()}`;

export default function () {
  const response = http.post(
    `${__ENV.GNS_URL}/api/v1/notifications`,
    __ENV.GNS_PAYLOAD,
    {headers: {Authorization: `Bearer ${__ENV.GNS_API_KEY}`, "Content-Type": "application/json", "Idempotency-Key": key}},
  );
  check(response, {"same request accepted": (result) => result.status === 202});
}
