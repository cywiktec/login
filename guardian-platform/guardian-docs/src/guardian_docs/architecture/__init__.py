"""Architecture documentation generated from a component dependency map."""

DEPENDENCIES = {
    "guardian-voice": ["guardian-ai-engine"],
    "guardian-ai-engine": ["guardian-safety-layer", "guardian-interfaces"],
    "guardian-safety-layer": [],
    "guardian-mission-manager": ["guardian-navigation", "guardian-safety-layer"],
    "guardian-navigation": ["guardian-perception"],
    "guardian-go2-driver": ["guardian-interfaces"],
    "guardian-core": ["guardian-go2-driver", "guardian-mission-manager", "guardian-safety-layer"],
    "guardian-telemetry": ["guardian-core"],
    "guardian-monitoring": ["guardian-telemetry"],
    "guardian-web": ["guardian-telemetry"],
    "guardian-mobile": ["guardian-telemetry"],
    "guardian-perception": [],
    "guardian-interfaces": [],
}


def find_cycle(deps):
    """Returns one dependency cycle as a list of nodes, or None."""
    state = {}

    def visit(n, path):
        state[n] = 1
        for m in deps.get(n, ()):
            if state.get(m) == 1:
                return path[path.index(m):] + [m] if m in path else [n, m]
            if m not in state:
                found = visit(m, path + [m])
                if found:
                    return found
        state[n] = 2
        return None

    for node in sorted(deps):
        if node not in state:
            found = visit(node, [node])
            if found:
                return found
    return None


def undefined(deps):
    """Components referenced as dependencies but not described."""
    return sorted({m for ms in deps.values() for m in ms} - set(deps))


def mermaid(deps):
    lines = ["graph TD"]
    for n in sorted(deps):
        for m in sorted(deps[n]):
            lines.append(f"    {n.replace('-', '_')}[{n}] --> {m.replace('-', '_')}[{m}]")
    return "\n".join(lines) + "\n"
