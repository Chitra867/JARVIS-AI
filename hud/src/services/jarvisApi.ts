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

function getApiBaseUrl(): string {
  const configuredUrl =
    import.meta.env.VITE_JARVIS_API_URL?.trim();

  if (configuredUrl) {
    return configuredUrl.replace(/\/+$/, "");
  }

  // During Vite development the HUD runs on :5173 while
  // FastAPI runs on :8000. In the production build FastAPI
  // serves the HUD itself, so use the current origin.
  if (
    window.location.hostname === "127.0.0.1"
    || window.location.hostname === "localhost"
  ) {
    if (window.location.port === "5173") {
      return "http://127.0.0.1:8000";
    }
  }

  return window.location.origin;
}

const API_BASE_URL =
  getApiBaseUrl();

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
