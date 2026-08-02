# Prompt State Machine

`idle -> scheduled -> visible -> submitted -> completed` is the normal path.

`visible -> snoozed` records a durable snooze expiry and closes the prompt.

`visible -> intervention_active -> visible` occurs when an intervention is cancelled or fails.

`visible -> completed` is allowed only after valid response/intervention completion. Close/exception cleanup is idempotent and must not log success.
