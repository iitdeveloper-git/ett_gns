# Template system

Identity is application + event + channel + locale + variant. Versions move through draft, validated, published, deprecated and archived states.

Validation checks:

- required channel fields
- Jinja syntax in a restricted `SandboxedEnvironment`
- strict undefined variables
- variables declared by the event JSON Schema
- sample data against the schema
- content size
- email HTML allowlist and safe URL protocols
- forbidden template introspection constructs

Publication is allowed only after successful validation. Published content cannot be edited. New work creates a subsequent draft version; rollback selects a previously published immutable version.

Locale fallback is requested locale, application default, platform default. Variant fallback is requested variant, then `default`.
