import asyncio
import tempfile
from pathlib import Path

import edge_tts


VOICE = "en-GB-RyanNeural"
RATE = "-8%"
PITCH = "-4Hz"
VOLUME = "+0%"


async def generate_speech(
    text: str,
) -> Path:
    text = text.strip()

    if not text:
        raise ValueError(
            "Speech text cannot be empty."
        )

    temp_file = tempfile.NamedTemporaryFile(
        suffix=".mp3",
        delete=False,
    )

    output_path = Path(
        temp_file.name
    )

    temp_file.close()

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate=RATE,
        pitch=PITCH,
        volume=VOLUME,
    )

    await communicate.save(
        str(output_path)
    )

    return output_path


def generate_speech_sync(
    text: str,
) -> Path:
    return asyncio.run(
        generate_speech(text)
    )