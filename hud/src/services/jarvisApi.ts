export interface CommandResponse {
  command: string;
  response: string;
  success: boolean;
}

export interface VoiceCommandResponse {
  transcript: string;
  response: string;
  success: boolean;
}

const API_BASE_URL = "http://127.0.0.1:8000";

export async function sendCommand(
  command: string,
): Promise<CommandResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/command`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        command,
      }),
    },
  );

  if (!response.ok) {
    throw new Error(
      `JARVIS request failed: ${response.status}`,
    );
  }

  return response.json() as Promise<CommandResponse>;
}

export async function sendVoice(
  audio: Blob,
): Promise<VoiceCommandResponse> {
  const formData = new FormData();

  formData.append(
    "audio",
    audio,
    "jarvis-voice.webm",
  );

  const response = await fetch(
    `${API_BASE_URL}/api/voice`,
    {
      method: "POST",
      body: formData,
    },
  );

  if (!response.ok) {
    throw new Error(
      `Voice request failed: ${response.status}`,
    );
  }

  return response.json() as Promise<VoiceCommandResponse>;
}