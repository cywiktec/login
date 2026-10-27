from pathlib import Path

import yaml


class ConfigManager:
    def __init__(self, config_dir=None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).resolve().parents[2] / "config"

    def load(self, name):
        if Path(name).name != name or not name.endswith(".yaml"):
            raise ValueError("config name must be a YAML filename")

        path = self.config_dir / name
        with path.open(encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)

        if not isinstance(config, dict):
            raise ValueError(f"{path} must contain a YAML mapping")
        return config
