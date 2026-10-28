"""Tiny YAML emitter for config generation (dicts, lists, strings, numbers, bools).

Strings are always emitted as JSON strings, which are valid YAML, so no value can
break out of its line.
"""

import json


def _scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return json.dumps(v)
    return json.dumps(str(v), ensure_ascii=False)


def to_yaml(obj, indent=0):
    pad = "  " * indent
    lines = []
    if isinstance(obj, dict):
        if not obj:
            return pad + "{}\n"
        for key, value in obj.items():
            k = _scalar(str(key))
            if isinstance(value, (dict, list)) and value:
                lines.append(f"{pad}{k}:")
                lines.append(to_yaml(value, indent + 1).rstrip("\n"))
            elif isinstance(value, (dict, list)):
                lines.append(f"{pad}{k}: {'{}' if isinstance(value, dict) else '[]'}")
            else:
                lines.append(f"{pad}{k}: {_scalar(value)}")
    elif isinstance(obj, list):
        if not obj:
            return pad + "[]\n"
        for item in obj:
            if isinstance(item, (dict, list)) and item:
                body = to_yaml(item, indent + 1).rstrip("\n").split("\n")
                lines.append(f"{pad}- {body[0].lstrip()}")
                lines.extend(body[1:])
            else:
                lines.append(f"{pad}- {_scalar(item) if not isinstance(item, (dict, list)) else ('{}' if isinstance(item, dict) else '[]')}")
    else:
        return pad + _scalar(obj) + "\n"
    return "\n".join(lines) + "\n"
