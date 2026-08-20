from pydantic import BaseModel


class CommandRequest(BaseModel):
    command: str


class CommandResponse(BaseModel):
    command: str
    response: str
    success: bool = True


class VoiceCommandResponse(BaseModel):
    transcript: str
    response: str
    success: bool = True