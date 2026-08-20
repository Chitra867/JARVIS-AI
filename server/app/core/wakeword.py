from pathlib import Path

import numpy as np
import openwakeword
from openwakeword.model import Model


class WakeWordEngine:
    # Lower than 0.5 for laptop microphones.
    THRESHOLD = 0.15

    def __init__(self) -> None:
        model_path = (
            Path(
                openwakeword.MODELS[
                    "hey_jarvis"
                ]["model_path"]
            ).with_suffix(".onnx")
        )

        self.model = Model(
            wakeword_models=[
                str(model_path)
            ],
            inference_framework="onnx",
        )

        self.last_score = 0.0

    def detect(
        self,
        pcm_bytes: bytes,
    ) -> bool:
        if not pcm_bytes:
            return False

        audio = np.frombuffer(
            pcm_bytes,
            dtype=np.int16,
        )

        if audio.size == 0:
            return False

        predictions = self.model.predict(
            audio
        )

        if not predictions:
            return False

        score = max(
            float(value)
            for value
            in predictions.values()
        )

        self.last_score = score

        # Useful while testing.
        if score >= 0.05:
            print(
                f"Wake score: {score:.3f}"
            )

        return score >= self.THRESHOLD


wakeword_engine = WakeWordEngine()