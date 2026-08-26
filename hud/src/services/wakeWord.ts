interface WakeWordMessage {
  type: string;
  keyword?: string;
  status?: string;
}

function getWakeWordUrl(): string {
  const configuredUrl =
    import.meta.env.VITE_JARVIS_WS_URL?.trim();

  if (configuredUrl) {
    return configuredUrl;
  }

  const backendUrl =
    (
      (
        window.location.hostname === "127.0.0.1"
        || window.location.hostname === "localhost"
      )
      && window.location.port === "5173"
    )
      ? new URL("http://127.0.0.1:8000")
      : new URL(window.location.origin);

  const protocol =
    backendUrl.protocol === "https:"
      ? "wss:"
      : "ws:";

  return (
    `${protocol}//${backendUrl.host}/ws/wakeword`
  );
}

export class WakeWordListener {
  private socket: WebSocket | null = null;

  private stream: MediaStream | null = null;

  private audioContext: AudioContext | null = null;

  private source: MediaStreamAudioSourceNode | null = null;

  private processor: AudioWorkletNode | null = null;

  private silentGain: GainNode | null = null;

  private running = false;

  private startInProgress = false;

  private readonly onWakeWord: () => void;

  constructor(onWakeWord: () => void) {
    this.onWakeWord = onWakeWord;
  }

  async start(): Promise<void> {
    if (
      this.running
      || this.startInProgress
    ) {
      return;
    }

    this.startInProgress = true;

    try {
      this.stream =
        await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            channelCount: 1,
          },
        });

      this.audioContext = new AudioContext({
        sampleRate: 16000,
      });

      if (this.audioContext.state === "suspended") {
        await this.audioContext.resume();
      }

      await this.audioContext.audioWorklet.addModule(
        "/wakeword-processor.js",
      );

      this.source =
        this.audioContext.createMediaStreamSource(
          this.stream,
        );

      this.processor =
        new AudioWorkletNode(
          this.audioContext,
          "wakeword-processor",
        );

      this.silentGain =
        this.audioContext.createGain();

      this.silentGain.gain.value = 0;

      await this.connectWebSocket();

      this.processor.port.onmessage = (
        event: MessageEvent<ArrayBuffer>,
      ) => {
        if (
          this.running
          && this.socket?.readyState ===
            WebSocket.OPEN
        ) {
          this.socket.send(event.data);
        }
      };

      this.source.connect(this.processor);

      this.processor.connect(this.silentGain);

      this.silentGain.connect(
        this.audioContext.destination,
      );

      this.running = true;

      console.log(
        "JARVIS wake-word listener started.",
      );
    } catch (error) {
      await this.stop();

      throw error;
    } finally {
      this.startInProgress = false;
    }
  }

  private connectWebSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      const socket =
        new WebSocket(
          getWakeWordUrl(),
        );

      let settled = false;

      const rejectOnce = (
        message: string,
      ) => {
        if (settled) {
          return;
        }

        settled = true;

        reject(
          new Error(message),
        );
      };

      this.socket = socket;

      socket.onopen = () => {
        if (
          this.socket !== socket
        ) {
          socket.close();

          rejectOnce(
            "Wake-word connection was cancelled.",
          );

          return;
        }

        settled = true;

        console.log(
          "Wake-word WebSocket connected.",
        );

        resolve();
      };

      socket.onerror = () => {
        rejectOnce(
          "Unable to connect wake-word WebSocket.",
        );
      };

      socket.onmessage = (event) => {
        if (
          this.socket !== socket
          || !this.running
        ) {
          return;
        }

        try {
          const message =
            JSON.parse(
              event.data,
            ) as WakeWordMessage;

          if (
            message.type === "wakeword"
            && message.keyword === "hey_jarvis"
          ) {
            console.log(
              "HEY JARVIS DETECTED",
            );

            this.onWakeWord();
          }
        } catch (error) {
          console.error(
            "Wake-word message error:",
            error,
          );
        }
      };

      socket.onclose = () => {
        if (
          !settled
        ) {
          rejectOnce(
            "Wake-word WebSocket closed before connecting.",
          );
        }

        if (
          this.socket === socket
        ) {
          this.socket = null;
        }

        console.log(
          "Wake-word WebSocket closed.",
        );
      };
    });
  }

  async stop(): Promise<void> {
    this.running = false;

    if (this.processor) {
      this.processor.port.onmessage = null;

      try {
        this.processor.disconnect();
      } catch {
        // Already disconnected.
      }

      this.processor = null;
    }

    if (this.source) {
      try {
        this.source.disconnect();
      } catch {
        // Already disconnected.
      }

      this.source = null;
    }

    if (this.silentGain) {
      try {
        this.silentGain.disconnect();
      } catch {
        // Already disconnected.
      }

      this.silentGain = null;
    }

    if (this.socket) {
      const socket =
        this.socket;

      this.socket = null;

      try {
        socket.close();
      } catch {
        // Already closed.
      }
    }

    if (this.stream) {
      this.stream
        .getTracks()
        .forEach((track) => {
          track.stop();
        });

      this.stream = null;
    }

    if (this.audioContext) {
      const audioContext =
        this.audioContext;

      this.audioContext = null;

      if (
        audioContext.state !== "closed"
      ) {
        try {
          await audioContext.close();
        } catch {
          // Already closing/closed.
        }
      }
    }

    console.log(
      "JARVIS wake-word listener stopped.",
    );
  }
}
