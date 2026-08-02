# Settings Schema Map

- Current schema: `2`.
- Validation is applied after pure migration and before persistence.
- Unknown keys are retained for forward compatibility but diagnostic output records only their type.
- Boolean, numeric, enum, date, website flag, and snooze fields are normalized/clamped.
- Invalid calendar dates are rejected using `datetime.date`.
- Save protocol: validate, same-directory unique temp, flush/fsync, backup existing file, atomic replace, explicit boolean result.
- Load protocol: parse, migrate, validate; quarantine malformed active file; recover `.bak`; otherwise return defaults.
