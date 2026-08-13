import httpx

from app.core.memory import memory_manager
from app.skills.base import Skill


class AISkill(Skill):
    OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
    MODEL = "llama3.2:3b"

    def can_handle(self, command: str) -> bool:
        return bool(command.strip())

    def execute(self, command: str) -> str:
        memories = memory_manager.get_recent_memories(limit=10)

        memory_context = "\n".join(
            f"- {memory}"
            for memory in memories
        )

        prompt = f"""
You are JARVIS, a concise personal AI assistant.

Relevant memory:
{memory_context if memory_context else "- No saved memory yet."}

Rules:
- Answer clearly and briefly.
- Use saved memory when relevant.
- Do not invent memories.
- Do not pretend you performed an action unless a JARVIS skill actually performed it.
- If asked who you are, identify yourself as JARVIS.
- Be useful and practical.

User: {command}
JARVIS:
""".strip()

        try:
            response = httpx.post(
                self.OLLAMA_URL,
                json={
                    "model": self.MODEL,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=60.0,
            )

            response.raise_for_status()

            data = response.json()
            answer = data.get("response", "").strip()

            if not answer:
                return "I couldn't generate a response."

            return answer

        except httpx.ConnectError:
            return "I can't connect to the local AI engine."

        except httpx.HTTPError:
            return "The local AI engine returned an error."