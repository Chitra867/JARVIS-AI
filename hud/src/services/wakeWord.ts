interface WakeWordMessage {
  type: string;
  keyword?: string;
  status?: string;
}

export class WakeWordListener {
  private socket: WebSocket | null = null;

  private stream: MediaStream | null = null;

  private audioContext: AudioContext | null = null;

  private source: MediaStreamAudioSourceNode | null = null;

  private processor: AudioWorkletNode | null = null;

  private silentGain: GainNode | null = null;

  private running = false;

  private readonly onWakeWord: () => void;

  constructor(onWakeWord: () => void) {
    this.onWakeWord = onWakeWord;
  }

  async start(): Promise<void> {
    if (this.running) {
      return;
    }

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
        this.socket?.readyState ===
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
  }

  private connectWebSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      const socket = new WebSocket(
        "ws://127.0.0.1:8000/ws/wakeword",
      );

      this.socket = socket;

      socket.onopen = () => {
        console.log(
          "Wake-word WebSocket connected.",
        );

        resolve();
      };

      socket.onerror = () => {
        reject(
          new Error(
            "Unable to connect wake-word WebSocket.",
          ),
        );
      };

      socket.onmessage = (event) => {
        try {
          const message =
            JSON.parse(
              event.data,
            ) as WakeWordMessage;

          if (
            message.type === "wakeword" &&
            message.keyword === "hey_jarvis"
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

      this.processor.disconnect();

      this.processor = null;
    }

    if (this.source) {
      this.source.disconnect();

      this.source = null;
    }

    if (this.silentGain) {
      this.silentGain.disconnect();

      this.silentGain = null;
    }

    if (this.socket) {
      this.socket.close();

      this.socket = null;
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
      await this.audioContext.close();

      this.audioContext = null;
    }

    console.log(
      "JARVIS wake-word listener stopped.",
    );
  }
}