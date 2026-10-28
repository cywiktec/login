"""Semantic versioning and changelog helpers. Never overwrites an existing release entry."""

import re

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def parse(version):
    m = _SEMVER.match(version.strip())
    if not m:
        raise ValueError(f"not a plain MAJOR.MINOR.PATCH version: {version!r}")
    return tuple(int(x) for x in m.groups())


def bump(version, part):
    major, minor, patch = parse(version)
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown part: {part!r}")


def tag_for(version):
    parse(version)
    return f"v{version}"


def changelog_entry(changelog, version, date, notes):
    """Returns new changelog text with the entry inserted after the title."""
    parse(version)
    if not notes:
        raise ValueError("empty release notes")
    if re.search(rf"^## \[{re.escape(version)}\]", changelog, re.M):
        raise ValueError(f"version {version} already in changelog")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("date must be YYYY-MM-DD")
    block = f"## [{version}] - {date}\n" + "".join(f"- {n}\n" for n in notes) + "\n"
    head, sep, rest = changelog.partition("\n")
    return head + sep + "\n" + block + rest.lstrip("\n")


def check_release(version, tag, file_version):
    """A tag may only be released if it equals VERSION."""
    parse(version)
    return tag == tag_for(version) and file_version.strip() == version
