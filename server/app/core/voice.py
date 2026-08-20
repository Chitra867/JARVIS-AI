from pathlib import Path

from faster_whisper import WhisperModel


class VoiceEngine:
    def __init__(self) -> None:
        self.model = WhisperModel(
            "small.en",
            device="cpu",
            compute_type="int8",
        )

    def transcribe(self, audio_path: Path) -> str:
        segments, _ = self.model.transcribe(
            str(audio_path),
            beam_size=5,
            language="en",
            task="transcribe",
            vad_filter=True,
            condition_on_previous_text=False,
            temperature=0.0,
            hotwords="Jarvis Hey Jarvis Hello Jarvis",
        )

        text = " ".join(
            segment.text.strip()
            for segment in segments
            if segment.text.strip()
        )

        return text.strip()


voice_engine = VoiceEngine()