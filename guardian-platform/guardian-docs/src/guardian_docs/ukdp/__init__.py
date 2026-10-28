"""UKDP v1.0 documentation standard: header and section checks for controlled documents.

The expansion of the acronym was not provided; this implements the standard as written in
docs/ukdp/UKDP-v1.0.md. Also provides the UKDP document register.
"""

import re

from ..register import Document, Register  # noqa: F401

HEADER_FIELDS = ("ID", "Wersja", "Status", "Właściciel", "Data")
REQUIRED_SECTIONS = ("Cel", "Zakres", "Założenia i ograniczenia", "Historia zmian")
STATUSES = ("szkic", "przegląd", "zatwierdzony", "wycofany")
ID_PATTERN = re.compile(r"^(FMEA|NZA|UKDP|RTM|SAT|SAC|ARCH)-\d{3}$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def new_register():
    return Register("UKDP")


def parse_header(text):
    fields = {}
    for name in HEADER_FIELDS:
        m = re.search(rf"^\*\*{re.escape(name)}:\*\* (.+)$", text, re.M)
        if m:
            fields[name] = m.group(1).strip()
    return fields


def check(text):
    """Returns a list of problems; empty means the document conforms to UKDP v1.0."""
    problems = []
    if not re.match(r"# \S", text):
        problems.append("brak tytułu (# ...) w pierwszej linii")
    fields = parse_header(text)
    for name in HEADER_FIELDS:
        if name not in fields:
            problems.append(f"brak pola nagłówka: {name}")
    if "ID" in fields and not ID_PATTERN.match(fields["ID"]):
        problems.append(f"zły format ID: {fields['ID']!r}")
    if "Wersja" in fields and not VERSION_PATTERN.match(fields["Wersja"]):
        problems.append(f"zły format wersji: {fields['Wersja']!r}")
    if "Status" in fields and fields["Status"] not in STATUSES:
        problems.append(f"zły status: {fields['Status']!r}")
    if "Data" in fields and not DATE_PATTERN.match(fields["Data"]):
        problems.append(f"zła data: {fields['Data']!r}")
    for section in REQUIRED_SECTIONS:
        if not re.search(rf"^## {re.escape(section)}\s*$", text, re.M):
            problems.append(f"brak sekcji: {section}")
    return problems
