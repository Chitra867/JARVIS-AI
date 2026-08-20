import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.core.jarvis import jarvis
from app.core.voice import voice_engine
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


@app.get("/")
async def root():
    return {
        "name": "JARVIS",
        "status": "online",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }


@app.post(
    "/api/command",
    response_model=CommandResponse,
)
async def execute_command(
    request: CommandRequest,
) -> CommandResponse:

    response = jarvis.execute(request.command)

    return CommandResponse(
        command=request.command,
        response=response,
        success=True,
    )


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

        transcript = voice_engine.transcribe(
            temp_path
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

        response = jarvis.execute(
            transcript
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