# MISIEK AI Guardian Platform

`guardian-interfaces` defines the shared contracts (messages, services, state
definitions) that every other component depends on.

| Group | Components |
|---|---|
| Robot runtime | `guardian-core`, `guardian-safety-layer`, `guardian-mission-manager`, `guardian-navigation`, `guardian-perception`, `guardian-go2-driver`, `guardian-ai-engine`, `guardian-voice`, `guardian-telemetry` |
| User interfaces | `guardian-mobile`, `guardian-web`, `guardian-command-center` |
| Operations | `guardian-monitoring`, `guardian-backup`, `guardian-testing`, `guardian-devops`, `guardian-installer`, `guardian-docs`, `guardian-digital-twin` |

Only `guardian-core` is implemented (state machine, watchdog, health monitor,
command dispatcher, snapshot/recovery). All other directories are placeholders
that describe their intended responsibility.
