import time
import psutil
import datetime

class SystemTelemetry:
    def __init__(self):
        self.boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())

    def get_stats(self) -> dict:
        """Collect real-time system metrics."""
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_count = psutil.cpu_count(logical=True)
        
        vm = psutil.virtual_memory()
        ram_percent = vm.percent
        ram_used_gb = round(vm.used / (1024**3), 2)
        ram_total_gb = round(vm.total / (1024**3), 2)
        
        disk = psutil.disk_usage('C:\\')
        disk_percent = disk.percent
        disk_free_gb = round(disk.free / (1024**3), 1)
        
        battery = psutil.sensors_battery()
        battery_percent = battery.percent if battery else None
        power_plugged = battery.power_plugged if battery else None
        
        uptime_seconds = int(time.time() - psutil.boot_time())
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        uptime_str = f"{hours}h {minutes}m"
        
        return {
            "cpu_percent": cpu_percent,
            "cpu_cores": cpu_count,
            "ram_percent": ram_percent,
            "ram_used_gb": ram_used_gb,
            "ram_total_gb": ram_total_gb,
            "disk_percent": disk_percent,
            "disk_free_gb": disk_free_gb,
            "battery_percent": battery_percent,
            "power_plugged": power_plugged,
            "uptime": uptime_str,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
        }

    def get_voice_summary(self) -> str:
        """Spoken diagnostic report in Jarvis style."""
        stats = self.get_stats()
        cpu = stats["cpu_percent"]
        ram = stats["ram_percent"]
        battery = stats["battery_percent"]
        plugged = stats["power_plugged"]
        
        parts = [f"Core diagnostics online, sir. CPU load is at {cpu} percent, memory allocation is at {ram} percent."]
        if battery is not None:
            status = "charging" if plugged else "discharging"
            parts.append(f"Battery reserves are at {battery} percent, currently {status}.")
        parts.append("All primary systems functioning within standard parameters.")
        return " ".join(parts)

telemetry = SystemTelemetry()
