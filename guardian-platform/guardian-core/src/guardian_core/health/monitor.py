import psutil


class HealthMonitor:
    def get_status(self):
        return {
            "cpu": psutil.cpu_percent(interval=None),
            "ram": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage("/").percent,
        }

    def get_battery(self):
        sensors = getattr(psutil, "sensors_battery", None)
        try:
            battery = sensors() if sensors else None
        except OSError:
            battery = None
        if battery is None:
            return None
        return {"percent": battery.percent, "plugged": battery.power_plugged}
