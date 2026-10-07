# ins-clock

A server-independent obligations clock. A GitHub Actions workflow wakes every 5 minutes, reads this repo's Actions variables, and turns due ones into issues in a private task repo.

This repo is public on purpose: it holds only the workflow and this README. No data, no secrets. Logs are public, so the workflow prints counts only, never names or values.

## Variable = one obligation

Name (UPPERCASE, GitHub forces uppercase and forbids a leading digit or hyphens):

    T<YYYYMMDD>_<HHMM>__<REC>__<ID>[__U<YYYYMMDD>]

- `T<YYYYMMDD>_<HHMM>`: next due time, always UTC.
- `<REC>`: `ONCE` or `P<n><unit>`, with unit `MI` (minutes), `H`, `D`, `W`, `MO` (months). A trailing `L` means the step is added in Africa/Cairo wall-clock time (keeps 00:00/06:00 local across DST); without `L` the step is added in UTC.
- `<ID>`: short unique token, letters and digits only (no underscore).
- `__U<YYYYMMDD>` (optional): last UTC date; the obligation is retired when the next occurrence would pass it.

Examples:

    T20261008_1600__ONCE__POST1          one-shot
    T20261007_2100__P6HL__ELEC           every 6h Cairo wall-clock, next due 2026-10-07 21:00 UTC
    T20261107_0800__P1MOL__BENCH         monthly, Cairo wall-clock

Value = the obligation body (what to do, plus references). Values are not publicly readable.

## Each run

1. List variables, decode names, pick those due (<= now UTC).
2. For each: create an issue in the private task repo (title = variable name, body = value + due/next footer), assigned to the Ins account. Skip creation if an issue with that title already exists.
3. Recurring: rename the variable to the next occurrence after now (missed occurrences are skipped, not queued). One-shot or past its end: delete the variable.
4. Daily around 03:00 UTC: update `heartbeat.txt` so GitHub does not disable the schedule after 60 days of inactivity.

Auth: the Actions secret `CLOCK_PAT` (fine-grained PAT limited to these two repos). The default token cannot write Variables.
