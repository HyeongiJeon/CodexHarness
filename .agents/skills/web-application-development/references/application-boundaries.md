# Application boundaries

Trace one user action through UI state, route/API contract, validation, persistence, and response. Give each state a clear owner; avoid duplicating authoritative state across client and server. Validate untrusted input at its receiving boundary, keep credentials server-side, and preserve existing access checks. For asynchronous work make loading, empty, success, and failure states observable. Verify with local HTTP requests and user-operated preview, covering submission, navigation, refresh/persistence, and representative failures without browser or GUI automation.
