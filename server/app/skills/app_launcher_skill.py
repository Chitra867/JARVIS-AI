import subprocess

from app.skills.base import Skill


class AppLauncherSkill(Skill):
    APPS = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "vs code": "code.cmd",
"vscode": "code.cmd",
        "chrome": "chrome",
    }

    def can_handle(self, command: str) -> bool:
        normalized = command.strip().lower()
        return normalized.startswith("open ")

    def execute(self, command: str) -> str:
        app_name = command.strip().lower().removeprefix("open ").strip()

        executable = self.APPS.get(app_name)

        if not executable:
            return f"I don't know how to open {app_name} yet."

        try:
            subprocess.Popen([executable])
            return f"Opening {app_name}."
        except OSError:
            return f"I couldn't open {app_name}."