# Android fixtures

Raw adb output captured from emulators by `tools/android/capture_fixtures.sh` (workflow
`capture-android-fixtures`). Each command has `NAME.out` (stdout), `NAME.err` (stderr, only if
non-empty) and `NAME.code` (exit code). **Do not edit these by hand** — re-capture instead.

| Directory | Image |
|---|---|
| `emulator_api30/` | Android 11, google_apis x86_64, pixel_6 profile |
| `emulator_api34/` | Android 14, google_apis x86_64, pixel_6 profile |

Real-phone fixtures go in `<brand>_<model>_api<N>/`; strip anything personal first (notification
text, contact names, account e-mails) — CLAUDE.md §6.3.
