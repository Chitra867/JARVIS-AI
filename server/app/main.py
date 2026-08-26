import asyncio
import os
import shutil
import tempfile
import time
from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from fastapi.responses import (
    FileResponse,
)

from pydantic import BaseModel

from starlette.background import (
    BackgroundTask,
)

from app.core.jarvis import (
    jarvis,
)

from app.core.tts import (
    generate_speech,
)

from app.core.voice import (
    voice_engine,
)

from app.core.wakeword import (
    wakeword_engine,
)

from app.models.command import (
    CommandRequest,
    CommandResponse,
    VoiceCommandResponse,
)


# =========================================================
# PATHS
# =========================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

HUD_DIST_DIR = (
    PROJECT_ROOT
    / "hud"
    / "dist"
)

HUD_INDEX_FILE = (
    HUD_DIST_DIR
    / "index.html"
)


# =========================================================
# APPLICATION
# =========================================================

app = FastAPI(
    title="JARVIS API",
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def get_cors_origins() -> list[str]:
    raw_origins = os.getenv(
        "JARVIS_CORS_ORIGINS",
        "",
    ).strip()

    if not raw_origins:
        return list(
            DEFAULT_CORS_ORIGINS
        )

    origins = [
        origin.strip()
        for origin
        in raw_origins.split(",")
        if origin.strip()
    ]

    return (
        origins
        or list(
            DEFAULT_CORS_ORIGINS
        )
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# TTS MODEL
# =========================================================

class TTSRequest(BaseModel):
    text: str


# =========================================================
# HELPERS
# =========================================================

def delete_temp_file(
    path: Path,
) -> None:
    try:
        path.unlink(
            missing_ok=True
        )

    except OSError:
        pass


# =========================================================
# ROOT
# =========================================================

@app.get(
    "/",
    response_model=None,
)
async def root():
    if HUD_INDEX_FILE.is_file():
        return FileResponse(
            path=str(
                HUD_INDEX_FILE
            ),
            media_type="text/html",
        )

    return {
        "name": "JARVIS",
        "status": "online",
        "version": "1.0.0",
        "hud": "not-built",
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health() -> dict[
    str,
    str,
]:
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
    command = (
        request.command
        .strip()
    )

    if not command:
        return CommandResponse(
            command=request.command,
            response=(
                "Tell me what you'd like "
                "me to do."
            ),
            success=False,
        )

    try:
        # jarvis.execute() can call Ollama and perform
        # other blocking work, so keep it off FastAPI's
        # async event loop.
        response = (
            await asyncio.to_thread(
                jarvis.execute,
                command,
            )
        )

        return CommandResponse(
            command=command,
            response=response,
            success=True,
        )

    except Exception as error:
        print(
            "JARVIS command error:",
            error,
        )

        return CommandResponse(
            command=command,
            response=(
                "I encountered an error while "
                "processing that command."
            ),
            success=False,
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
    suffix = (
        Path(
            audio.filename
            or "voice.webm"
        )
        .suffix
        or ".webm"
    )

    temp_path: Path | None = None

    try:
        # -------------------------------------------------
        # SAVE UPLOADED AUDIO TEMPORARILY
        # -------------------------------------------------

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

        # -------------------------------------------------
        # SPEECH TO TEXT
        # -------------------------------------------------

        transcript = (
            await asyncio.to_thread(
                voice_engine.transcribe,
                temp_path,
            )
        )

        transcript = (
            transcript
            .strip()
            if transcript
            else ""
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

        # -------------------------------------------------
        # EXECUTE TRANSCRIBED COMMAND
        # -------------------------------------------------

        response = (
            await asyncio.to_thread(
                jarvis.execute,
                transcript,
            )
        )

        return VoiceCommandResponse(
            transcript=transcript,
            response=response,
            success=True,
        )

    except Exception as error:
        print(
            "Voice command error:",
            error,
        )

        return VoiceCommandResponse(
            transcript="",
            response=(
                "I encountered an error while "
                "processing your voice command."
            ),
            success=False,
        )

    finally:
        await audio.close()

        if temp_path is not None:
            temp_path.unlink(
                missing_ok=True
            )


# =========================================================
# JARVIS NEURAL TTS
# =========================================================

@app.post(
    "/api/tts",
    response_class=FileResponse,
)
async def text_to_speech(
    request: TTSRequest,
) -> FileResponse:
    text = (
        request.text
        .strip()
    )

    if not text:
        raise HTTPException(
            status_code=400,
            detail=(
                "Text cannot be empty."
            ),
        )

    # Prevent accidentally generating extremely
    # large audio responses.
    if len(text) > 3000:
        raise HTTPException(
            status_code=400,
            detail=(
                "Text is too long. "
                "Maximum length is 3000 characters."
            ),
        )

    try:
        audio_path = (
            await generate_speech(
                text
            )
        )

    except Exception as error:
        print(
            "JARVIS TTS error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to generate "
                "JARVIS speech."
            ),
        ) from error

    if (
        not audio_path.exists()
        or not audio_path.is_file()
    ):
        raise HTTPException(
            status_code=500,
            detail=(
                "Generated speech file "
                "was not found."
            ),
        )

    # The temporary MP3 is deleted automatically
    # after FastAPI finishes sending it.
    return FileResponse(
        path=str(
            audio_path
        ),
        media_type="audio/mpeg",
        filename="jarvis.mp3",
        background=BackgroundTask(
            delete_temp_file,
            audio_path,
        ),
    )


# =========================================================
# ALWAYS-LISTENING WAKE WORD
# =========================================================

@app.websocket(
    "/ws/wakeword"
)
async def wakeword_websocket(
    websocket: WebSocket,
) -> None:
    await websocket.accept()

    print(
        "Wake-word listener connected."
    )

    await websocket.send_json(
        {
            "type": "status",
            "status": "waiting",
        }
    )

    last_detection = 0.0
    cooldown_seconds = 3.0
    frame_count = 0

    try:
        while True:
            pcm_bytes = (
                await websocket
                .receive_bytes()
            )

            if not pcm_bytes:
                continue

            frame_count += 1

            # ---------------------------------------------
            # DEBUG AUDIO FLOW
            # ---------------------------------------------

            if (
                frame_count % 50
                == 0
            ):
                print(
                    (
                        "Wake audio frames received: "
                        f"{frame_count} "
                        f"| bytes: "
                        f"{len(pcm_bytes)}"
                    )
                )

            # ---------------------------------------------
            # WAKE WORD DETECTION
            # ---------------------------------------------

            detected = (
                await asyncio.to_thread(
                    wakeword_engine.detect,
                    pcm_bytes,
                )
            )

            now = (
                time.monotonic()
            )

            if (
                detected
                and (
                    now
                    - last_detection
                    >= cooldown_seconds
                )
            ):
                last_detection = now

                print(
                    ">>> HEY JARVIS DETECTED <<<"
                )

                await websocket.send_json(
                    {
                        "type": "wakeword",
                        "keyword": (
                            "hey_jarvis"
                        ),
                    }
                )

    except WebSocketDisconnect:
        print(
            "Wake-word listener "
            "disconnected."
        )

    except Exception as error:
        print(
            "Wake-word WebSocket error:",
            error,
        )

        try:
            await websocket.close()

        except Exception:
            pass

# =========================================================
# PRODUCTION HUD STATIC FILES
# =========================================================
#
# Keep this catch-all LAST so API and WebSocket routes above
# always take precedence.
# =========================================================

@app.get(
    "/{resource_path:path}",
    include_in_schema=False,
    response_model=None,
)
async def serve_hud_resource(
    resource_path: str,
):
    if not HUD_DIST_DIR.is_dir():
        raise HTTPException(
            status_code=404,
            detail="JARVIS HUD is not built.",
        )

    dist_root = (
        HUD_DIST_DIR
        .resolve()
    )

    candidate = (
        HUD_DIST_DIR
        / resource_path
    ).resolve()

    try:
        candidate.relative_to(
            dist_root
        )
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail="Resource not found.",
        ) from error

    if candidate.is_file():
        return FileResponse(
            path=str(
                candidate
            )
        )

    if HUD_INDEX_FILE.is_file():
        return FileResponse(
            path=str(
                HUD_INDEX_FILE
            ),
            media_type="text/html",
        )

    raise HTTPException(
        status_code=404,
        detail="Resource not found.",
    )
