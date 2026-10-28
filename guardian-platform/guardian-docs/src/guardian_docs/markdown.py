"""Markdown helpers shared by the document generators."""


def cell(value):
    """Escapes a value for a Markdown table cell."""
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def table(headers, rows):
    out = ["| " + " | ".join(cell(h) for h in headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        if len(r) != len(headers):
            raise ValueError("row length differs from headers")
        out.append("| " + " | ".join(cell(c) for c in r) + " |")
    return "\n".join(out) + "\n"
