# Template and Event System

## Template identity

```text
application + event + channel + locale + variant
```

## Version lifecycle

```text
draft -> validated -> published -> deprecated -> archived
```

Published versions are immutable.

## Event schemas

Use JSON Schema to validate runtime data and template variables.

## Localization fallback

```text
requested locale -> app default -> platform default -> fail
```

## Channel content

- Email: subject, HTML, text
- SMS: text
- Webhook: headers and JSON body
- Push: title/body/image/deep link
- WhatsApp: provider template name, language, parameters
- Telegram: body, parse mode, buttons/media

## Publish checks

- Syntax valid
- Variables declared in schema
- Required fields present
- Safe HTML
- Size limits
- Test data renders
- Provider-specific rules pass
