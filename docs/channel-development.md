# Channel development

Implement the `ChannelAdapter` protocol in `ett_gns_app/channels/contracts.py`:

- validate provider configuration
- validate recipient
- validate channel content
- return normalized `SendResult`
- raise `AdapterError` with stable code and retryability

Register the provider type in `adapter_for`. Add:

- deterministic fake behavior
- HTTP/mock-server contract tests
- timeout and error classification tests
- recipient/content safety tests
- callback normalization only for statuses the provider actually emits

Do not add provider-specific fields to the runtime request contract.
