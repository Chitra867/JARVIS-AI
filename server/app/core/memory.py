from datetime import datetime
from pathlib import Path


class MemoryManager:
    def __init__(self) -> None:
        self.vault_path = Path(__file__).resolve().parents[3] / "vault"
        self.daily_path = self.vault_path / "daily"

        self.daily_path.mkdir(parents=True, exist_ok=True)

    def remember(self, text: str) -> str:
        cleaned_text = text.strip()

        if not cleaned_text:
            return "There is nothing to remember."

        now = datetime.now()

        memory_file = self.daily_path / f"{now:%Y-%m-%d}.md"

        if not memory_file.exists():
            memory_file.write_text(
                f"# {now:%Y-%m-%d}\n\n",
                encoding="utf-8",
            )

        with memory_file.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                f"## {now:%H:%M}\n"
                f"- {cleaned_text}\n\n"
            )

        return "I've saved that to memory."

    def search(self, query: str) -> list[str]:
        cleaned_query = query.strip().lower()

        if not cleaned_query:
            return []

        matches: list[str] = []
        seen: set[str] = set()

        for file_path in self.vault_path.rglob("*.md"):
            content = file_path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            for line in content.splitlines():
                cleaned_line = line.strip().lstrip("-").strip()

                if (
                    cleaned_query in cleaned_line.lower()
                    and cleaned_line
                    and cleaned_line not in seen
                ):
                    seen.add(cleaned_line)
                    matches.append(cleaned_line)

                    if len(matches) >= 5:
                        return matches

        return matches

    def get_recent_memories(self, limit: int = 20) -> list[str]:
        memories: list[str] = []

        files = sorted(
            self.daily_path.glob("*.md"),
            reverse=True,
        )

        for file_path in files:
            content = file_path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            for line in reversed(content.splitlines()):
                cleaned_line = line.strip().lstrip("-").strip()

                if (
                    cleaned_line
                    and not cleaned_line.startswith("#")
                ):
                    memories.append(cleaned_line)

                    if len(memories) >= limit:
                        return memories

        return memories
    

memory_manager = MemoryManager()