"""RTM: requirements traceability matrix (requirement -> tests)."""

from dataclasses import dataclass, field

from ..markdown import table


@dataclass(frozen=True)
class Requirement:
    id: str
    text: str
    component: str
    tests: tuple = field(default_factory=tuple)


def validate(requirements, known_tests=None):
    """Problems: duplicate ids, untested requirements, tests that do not exist."""
    problems, seen = [], set()
    for r in requirements:
        if r.id in seen:
            problems.append(f"duplicate id {r.id}")
        seen.add(r.id)
        if not r.tests:
            problems.append(f"{r.id}: no test")
        elif known_tests is not None:
            problems.extend(f"{r.id}: unknown test {t}" for t in r.tests if t not in known_tests)
    return problems


def coverage(requirements, known_tests=None):
    """Fraction of requirements with at least one existing test; 0.0 when empty."""
    if not requirements:
        return 0.0
    ok = sum(1 for r in requirements
             if r.tests and (known_tests is None or all(t in known_tests for t in r.tests)))
    return ok / len(requirements)


def render(requirements):
    return table(["ID", "Component", "Requirement", "Tests"],
                 [(r.id, r.component, r.text, ", ".join(r.tests) or "**NONE**")
                  for r in sorted(requirements, key=lambda r: r.id)])
