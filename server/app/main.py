import asyncio
import shutil
import tempfile
import time
from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware

from app.core.jarvis import jarvis
from app.core.voice import voice_engine
from app.core.wakeword import wakeword_engine
from app.models.command import (
    CommandRequest,
    CommandResponse,
    VoiceCommandResponse,
)


app = FastAPI(
    title="JARVIS API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():
    return {
        "name": "JARVIS",
        "status": "online",
        "version": "1.0.0",
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }


# =========================================================
# TEXT COMMAND
# =========================================================

@app.post(
    "/api/command",
    response_model=CommandResponse,
)
async def execute_command(
    request: CommandRequest,
) -> CommandResponse:

    response = jarvis.execute(
        request.command
    )

    return CommandResponse(
        command=request.command,
        response=response,
        success=True,
    )


# =========================================================
# VOICE COMMAND
# =========================================================

@app.post(
    "/api/voice",
    response_model=VoiceCommandResponse,
)
async def execute_voice_command(
    audio: UploadFile = File(...),
) -> VoiceCommandResponse:

    suffix = Path(
        audio.filename or "voice.webm"
    ).suffix or ".webm"

    temp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temp_file:

            shutil.copyfileobj(
                audio.file,
                temp_file,
            )

            temp_path = Path(
                temp_file.name
            )

        transcript = await asyncio.to_thread(
            voice_engine.transcribe,
            temp_path,
        )

        if not transcript:
            return VoiceCommandResponse(
                transcript="",
                response=(
                    "I couldn't hear that clearly. "
                    "Please try again."
                ),
                success=False,
            )

        response = await asyncio.to_thread(
            jarvis.execute,
            transcript,
        )

        return VoiceCommandResponse(
            transcript=transcript,
            response=response,
            success=True,
        )

    finally:
        await audio.close()

        if temp_path is not None:
            temp_path.unlink(
                missing_ok=True
            )


# =========================================================
# ALWAYS-LISTENING WAKE WORD
# =========================================================
@app.websocket("/ws/wakeword")
async def wakeword_websocket(
    websocket: WebSocket,
) -> None:

    await websocket.accept()

    print("Wake-word listener connected.")

    await websocket.send_json({
        "type": "status",
        "status": "waiting",
    })

    last_detection = 0.0
    cooldown_seconds = 3.0
    frame_count = 0

    try:
        while True:
            pcm_bytes = await websocket.receive_bytes()

            if not pcm_bytes:
                continue

            frame_count += 1

            # Confirm browser audio is reaching backend
            if frame_count % 50 == 0:
                print(
                    f"Wake audio frames received: {frame_count} "
                    f"| bytes: {len(pcm_bytes)}"
                )

            detected = await asyncio.to_thread(
                wakeword_engine.detect,
                pcm_bytes,
            )

            now = time.monotonic()

            if (
                detected
                and now - last_detection >= cooldown_seconds
            ):
                last_detection = now

                print(
                    ">>> HEY JARVIS DETECTED <<<"
                )

                await websocket.send_json({
                    "type": "wakeword",
                    "keyword": "hey_jarvis",
                })

    except WebSocketDisconnect:
        print(
            "Wake-word listener disconnected."
        )

    except Exception as error:
        print(
            "Wake-word WebSocket error:",
            error,
        )