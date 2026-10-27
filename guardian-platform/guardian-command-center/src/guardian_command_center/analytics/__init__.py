"""Analytics over incidents, missions and fleet snapshots. No data gives None, never 0."""


def mean_time_to_ack(incidents):
    times = [i["acked"] - i["opened"] for i in incidents if i["acked"] is not None]
    return sum(times) / len(times) if times else None


def incidents_by_severity(incidents):
    out = {}
    for i in incidents:
        out[i["severity"]] = out.get(i["severity"], 0) + 1
    return dict(sorted(out.items()))


def unresolved(incidents):
    return sum(1 for i in incidents if i["status"] != "resolved")


def mission_success_rate(missions):
    """done / (done + aborted); in-flight missions are ignored."""
    done = sum(1 for m in missions if m["state"] == "done")
    aborted = sum(1 for m in missions if m["state"] == "aborted")
    return done / (done + aborted) if done + aborted else None


def availability(samples):
    """samples: list of fleet status dicts {robot_id: 'online'|'stale'|...} taken over time.
    Returns the fraction of robot-samples that were online."""
    total = online = 0
    for snap in samples:
        for status in snap.values():
            total += 1
            online += status == "online"
    return online / total if total else None
