# Channels and Providers

## Email

Adapters: SMTP, SES, SendGrid, Mailgun, Postmark.

Features: HTML/text, attachments, reply-to, callbacks, bounce/complaint handling.

## SMS

Adapters: Twilio, AWS SNS, Exotel, MSG91.

Features: E.164 validation, sender ID, template IDs, delivery receipts, segment counting.

## Webhook

Features: HMAC signature, timestamp, replay protection, timeout, retry, circuit breaker, destination policy.

## Push

Adapters: FCM, APNs, OneSignal.

Features: device token, topic, TTL, collapse key, image, deep link.

## WhatsApp

Adapters: Meta Cloud API, Twilio, BSPs.

Special rules:

- approved templates for business-initiated messages
- opt-in evidence
- template language/category
- 24-hour service window
- media handling
- provider rate tiers

## Telegram

Adapter: Telegram Bot API.

Features: chat ID, Markdown/HTML parse mode, media, inline keyboard, webhook secret.

## Future channels

Slack, Teams, Discord, in-app inbox, voice, IoT.

## Provider selection

```text
event-specific provider
-> app channel provider
-> tenant provider
-> global default if policy permits
-> fail
```
