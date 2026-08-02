# Performance Budgets

The bounded automated stability gate runs `py -3 tools/performance_soak.py` in the verification data root. Its current budgets are:

- 5,000 named timer replacement/cancel cycles with zero owned callbacks left;
- 10,000 runtime pause transitions;
- 250 SQLite task start/complete lifecycles;
- database file no larger than 2 MB after the disposable workload;
- peak traced Python allocation no larger than 64 MB;
- total execution no longer than 15 seconds.

These are regression budgets for core services, not a substitute for live Tk, native Windows, browser, camera, or long-duration user-session measurements.
