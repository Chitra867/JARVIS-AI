from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.jarvis import jarvis
from app.models.command import CommandRequest, CommandResponse


app = FastAPI(
    title="JARVIS API",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
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
        "version": "0.1.0",
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