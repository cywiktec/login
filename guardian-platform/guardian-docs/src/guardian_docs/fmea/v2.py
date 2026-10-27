"""FMEA v2.0 data: failure modes per component, tied to the mitigations actually implemented.

All S/O/D ratings are the author's estimates for review, not field data. `verified_by` cites
a test in this monorepo; an empty value means no test evidence exists (a gap, not a pass).
"""

from . import FailureMode as F

VERSION = "2.0"


def modes():
    return [
        # --- safety-layer / ai-engine / voice: command path ---
        F("F-001", "safety-layer", "E-stop command not delivered", "Robot keeps moving", 10, 2, 4,
          "E-stop allowed from every source and state; latched until explicit reset",
          "guardian-safety-layer test_latches_and_notifies_once; guardian-testing safety invariants"),
        F("F-002", "safety-layer", "FSM leaves EMERGENCY_STOP without operator action", "Robot restarts motion", 10, 2, 3,
          "reset() raises at EMERGENCY_STOP; only clear_emergency_stop() leaves it",
          "guardian-testing safety (FSM invariants)"),
        F("F-003", "safety-layer", "Geofence polygon wrong or too permissive", "Robot leaves the allowed area", 9, 3, 5,
          "Polygon validated (>= 3 vertices); boundary counts as inside; simulation latches e-stop on breach",
          "guardian-safety-layer test_inside_outside_and_edge; guardian-digital-twin scenarios"),
        F("F-004", "safety-layer", "Heartbeat/watchdog stops being evaluated", "Hung control loop goes unnoticed", 9, 3, 6,
          "Per-source expiry: a silent heartbeat source expires", "guardian-safety-layer watchdog test_expiry_per_source"),
        F("F-005", "ai-engine", "LLM misreads intent", "Wrong actuating command executed", 8, 5, 4,
          "LLM actuating intents need confidence >= 0.8; policy by state and source",
          "guardian-ai-engine policy tests"),
        F("F-006", "ai-engine", "Untrusted source issues a command", "Unauthorised actuation", 9, 3, 3,
          "Sources 'none' and 'web' are denied everything except emergency_stop",
          "guardian-ai-engine policy tests"),
        F("F-007", "ai-engine", "Unknown state while evaluating policy", "Command allowed in an unknown situation", 8, 2, 4,
          "Unknown state denies all non-read-only intents", "guardian-ai-engine policy tests"),
        F("F-008", "voice", "Speech misrecognised as a command", "Unintended command", 7, 5, 5,
          "Wake word required; STT confidence >= 0.6; NaN confidence rejected; bare 'stop' only for e-stop",
          "guardian-voice tests"),
        F("F-009", "voice", "Noise suppresses the spoken 'stop'", "E-stop not recognised", 9, 4, 6,
          "No technical mitigation beyond bare-stop path; physical e-stop button required (not in software)", ""),
        # --- go2-driver / perception: sensing ---
        F("F-010", "go2-driver", "Telemetry stops or ages", "Decisions on stale state", 8, 4, 3,
          "latest(max_age) returns nothing when stale; consumers fail closed", "guardian-go2-driver tests"),
        F("F-011", "go2-driver", "Malformed telemetry frame", "Garbage values enter the system", 7, 4, 2,
          "parse_state rejects non-finite and missing fields", "guardian-go2-driver tests"),
        F("F-012", "go2-driver", "Battery reading wrong", "Mission started on a dying battery", 7, 3, 5,
          "Battery guard levels and threshold validation", "guardian-safety-layer test_levels, test_invalid_thresholds"),
        F("F-013", "perception", "Lidar returns NaN/inf for a sector", "Obstacle treated as free space", 9, 4, 3,
          "min_distance returns None (unknown) when too many readings are unusable; callers must treat as obstacle",
          "guardian-perception lidar tests"),
        F("F-014", "perception", "Camera frame stale", "Detections from the past", 6, 4, 3,
          "CameraSource.latest() returns None when stale", "guardian-perception camera tests"),
        F("F-015", "perception", "Person not detected", "No person-in-zone event", 8, 4, 7,
          "None in software: depends on the (external) model; thresholds untuned", ""),
        F("F-016", "perception", "Tracker swaps identities", "Wrong object history", 4, 5, 6,
          "IoU association with same-label constraint", "guardian-perception tracker tests"),
        # --- mission / navigation / core ---
        F("F-017", "mission-manager", "Mission interrupted by power loss", "Mission cannot resume", 6, 4, 3,
          "Checkpoint manager and recovery", "guardian-mission-manager test_interrupted_and_resume"),
        F("F-018", "navigation", "Waypoint outside geofence", "Route leaves the allowed area", 8, 3, 3,
          "Map geofence applied to the planning grid, so the planner is confined", "guardian-navigation test_apply_to_grid_confines_planner"),
        F("F-019", "core", "Corrupt snapshot used for recovery", "Robot resumes in a wrong state", 9, 3, 3,
          "RecoveryEngine verifies schema and SHA-256; falls back to older snapshot; FAILED if none",
          "guardian-core test_recovery_engine"),
        F("F-020", "core", "Recovery reports READY while unhealthy", "False sense of recovery", 8, 3, 4,
          "success requires health score >= 80; NaN rejected; health check injectable", "guardian-core test_recovery_engine"),
        F("F-021", "core", "Journal entry corrupt during replay", "Partial replay hides lost actions", 7, 3, 3,
          "Any corrupt entry fails the whole recovery", "guardian-core test_recovery_engine"),
        # --- data, backup, telemetry ---
        F("F-022", "backup", "Snapshot torn on power loss", "Lost resume point", 5, 3, 2,
          "Atomic write (temp, fsync, rename, fsync dir) + hash verify", "guardian-backup tests"),
        F("F-023", "backup", "Journal tail torn or tampered", "Corrupt history trusted", 6, 3, 2,
          "Hash chain; torn tail detected and truncated", "guardian-backup tests"),
        F("F-024", "backup", "Retention deletes the only valid snapshot", "No recovery possible", 9, 2, 2,
          "Never deletes the newest valid snapshot", "guardian-backup tests"),
        F("F-025", "telemetry", "Slow client blocks the hub", "Telemetry delay for all clients", 5, 4, 4,
          "Bounded per-client queues", "guardian-telemetry tests"),
        F("F-026", "telemetry", "Broker down", "No telemetry to the operators", 7, 4, 3,
          "Monitoring alerts on missing data; in-memory broker only - no real transport", ""),
        # --- operations ---
        F("F-027", "monitoring", "Stale data exported as healthy", "Operators see a green dashboard", 8, 3, 4,
          "guardian_up = 0 when data is stale", "guardian-monitoring tests"),
        F("F-028", "monitoring", "Alert rules wrong or never loaded", "No alert on a real fault", 8, 4, 6,
          "Rules generated from code; NOT validated with promtool/amtool", ""),
        F("F-029", "command-center", "Command issued by an unauthorised role", "Unauthorised actuation", 9, 3, 3,
          "Role check per command; unknown role refused; no authentication exists yet", "guardian-command-center tests"),
        F("F-030", "command-center", "Queued e-stop lost on restart", "E-stop not delivered", 10, 3, 6,
          "None: queue is in memory", ""),
        F("F-031", "web", "Report injection (HTML/CSV formulas)", "Operator browser/spreadsheet compromised", 6, 3, 3,
          "HTML escaped; CSV formula guard", "guardian-web tests"),
        F("F-032", "devops", "Secret committed to the repository", "Credential leak", 8, 4, 5,
          "Heuristic secret scanner; env refs only in compose", "guardian-devops tests"),
        F("F-033", "devops", "Tampered release artifact", "Malicious code deployed", 9, 2, 5,
          "SHA-256 manifest verified before use; no signing", "guardian-devops tests"),
        F("F-034", "installer", "Installer changes the system unexpectedly", "Broken host", 6, 3, 3,
          "Dry run by default; preflight; resumable with rollback", "guardian-installer tests"),
        F("F-035", "installer", "ROS repository key not pinned", "Supply-chain compromise", 8, 2, 7,
          "None: key fetched over HTTPS without fingerprint pinning", ""),
        F("F-036", "interfaces", "State enum drifts between Python/ROS/protobuf/OpenAPI", "Components disagree on state", 7, 5, 6,
          "Documented rule only; no automatic check", ""),
    ]
