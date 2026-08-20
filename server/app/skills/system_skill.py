import platform
import time
from pathlib import Path

import psutil

from app.skills.base import Skill


class SystemSkill(Skill):
    def can_handle(self, command: str) -> bool:
        normalized = command.strip().lower()

        keywords = (
            "system status",
            "computer status",
            "pc status",
            "system info",
            "system information",
            "cpu",
            "processor",
            "ram",
            "memory usage",
            "battery",
            "disk",
            "storage",
            "operating system",
            "os version",
            "uptime",
            "network status",
            "internet status",
        )

        return any(
            keyword in normalized
            for keyword in keywords
        )

    def execute(self, command: str) -> str:
        normalized = command.strip().lower()

        if "battery" in normalized:
            return self.get_battery()

        if (
            "cpu" in normalized
            or "processor" in normalized
        ):
            return self.get_cpu()

        if (
            "ram" in normalized
            or "memory usage" in normalized
        ):
            return self.get_memory()

        if (
            "disk" in normalized
            or "storage" in normalized
        ):
            return self.get_disk()

        if (
            "operating system" in normalized
            or "os version" in normalized
        ):
            return self.get_os()

        if "uptime" in normalized:
            return self.get_uptime()

        if (
            "network status" in normalized
            or "internet status" in normalized
        ):
            return self.get_network()

        return self.get_full_status()

    def get_cpu(self) -> str:
        usage = psutil.cpu_percent(
            interval=0.3,
        )

        physical_cores = psutil.cpu_count(
            logical=False,
        )

        logical_cores = psutil.cpu_count(
            logical=True,
        )

        frequency = psutil.cpu_freq()

        if frequency:
            frequency_ghz = (
                frequency.current / 1000
            )

            return (
                f"CPU usage is {usage:.0f} percent. "
                f"You have {physical_cores} physical cores "
                f"and {logical_cores} logical processors. "
                f"The current CPU frequency is "
                f"{frequency_ghz:.2f} gigahertz."
            )

        return (
            f"CPU usage is {usage:.0f} percent. "
            f"You have {physical_cores} physical cores "
            f"and {logical_cores} logical processors."
        )

    def get_memory(self) -> str:
        memory = psutil.virtual_memory()

        total_gb = (
            memory.total / (1024 ** 3)
        )

        used_gb = (
            memory.used / (1024 ** 3)
        )

        available_gb = (
            memory.available / (1024 ** 3)
        )

        return (
            f"RAM usage is {memory.percent:.0f} percent. "
            f"You are using approximately "
            f"{used_gb:.1f} gigabytes out of "
            f"{total_gb:.1f} gigabytes. "
            f"{available_gb:.1f} gigabytes are currently available."
        )

    def get_battery(self) -> str:
        battery = psutil.sensors_battery()

        if battery is None:
            return (
                "Battery information is not available "
                "on this system."
            )

        status = (
            "charging"
            if battery.power_plugged
            else "running on battery"
        )

        response = (
            f"Battery level is "
            f"{battery.percent:.0f} percent, "
            f"and the laptop is {status}."
        )

        if (
            not battery.power_plugged
            and battery.secsleft
            not in (
                psutil.POWER_TIME_UNKNOWN,
                psutil.POWER_TIME_UNLIMITED,
            )
        ):
            hours = (
                battery.secsleft // 3600
            )

            minutes = (
                battery.secsleft % 3600
            ) // 60

            response += (
                f" Estimated remaining time is "
                f"{hours} hours and {minutes} minutes."
            )

        return response

    def get_disk(self) -> str:
        drive = (
            Path.home().anchor
            or "C:\\"
        )

        disk = psutil.disk_usage(
            drive,
        )

        total_gb = (
            disk.total / (1024 ** 3)
        )

        used_gb = (
            disk.used / (1024 ** 3)
        )

        free_gb = (
            disk.free / (1024 ** 3)
        )

        return (
            f"Your {drive} drive is "
            f"{disk.percent:.0f} percent full. "
            f"{used_gb:.1f} gigabytes are used "
            f"out of {total_gb:.1f} gigabytes, "
            f"with {free_gb:.1f} gigabytes free."
        )

    def get_os(self) -> str:
        system = platform.system()
        release = platform.release()
        version = platform.version()
        machine = platform.machine()

        return (
            f"You are running {system} {release} "
            f"on a {machine} system. "
            f"The operating system build is {version}."
        )

    def get_uptime(self) -> str:
        uptime_seconds = (
            time.time()
            - psutil.boot_time()
        )

        days = int(
            uptime_seconds // 86400
        )

        hours = int(
            (
                uptime_seconds % 86400
            ) // 3600
        )

        minutes = int(
            (
                uptime_seconds % 3600
            ) // 60
        )

        parts: list[str] = []

        if days:
            parts.append(
                f"{days} day"
                + (
                    "s"
                    if days != 1
                    else ""
                )
            )

        if hours:
            parts.append(
                f"{hours} hour"
                + (
                    "s"
                    if hours != 1
                    else ""
                )
            )

        parts.append(
            f"{minutes} minute"
            + (
                "s"
                if minutes != 1
                else ""
            )
        )

        return (
            "The computer has been running for "
            + ", ".join(parts)
            + "."
        )

    def get_network(self) -> str:
        interfaces = (
            psutil.net_if_stats()
        )

        active_interfaces = [
            name
            for name, stats
            in interfaces.items()
            if (
                stats.isup
                and "loopback"
                not in name.lower()
            )
        ]

        if not active_interfaces:
            return (
                "I cannot detect an active "
                "network interface."
            )

        visible = ", ".join(
            active_interfaces[:3]
        )

        return (
            f"Network connectivity is active. "
            f"Active interface"
            f"{'s are' if len(active_interfaces) > 1 else ' is'} "
            f"{visible}."
        )

    def get_full_status(self) -> str:
        cpu = psutil.cpu_percent(
            interval=0.3,
        )

        memory = psutil.virtual_memory()

        battery = psutil.sensors_battery()

        drive = (
            Path.home().anchor
            or "C:\\"
        )

        disk = psutil.disk_usage(
            drive,
        )

        response = (
            f"System status is normal. "
            f"CPU usage is {cpu:.0f} percent. "
            f"RAM usage is {memory.percent:.0f} percent. "
            f"Disk usage is {disk.percent:.0f} percent."
        )

        if battery is not None:
            response += (
                f" Battery is at "
                f"{battery.percent:.0f} percent"
            )

            if battery.power_plugged:
                response += (
                    " and the charger is connected."
                )
            else:
                response += "."

        return response