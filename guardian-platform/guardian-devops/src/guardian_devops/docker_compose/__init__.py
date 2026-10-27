"""Generates docker-compose files and rejects risky service settings."""

from ..yamlout import to_yaml


def service(image, ports=(), env=None, volumes=(), healthcheck=None):
    if ":" not in image.rsplit("/", 1)[-1] and "@" not in image:
        raise ValueError(f"image must carry a tag or digest: {image}")
    svc = {"image": image, "restart": "unless-stopped", "read_only": True,
           "cap_drop": ["ALL"], "security_opt": ["no-new-privileges:true"]}
    if ports:
        # Bind to loopback only; exposing to the network must be a deliberate edit.
        svc["ports"] = [f"127.0.0.1:{h}:{c}" for h, c in ports]
    if env:
        svc["environment"] = dict(env)
    if volumes:
        svc["volumes"] = list(volumes)
    if healthcheck:
        svc["healthcheck"] = {"test": ["CMD-SHELL", healthcheck], "interval": "30s",
                              "timeout": "5s", "retries": 3}
    return svc


def default_stack():
    return {
        "services": {
            "mosquitto": service("eclipse-mosquitto:2", ports=[(1883, 1883)]),
            "prometheus": service("prom/prometheus:v2.53.0", ports=[(9090, 9090)]),
            "grafana": service("grafana/grafana:11.1.0", ports=[(3000, 3000)]),
            "alertmanager": service("prom/alertmanager:v0.27.0", ports=[(9093, 9093)]),
        }
    }


def render(compose):
    return to_yaml(compose)


def validate(compose):
    problems = []
    services = compose.get("services")
    if not services:
        return ["no services"]
    for name, s in services.items():
        image = s.get("image", "")
        tag = image.rsplit("/", 1)[-1].partition(":")[2]
        if not image:
            problems.append(f"{name}: no image")
        elif tag in ("", "latest") and "@" not in image:
            problems.append(f"{name}: image not pinned ({image})")
        if s.get("privileged"):
            problems.append(f"{name}: privileged")
        if s.get("network_mode") == "host":
            problems.append(f"{name}: host network")
        for v in s.get("volumes", []):
            if str(v).startswith("/var/run/docker.sock"):
                problems.append(f"{name}: mounts docker socket")
        for p in s.get("ports", []):
            p = str(p)
            if not p.startswith("127.0.0.1:") and p.count(":") < 2:
                problems.append(f"{name}: port {p} published on all interfaces")
        for k, v in (s.get("environment") or {}).items():
            if any(w in k.upper() for w in ("PASSWORD", "SECRET", "TOKEN", "KEY")) \
                    and not str(v).startswith("${"):
                problems.append(f"{name}: literal secret in {k}")
    return problems
