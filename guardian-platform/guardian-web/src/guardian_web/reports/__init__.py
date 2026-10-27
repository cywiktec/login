"""Mission reports as data, Markdown, HTML and CSV. All output is escaped."""

import csv
import html
import io

CSV_DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def mission_report(mission_id, events):
    """events: list of dicts with 'ts', 'kind' and 'message'. Invalid entries are counted
    instead of silently dropped, and events are sorted by time."""
    valid, invalid = [], 0
    for e in events:
        ts = e.get("ts") if isinstance(e, dict) else None
        if isinstance(ts, bool) or not isinstance(ts, (int, float)):
            invalid += 1
            continue
        valid.append({"ts": float(ts), "kind": str(e.get("kind", "")), "message": str(e.get("message", ""))})
    valid.sort(key=lambda e: e["ts"])
    kinds = {}
    for e in valid:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    return {
        "mission_id": str(mission_id),
        "events": valid,
        "invalid_events": invalid,
        "duration_s": (valid[-1]["ts"] - valid[0]["ts"]) if valid else 0.0,
        "counts": kinds,
    }


def to_markdown(report):
    def cell(text):
        return str(text).replace("|", "\\|").replace("\n", " ")

    lines = [f"# Mission {cell(report['mission_id'])}", "",
             f"Duration: {report['duration_s']:.1f} s  ", f"Events: {len(report['events'])}  ",
             f"Invalid events skipped: {report['invalid_events']}", "",
             "| ts | kind | message |", "|---|---|---|"]
    lines += [f"| {e['ts']} | {cell(e['kind'])} | {cell(e['message'])} |" for e in report["events"]]
    return "\n".join(lines) + "\n"


def to_html(report):
    esc = html.escape
    rows = "".join(f"<tr><td>{e['ts']}</td><td>{esc(e['kind'])}</td><td>{esc(e['message'])}</td></tr>"
                   for e in report["events"])
    return (f"<h1>Mission {esc(report['mission_id'])}</h1>"
            f"<p>Duration: {report['duration_s']:.1f} s; events: {len(report['events'])}; "
            f"invalid skipped: {report['invalid_events']}</p>"
            f"<table><tr><th>ts</th><th>kind</th><th>message</th></tr>{rows}</table>")


def _csv_safe(value):
    text = str(value)
    # Stop spreadsheet formula injection when the file is opened in Excel/Sheets.
    return "'" + text if text.startswith(CSV_DANGEROUS) else text


def to_csv(report):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["ts", "kind", "message"])
    for e in report["events"]:
        writer.writerow([e["ts"], _csv_safe(e["kind"]), _csv_safe(e["message"])])
    return out.getvalue()
