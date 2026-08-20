import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";

import {
  sendCommand,
  sendVoice,
} from "./services/jarvisApi";

import {
  WakeWordListener,
} from "./services/wakeWord";

import "./App.css";

function App() {
  const [command, setCommand] = useState("");

  const [response, setResponse] = useState(
    "Click Enable JARVIS to start hands-free mode.",
  );

  const [isLoading, setIsLoading] = useState(false);
  const [isEnabled, setIsEnabled] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const wakeWordRef =
    useRef<WakeWordListener | null>(null);

  const conversationBusyRef =
    useRef(false);

  const mountedRef =
    useRef(true);

  // =====================================================
  // SPEAK JARVIS RESPONSE
  // =====================================================

  const speak = (
    text: string,
  ): Promise<void> => {
    return new Promise((resolve) => {
      if (
        !("speechSynthesis" in window)
      ) {
        resolve();
        return;
      }

      window.speechSynthesis.cancel();

      const utterance =
        new SpeechSynthesisUtterance(
          text,
        );

      utterance.rate = 1;
      utterance.pitch = 0.9;
      utterance.volume = 1;

      utterance.onstart = () => {
        if (mountedRef.current) {
          setIsSpeaking(true);
        }
      };

      utterance.onend = () => {
        if (mountedRef.current) {
          setIsSpeaking(false);
        }

        resolve();
      };

      utterance.onerror = () => {
        if (mountedRef.current) {
          setIsSpeaking(false);
        }

        resolve();
      };

      window.speechSynthesis.speak(
        utterance,
      );
    });
  };

  // =====================================================
  // TEXT COMMAND
  // =====================================================

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    const trimmedCommand =
      command.trim();

    if (
      !trimmedCommand ||
      isLoading ||
      conversationBusyRef.current
    ) {
      return;
    }

    conversationBusyRef.current = true;

    try {
      setIsLoading(true);
      setResponse("Processing...");

      const result =
        await sendCommand(
          trimmedCommand,
        );

      setCommand("");
      setResponse(
        result.response,
      );

      await speak(
        result.response,
      );
    } catch (error) {
      console.error(error);

      setResponse(
        "Unable to communicate with JARVIS core.",
      );
    } finally {
      setIsLoading(false);

      conversationBusyRef.current =
        false;
    }
  };

  // =====================================================
  // AUTOMATIC COMMAND RECORDING
  // =====================================================

  const recordCommand =
    async (): Promise<Blob | null> => {
      if (
        !navigator.mediaDevices
          ?.getUserMedia
      ) {
        setResponse(
          "Microphone is not supported.",
        );

        return null;
      }

      if (
        !("MediaRecorder" in window)
      ) {
        setResponse(
          "Audio recording is not supported.",
        );

        return null;
      }

      let stream: MediaStream | null =
        null;

      let audioContext:
        | AudioContext
        | null = null;

      try {
        stream =
          await navigator.mediaDevices
            .getUserMedia({
              audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                channelCount: 1,
              },
            });

        const recorder =
          new MediaRecorder(stream);

        const chunks: Blob[] = [];

        audioContext =
          new AudioContext();

        if (
          audioContext.state ===
          "suspended"
        ) {
          await audioContext.resume();
        }

        const source =
          audioContext
            .createMediaStreamSource(
              stream,
            );

        const analyser =
          audioContext
            .createAnalyser();

        analyser.fftSize = 2048;
        analyser.smoothingTimeConstant =
          0.2;

        source.connect(analyser);

        const samples =
          new Uint8Array(
            analyser.fftSize,
          );

        return await new Promise<
          Blob | null
        >((resolve) => {
          let speechDetected = false;

          let silenceStarted:
            | number
            | null = null;

          const startedAt =
            Date.now();

          let animationFrame = 0;

          const stopRecorder = () => {
            if (
              recorder.state ===
              "recording"
            ) {
              recorder.stop();
            }
          };

          const cleanup =
            async () => {
              cancelAnimationFrame(
                animationFrame,
              );

              source.disconnect();
              analyser.disconnect();

              stream
                ?.getTracks()
                .forEach(
                  (track) =>
                    track.stop(),
                );

              if (
                audioContext &&
                audioContext.state !==
                  "closed"
              ) {
                await audioContext.close();
              }
            };

          recorder.ondataavailable = (
            event,
          ) => {
            if (
              event.data.size > 0
            ) {
              chunks.push(
                event.data,
              );
            }
          };

          recorder.onerror = async (
            event,
          ) => {
            console.error(
              "Recorder error:",
              event,
            );

            await cleanup();

            resolve(null);
          };

          recorder.onstop =
            async () => {
              await cleanup();

              const blob =
                new Blob(
                  chunks,
                  {
                    type:
                      recorder.mimeType ||
                      "audio/webm",
                  },
                );

              resolve(
                blob.size > 0
                  ? blob
                  : null,
              );
            };

          const monitorAudio = () => {
            analyser
              .getByteTimeDomainData(
                samples,
              );

            let sum = 0;

            for (
              let index = 0;
              index <
              samples.length;
              index++
            ) {
              const normalized =
                (
                  samples[index] -
                  128
                ) /
                128;

              sum +=
                normalized *
                normalized;
            }

            const rms =
              Math.sqrt(
                sum /
                  samples.length,
              );

            // Lower threshold works better
            // with quieter laptop microphones.
            const speechThreshold =
              0.015;

            if (
              rms >
              speechThreshold
            ) {
              speechDetected = true;

              silenceStarted = null;
            } else if (
              speechDetected
            ) {
              if (
                silenceStarted ===
                null
              ) {
                silenceStarted =
                  Date.now();
              }

              // Stop after user has
              // finished speaking.
              if (
                Date.now() -
                  silenceStarted >=
                1200
              ) {
                stopRecorder();

                return;
              }
            }

            // No speech at all for 5 sec.
            if (
              !speechDetected &&
              Date.now() -
                startedAt >
                5000
            ) {
              stopRecorder();

              return;
            }

            // Maximum command length.
            if (
              Date.now() -
                startedAt >
              12000
            ) {
              stopRecorder();

              return;
            }

            animationFrame =
              requestAnimationFrame(
                monitorAudio,
              );
          };

          recorder.start();

          setIsListening(true);

          setResponse(
            "Listening...",
          );

          monitorAudio();
        });
      } catch (error) {
        console.error(
          "Recording error:",
          error,
        );

        stream
          ?.getTracks()
          .forEach(
            (track) =>
              track.stop(),
          );

        if (
          audioContext &&
          audioContext.state !==
            "closed"
        ) {
          await audioContext.close();
        }

        return null;
      }
    };

  // =====================================================
  // SEND VOICE TO JARVIS
  // =====================================================

  const processVoiceCommand =
    async () => {
      const audio =
        await recordCommand();

      setIsListening(false);

      if (!audio) {
        setResponse(
          "I didn't hear anything.",
        );

        return;
      }

      try {
        setIsLoading(true);

        setResponse(
          "Processing...",
        );

        const result =
          await sendVoice(audio);

        if (
          result.transcript
        ) {
          setCommand(
            result.transcript,
          );
        }

        setResponse(
          result.response,
        );

        if (
          result.success
        ) {
          await speak(
            result.response,
          );
        }
      } catch (error) {
        console.error(error);

        setResponse(
          "Voice processing failed.",
        );
      } finally {
        setIsLoading(false);
      }
    };

  // =====================================================
  // WAKE WORD DETECTED
  // =====================================================

  const handleWakeWord =
    async () => {
      if (
        conversationBusyRef.current
      ) {
        return;
      }

      conversationBusyRef.current =
        true;

      try {
        console.log(
          "HEY JARVIS DETECTED",
        );

        // Stop wake-word microphone so
        // it does not hear JARVIS itself.
        await wakeWordRef.current
          ?.stop();

        setResponse("Yes?");

        await speak("Yes?");

        // Automatically listen to
        // user's next sentence.
        await processVoiceCommand();
      } catch (error) {
        console.error(
          "Conversation error:",
          error,
        );

        setResponse(
          "Conversation failed.",
        );
      } finally {
        setIsListening(false);

        conversationBusyRef.current =
          false;

        // Resume waiting for Hey Jarvis.
        if (
          mountedRef.current &&
          wakeWordRef.current
        ) {
          try {
            await wakeWordRef.current
              .start();

            setResponse(
              'Waiting for "Hey Jarvis"...',
            );
          } catch (error) {
            console.error(
              "Wake listener restart error:",
              error,
            );

            setResponse(
              "Wake-word listener failed.",
            );
          }
        }
      }
    };

  // =====================================================
  // ENABLE HANDS-FREE JARVIS
  // =====================================================

  const enableJarvis =
    async () => {
      if (isEnabled) {
        return;
      }

      try {
        setResponse(
          "Starting JARVIS...",
        );

        const listener =
          new WakeWordListener(
            () => {
              void handleWakeWord();
            },
          );

        wakeWordRef.current =
          listener;

        await listener.start();

        setIsEnabled(true);

        setResponse(
          'Waiting for "Hey Jarvis"...',
        );
      } catch (error) {
        console.error(
          "Enable JARVIS error:",
          error,
        );

        setResponse(
          "Unable to enable hands-free mode.",
        );
      }
    };

  // =====================================================
  // DISABLE HANDS-FREE JARVIS
  // =====================================================

  const disableJarvis =
    async () => {
      try {
        conversationBusyRef.current =
          true;

        window.speechSynthesis
          ?.cancel();

        await wakeWordRef.current
          ?.stop();

        wakeWordRef.current = null;

        setIsEnabled(false);
        setIsListening(false);
        setIsSpeaking(false);

        setResponse(
          "JARVIS hands-free mode disabled.",
        );
      } finally {
        conversationBusyRef.current =
          false;
      }
    };

  // =====================================================
  // CLEANUP
  // =====================================================

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;

      window.speechSynthesis
        ?.cancel();

      void wakeWordRef.current
        ?.stop();
    };
  }, []);

  // =====================================================
  // UI
  // =====================================================

  return (
    <main>
      <h1>JARVIS</h1>

      <p>
        {isListening
          ? `🎙 ${response}`
          : isSpeaking
            ? `🔊 ${response}`
            : response}
      </p>

      {!isEnabled ? (
        <button
          type="button"
          onClick={enableJarvis}
        >
          Enable JARVIS
        </button>
      ) : (
        <button
          type="button"
          onClick={() => {
            void disableJarvis();
          }}
        >
          Disable Hands-Free
        </button>
      )}

      {isEnabled && (
        <p>
          🟢 Hands-free mode active
        </p>
      )}

      <form
        onSubmit={handleSubmit}
      >
        <input
          value={command}
          onChange={(event) =>
            setCommand(
              event.target.value,
            )
          }
          placeholder="Ask JARVIS..."
          disabled={
            isLoading ||
            isListening
          }
        />

        <button
          type="submit"
          disabled={
            isLoading ||
            isListening ||
            isSpeaking ||
            !command.trim()
          }
        >
          {isLoading
            ? "Processing..."
            : "Send"}
        </button>
      </form>
    </main>
  );
}

export default App;