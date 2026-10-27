# guardian-mission-manager

Mission planning and execution for MISIEK AI Guardian: patrols, scheduling,
lifecycle and crash recovery. Pure Python, no dependencies; not yet wired to
`guardian-core` or `guardian-navigation`.

| Module | Responsibility |
|---|---|
| `route_manager` | `Waypoint`, `Route` (length, reverse) and a registry |
| `planner` | Builds a `MissionPlan` (loops, optional return to base) into ordered steps |
| `scheduler` | Time- and priority-ordered start queue with cancel (injectable clock) |
| `mission_fsm` | `PLANNED`, `RUNNING`, `PAUSED`, `COMPLETED`, `ABORTED` or `FAILED`; terminal states are final |
| `checkpoint_manager` | Atomic JSON checkpoints (rejects path-like mission ids) |
| `recovery` | Finds interrupted missions and resumes them from the last checkpoint |

On resume, the step that was in flight (`next_step`) is repeated rather than
skipped, so steps must be safe to repeat.

```
make test
```
