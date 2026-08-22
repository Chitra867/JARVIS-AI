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


type VoiceTurnResult =
  | "continue"
  | "end"
  | "silence";


const MAX_CONVERSATION_TURNS = 20;

const FIRST_COMMAND_TIMEOUT = 6000;
const FOLLOW_UP_TIMEOUT = 6000;

const TTS_API_URL =
  "http://127.0.0.1:8000/api/tts";


const END_CONVERSATION_PHRASES = new Set([
  "thanks",
  "thank you",
  "thanks jarvis",
  "thank you jarvis",

  "that's all",
  "thats all",

  "that's it",
  "thats it",

  "stop listening",
  "stop conversation",
  "end conversation",

  "goodbye",
  "goodbye jarvis",

  "bye",
  "bye jarvis",
]);


function App() {
  const [command, setCommand] =
    useState("");

  const [response, setResponse] =
    useState(
      "Click Enable JARVIS to start hands-free mode.",
    );

  const [isLoading, setIsLoading] =
    useState(false);

  const [isEnabled, setIsEnabled] =
    useState(false);

  const [isListening, setIsListening] =
    useState(false);

  const [isSpeaking, setIsSpeaking] =
    useState(false);


  // =====================================================
  // REFS
  // =====================================================

  const wakeWordRef =
    useRef<WakeWordListener | null>(
      null,
    );

  const conversationBusyRef =
    useRef(false);

  const mountedRef =
    useRef(true);

  const enabledRef =
    useRef(false);

  const cancelConversationRef =
    useRef(false);

  const wakeHandlerRef =
    useRef<() => void>(() => {});


  // =====================================================
  // NEURAL TTS AUDIO REFS
  // =====================================================

  const audioRef =
    useRef<HTMLAudioElement | null>(
      null,
    );

  const audioUrlRef =
    useRef<string | null>(
      null,
    );

  const ttsAbortRef =
    useRef<AbortController | null>(
      null,
    );


  // =====================================================
  // STOP CURRENT SPEECH
  // =====================================================

  const stopSpeech = () => {
    // Cancel an in-progress TTS download.
    if (ttsAbortRef.current) {
      ttsAbortRef.current.abort();

      ttsAbortRef.current = null;
    }

    // Stop currently playing neural audio.
    if (audioRef.current) {
      try {
        audioRef.current.pause();

        audioRef.current.currentTime = 0;
      } catch {
        // Audio may already be stopped.
      }

      audioRef.current = null;
    }

    // Release the browser Blob URL.
    if (audioUrlRef.current) {
      URL.revokeObjectURL(
        audioUrlRef.current,
      );

      audioUrlRef.current = null;
    }

    // Browser TTS is no longer the primary engine,
    // but cancel any legacy speech that may exist.
    if (
      "speechSynthesis"
      in window
    ) {
      window.speechSynthesis.cancel();
    }

    if (mountedRef.current) {
      setIsSpeaking(false);
    }
  };


  // =====================================================
  // BROWSER TTS FALLBACK
  // =====================================================
  //
  // This is used ONLY if the neural FastAPI TTS
  // endpoint is unavailable.
  // =====================================================

  const speakFallback = (
    text: string,
  ): Promise<void> => {
    return new Promise(
      (resolve) => {
        if (
          !text.trim()
          || !(
            "speechSynthesis"
            in window
          )
        ) {
          resolve();

          return;
        }

        window.speechSynthesis.cancel();

        const utterance =
          new SpeechSynthesisUtterance(
            text,
          );

        utterance.rate = 0.92;
        utterance.pitch = 0.8;
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
      },
    );
  };


  // =====================================================
  // JARVIS NEURAL SPEECH
  // =====================================================

  const speak = async (
    text: string,
  ): Promise<void> => {
    const cleanText =
      text.trim();

    if (!cleanText) {
      return;
    }

    // Stop any previous response first.
    stopSpeech();

    const controller =
      new AbortController();

    ttsAbortRef.current =
      controller;

    try {
      if (mountedRef.current) {
        setIsSpeaking(true);
      }

      const ttsResponse =
        await fetch(
          TTS_API_URL,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              text: cleanText,
            }),

            signal:
              controller.signal,
          },
        );

      if (!ttsResponse.ok) {
        const errorText =
          await ttsResponse.text();

        throw new Error(
          (
            "JARVIS TTS request failed: "
            + ttsResponse.status
            + " "
            + errorText
          ),
        );
      }

      const audioBlob =
        await ttsResponse.blob();

      if (
        audioBlob.size <= 0
      ) {
        throw new Error(
          "JARVIS TTS returned empty audio.",
        );
      }

      const audioUrl =
        URL.createObjectURL(
          audioBlob,
        );

      audioUrlRef.current =
        audioUrl;

      const audio =
        new Audio(
          audioUrl,
        );

      audioRef.current =
        audio;

      audio.preload = "auto";
      audio.volume = 1;

      await new Promise<void>(
        (
          resolve,
          reject,
        ) => {
          audio.onended = () => {
            resolve();
          };

          audio.onerror = () => {
            reject(
              new Error(
                "Unable to play JARVIS neural audio.",
              ),
            );
          };

          audio.play().catch(
            reject,
          );
        },
      );
    } catch (error) {
      // Abort is expected when JARVIS is disabled
      // or another response interrupts speech.
      if (
        error instanceof DOMException
        && error.name ===
          "AbortError"
      ) {
        return;
      }

      console.error(
        "JARVIS neural TTS error:",
        error,
      );

      // Keep the assistant usable even if
      // edge-tts or the internet is unavailable.
      await speakFallback(
        cleanText,
      );
    } finally {
      if (
        ttsAbortRef.current
        === controller
      ) {
        ttsAbortRef.current =
          null;
      }

      if (audioRef.current) {
        audioRef.current =
          null;
      }

      if (audioUrlRef.current) {
        URL.revokeObjectURL(
          audioUrlRef.current,
        );

        audioUrlRef.current =
          null;
      }

      if (mountedRef.current) {
        setIsSpeaking(false);
      }
    }
  };


  // =====================================================
  // DISPLAY + SPEAK
  // =====================================================

  const respond = async (
    text: string,
    shouldSpeak = true,
  ): Promise<void> => {
    if (!mountedRef.current) {
      return;
    }

    setResponse(
      text,
    );

    if (shouldSpeak) {
      await speak(
        text,
      );
    }
  };


  // =====================================================
  // NORMALIZE TRANSCRIPT
  // =====================================================

  const normalizeTranscript = (
    text: string,
  ): string => {
    return text
      .trim()
      .toLowerCase()
      .replace(
        /[.,!?;:]+$/g,
        "",
      )
      .replace(
        /\s+/g,
        " ",
      );
  };


  // =====================================================
  // CHECK END OF CONVERSATION
  // =====================================================

  const isEndConversationCommand = (
    text: string,
  ): boolean => {
    const normalized =
      normalizeTranscript(
        text,
      );

    return (
      END_CONVERSATION_PHRASES
      .has(
        normalized,
      )
    );
  };


  const getConversationEndResponse = (
    text: string,
  ): string => {
    const normalized =
      normalizeTranscript(
        text,
      );

    if (
      normalized.includes(
        "thank",
      )
      || normalized ===
        "thanks"
      || normalized ===
        "thanks jarvis"
    ) {
      return (
        "You're welcome."
      );
    }

    if (
      normalized.includes(
        "goodbye",
      )
      || normalized ===
        "bye"
      || normalized ===
        "bye jarvis"
    ) {
      return "Goodbye.";
    }

    return "Okay.";
  };


  // =====================================================
  // TEXT COMMAND
  // =====================================================

  const handleSubmit = async (
    event:
      FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    const trimmedCommand =
      command.trim();

    if (
      !trimmedCommand
      || isLoading
      || conversationBusyRef.current
    ) {
      return;
    }

    conversationBusyRef.current =
      true;

    let wakeWasRunning =
      false;

    try {
      if (
        enabledRef.current
        && wakeWordRef.current
      ) {
        wakeWasRunning =
          true;

        await wakeWordRef.current
          .stop();
      }

      setIsLoading(
        true,
      );

      setResponse(
        "Processing...",
      );

      const result =
        await sendCommand(
          trimmedCommand,
        );

      setCommand(
        "",
      );

      await respond(
        result.response,
      );
    } catch (error) {
      console.error(
        "Text command error:",
        error,
      );

      await respond(
        "Unable to communicate with JARVIS core.",
      );
    } finally {
      setIsLoading(
        false,
      );

      conversationBusyRef.current =
        false;

      if (
        wakeWasRunning
        && enabledRef.current
        && mountedRef.current
        && wakeWordRef.current
      ) {
        try {
          await wakeWordRef.current
            .start();
        } catch (error) {
          console.error(
            "Wake listener restart error:",
            error,
          );
        }
      }
    }
  };


  // =====================================================
  // AUTOMATIC COMMAND RECORDING
  // =====================================================

  const recordCommand = async (
    noSpeechTimeout =
      FIRST_COMMAND_TIMEOUT,

    listeningMessage =
      "Listening...",
  ): Promise<Blob | null> => {
    if (
      !navigator.mediaDevices
        ?.getUserMedia
    ) {
      await respond(
        "Microphone is not supported.",
      );

      return null;
    }

    if (
      !(
        "MediaRecorder"
        in window
      )
    ) {
      await respond(
        "Audio recording is not supported.",
      );

      return null;
    }

    let stream:
      | MediaStream
      | null = null;

    let audioContext:
      | AudioContext
      | null = null;

    try {
      stream =
        await navigator
          .mediaDevices
          .getUserMedia({
            audio: {
              echoCancellation:
                true,

              noiseSuppression:
                true,

              autoGainControl:
                true,

              channelCount:
                1,
            },
          });

      audioContext =
        new AudioContext();

      if (
        audioContext.state
        === "suspended"
      ) {
        await audioContext
          .resume();
      }

      const recorder =
        new MediaRecorder(
          stream,
        );

      const chunks:
        Blob[] = [];

      const source =
        audioContext
          .createMediaStreamSource(
            stream,
          );

      const analyser =
        audioContext
          .createAnalyser();

      analyser.fftSize =
        2048;

      analyser
        .smoothingTimeConstant =
        0.2;

      source.connect(
        analyser,
      );

      const samples =
        new Uint8Array(
          analyser.fftSize,
        );

      return await new Promise<
        Blob | null
      >((resolve) => {
        let speechDetected =
          false;

        let silenceStarted:
          | number
          | null = null;

        const startedAt =
          Date.now();

        let animationFrame =
          0;

        let finished =
          false;

        const finish = (
          value:
            Blob | null,
        ) => {
          if (finished) {
            return;
          }

          finished = true;

          resolve(
            value,
          );
        };

        const stopRecorder =
          () => {
            if (
              recorder.state
              === "recording"
            ) {
              recorder.stop();
            }
          };

        const cleanup =
          async () => {
            cancelAnimationFrame(
              animationFrame,
            );

            try {
              source.disconnect();
            } catch {
              // already disconnected
            }

            try {
              analyser.disconnect();
            } catch {
              // already disconnected
            }

            stream
              ?.getTracks()
              .forEach(
                (track) => {
                  track.stop();
                },
              );

            if (
              audioContext
              && audioContext.state
                !== "closed"
            ) {
              await audioContext
                .close();
            }
          };

        recorder.ondataavailable =
          (event) => {
            if (
              event.data.size
              > 0
            ) {
              chunks.push(
                event.data,
              );
            }
          };

        recorder.onerror =
          async (event) => {
            console.error(
              "Recorder error:",
              event,
            );

            await cleanup();

            finish(
              null,
            );
          };

        recorder.onstop =
          async () => {
            await cleanup();

            if (
              !speechDetected
              || cancelConversationRef
                .current
            ) {
              finish(
                null,
              );

              return;
            }

            const blob =
              new Blob(
                chunks,
                {
                  type:
                    recorder.mimeType
                    || "audio/webm",
                },
              );

            finish(
              blob.size > 0
                ? blob
                : null,
            );
          };

        const monitorAudio =
          () => {
            if (
              cancelConversationRef
                .current
            ) {
              stopRecorder();

              return;
            }

            analyser
              .getByteTimeDomainData(
                samples,
              );

            let sum =
              0;

            for (
              let index = 0;
              index
              < samples.length;
              index++
            ) {
              const normalized =
                (
                  samples[index]
                  - 128
                )
                / 128;

              sum +=
                normalized
                * normalized;
            }

            const rms =
              Math.sqrt(
                sum
                / samples.length,
              );

            const speechThreshold =
              0.015;

            if (
              rms
              > speechThreshold
            ) {
              speechDetected =
                true;

              silenceStarted =
                null;
            } else if (
              speechDetected
            ) {
              if (
                silenceStarted
                === null
              ) {
                silenceStarted =
                  Date.now();
              }

              if (
                Date.now()
                - silenceStarted
                >= 1200
              ) {
                stopRecorder();

                return;
              }
            }

            if (
              !speechDetected
              && (
                Date.now()
                - startedAt
                > noSpeechTimeout
              )
            ) {
              stopRecorder();

              return;
            }

            if (
              Date.now()
              - startedAt
              > 15000
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

        setIsListening(
          true,
        );

        setResponse(
          listeningMessage,
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
          (track) => {
            track.stop();
          },
        );

      if (
        audioContext
        && audioContext.state
          !== "closed"
      ) {
        await audioContext
          .close();
      }

      setIsListening(
        false,
      );

      return null;
    }
  };


  // =====================================================
  // PROCESS ONE CONVERSATION TURN
  // =====================================================

  const processVoiceTurn = async (
    firstTurn: boolean,
  ): Promise<VoiceTurnResult> => {
    if (
      cancelConversationRef
        .current
    ) {
      return "end";
    }

    const audio =
      await recordCommand(
        firstTurn
          ? FIRST_COMMAND_TIMEOUT
          : FOLLOW_UP_TIMEOUT,

        firstTurn
          ? "Listening..."
          : "Listening for follow-up...",
      );

    setIsListening(
      false,
    );

    if (
      cancelConversationRef
        .current
    ) {
      return "end";
    }

    if (!audio) {
      return "silence";
    }

    try {
      setIsLoading(
        true,
      );

      setResponse(
        "Processing...",
      );

      const result =
        await sendVoice(
          audio,
        );

      const transcript =
        result.transcript
          ?.trim()
        || "";

      if (transcript) {
        setCommand(
          transcript,
        );
      }

      if (!transcript) {
        await respond(
          result.response
          || (
            "I couldn't hear "
            + "that clearly."
          ),
        );

        return "end";
      }

      if (
        isEndConversationCommand(
          transcript,
        )
      ) {
        await respond(
          getConversationEndResponse(
            transcript,
          ),
        );

        return "end";
      }

      await respond(
        result.response,
      );

      if (!result.success) {
        return "end";
      }

      return "continue";
    } catch (error) {
      console.error(
        "Voice processing error:",
        error,
      );

      await respond(
        "Voice processing failed.",
      );

      return "end";
    } finally {
      setIsLoading(
        false,
      );
    }
  };


  // =====================================================
  // CONTINUOUS CONVERSATION
  // =====================================================

  const runConversation =
    async (): Promise<void> => {
      await respond(
        "Yes?",
      );

      for (
        let turn = 0;
        turn
        < MAX_CONVERSATION_TURNS;
        turn++
      ) {
        if (
          cancelConversationRef
            .current
          || !enabledRef.current
          || !mountedRef.current
        ) {
          break;
        }

        const result =
          await processVoiceTurn(
            turn === 0,
          );

        if (
          result === "end"
          || result === "silence"
        ) {
          break;
        }
      }
    };


  // =====================================================
  // WAKE WORD DETECTED
  // =====================================================

  const handleWakeWord =
    async (): Promise<void> => {
      if (
        conversationBusyRef
          .current
        || !enabledRef.current
      ) {
        return;
      }

      conversationBusyRef.current =
        true;

      cancelConversationRef.current =
        false;

      try {
        console.log(
          "HEY JARVIS DETECTED",
        );

        await wakeWordRef.current
          ?.stop();

        await runConversation();
      } catch (error) {
        console.error(
          "Conversation error:",
          error,
        );

        await respond(
          "Conversation failed.",
        );
      } finally {
        setIsListening(
          false,
        );

        setIsLoading(
          false,
        );

        conversationBusyRef.current =
          false;

        if (
          mountedRef.current
          && enabledRef.current
          && wakeWordRef.current
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
  // KEEP WAKE CALLBACK CURRENT
  // =====================================================

  useEffect(() => {
    wakeHandlerRef.current =
      () => {
        void handleWakeWord();
      };
  });


  // =====================================================
  // ENABLE HANDS-FREE
  // =====================================================

  const enableJarvis =
    async () => {
      if (
        enabledRef.current
      ) {
        return;
      }

      try {
        setResponse(
          "Starting JARVIS...",
        );

        cancelConversationRef.current =
          false;

        const listener =
          new WakeWordListener(
            () => {
              wakeHandlerRef.current();
            },
          );

        wakeWordRef.current =
          listener;

        await listener.start();

        enabledRef.current =
          true;

        setIsEnabled(
          true,
        );

        setResponse(
          'Waiting for "Hey Jarvis"...',
        );
      } catch (error) {
        console.error(
          "Enable JARVIS error:",
          error,
        );

        enabledRef.current =
          false;

        setIsEnabled(
          false,
        );

        await respond(
          "Unable to enable hands-free mode.",
        );
      }
    };


  // =====================================================
  // DISABLE HANDS-FREE
  // =====================================================

  const disableJarvis =
    async () => {
      try {
        cancelConversationRef.current =
          true;

        enabledRef.current =
          false;

        // Stop neural TTS immediately.
        stopSpeech();

        await wakeWordRef.current
          ?.stop();

        wakeWordRef.current =
          null;

        setIsEnabled(
          false,
        );

        setIsListening(
          false,
        );

        setIsSpeaking(
          false,
        );

        setIsLoading(
          false,
        );

        setResponse(
          "JARVIS hands-free mode disabled.",
        );
      } catch (error) {
        console.error(
          "Disable JARVIS error:",
          error,
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
    mountedRef.current =
      true;

    return () => {
      mountedRef.current =
        false;

      enabledRef.current =
        false;

      cancelConversationRef.current =
        true;

      if (
        ttsAbortRef.current
      ) {
        ttsAbortRef.current
          .abort();

        ttsAbortRef.current =
          null;
      }

      if (
        audioRef.current
      ) {
        try {
          audioRef.current
            .pause();
        } catch {
          // already stopped
        }

        audioRef.current =
          null;
      }

      if (
        audioUrlRef.current
      ) {
        URL.revokeObjectURL(
          audioUrlRef.current,
        );

        audioUrlRef.current =
          null;
      }

      if (
        "speechSynthesis"
        in window
      ) {
        window.speechSynthesis
          .cancel();
      }

      void wakeWordRef.current
        ?.stop();
    };
  }, []);


  // =====================================================
  // UI
  // =====================================================

  return (
    <main className="jarvis-shell">
      <div
        className="ambient ambient-one"
      />

      <div
        className="ambient ambient-two"
      />

      <div
        className="grid-overlay"
      />

      <header className="topbar">
        <div className="brand">
          <div
            className="brand-mark"
            aria-hidden="true"
          >
            <span>J</span>
          </div>

          <div>
            <strong>
              JARVIS OS
            </strong>

            <small>
              Personal Intelligence System
            </small>
          </div>
        </div>

        <div className="topbar-status">
          <span className="status-pill">
            <i className="status-dot" />

            Local Core
          </span>

          <span
            className={
              "status-pill "
              + "status-pill-muted"
            }
          >
            Private • On-device AI
          </span>
        </div>
      </header>

      <div className="workspace">
        <aside
          className={
            "panel sidebar "
            + "left-sidebar"
          }
        >
          <div className="panel-heading">
            <span>
              System
            </span>

            <b>
              LIVE
            </b>
          </div>

          <div className="system-list">
            <div className="system-row">
              <span className="system-icon">
                ◎
              </span>

              <div>
                <strong>
                  JARVIS Core
                </strong>

                <small>
                  {isLoading
                    ? "Processing request"
                    : "Ready"}
                </small>
              </div>

              <span
                className={
                  `mini-led ${
                    isLoading
                      ? "busy"
                      : "online"
                  }`
                }
              />
            </div>

            <div className="system-row">
              <span className="system-icon">
                ◉
              </span>

              <div>
                <strong>
                  Voice Engine
                </strong>

                <small>
                  {isEnabled
                    ? "Hands-free enabled"
                    : "Standby"}
                </small>
              </div>

              <span
                className={
                  `mini-led ${
                    isEnabled
                      ? "online"
                      : "idle"
                  }`
                }
              />
            </div>

            <div className="system-row">
              <span className="system-icon">
                ⌁
              </span>

              <div>
                <strong>
                  Wake Word
                </strong>

                <small>
                  {isEnabled
                    ? 'Waiting for "Hey Jarvis"'
                    : "Disabled"}
                </small>
              </div>

              <span
                className={
                  `mini-led ${
                    isEnabled
                      ? "online"
                      : "idle"
                  }`
                }
              />
            </div>

            <div className="system-row">
              <span className="system-icon">
                ◇
              </span>

              <div>
                <strong>
                  Memory
                </strong>

                <small>
                  Persistent context
                </small>
              </div>

              <span className="mini-led online" />
            </div>
          </div>

          <div className="section-label">
            Quick commands
          </div>

          <div className="quick-actions">
            <button
              type="button"
              onClick={() =>
                setCommand(
                  "open chrome",
                )
              }
            >
              <span>↗</span>

              Open Chrome
            </button>

            <button
              type="button"
              onClick={() =>
                setCommand(
                  "open youtube",
                )
              }
            >
              <span>▶</span>

              Open YouTube
            </button>

            <button
              type="button"
              onClick={() =>
                setCommand(
                  "search for FastAPI",
                )
              }
            >
              <span>⌕</span>

              Search Web
            </button>

            <button
              type="button"
              onClick={() =>
                setCommand(
                  "show active memories",
                )
              }
            >
              <span>◆</span>

              Memories
            </button>
          </div>

          <div className="sidebar-note">
            <span>
              TIP
            </span>

            Try a multi-step command such
            as “Open Chrome, search Python
            decorators, then open YouTube.”
          </div>
        </aside>

        <section className="console">
          <div className="console-topline">
            <span>
              NEURAL INTERFACE
            </span>

            <span>
              {isListening
                ? "VOICE INPUT"
                : isSpeaking
                  ? "NEURAL VOICE"
                  : isLoading
                    ? "PROCESSING"
                    : "READY"}
            </span>
          </div>

          <div
            className={
              `core-visual ${
                isListening
                  ? "listening"
                  : isSpeaking
                    ? "speaking"
                    : isLoading
                      ? "thinking"
                      : "idle"
              }`
            }
            aria-label="JARVIS core status"
          >
            <div className="core-glow" />

            <div className="orbit orbit-one">
              <span />
            </div>

            <div className="orbit orbit-two">
              <span />
            </div>

            <div className="orbit orbit-three" />

            <div className="core-center">
              <span>
                J
              </span>
            </div>
          </div>

          <div className="hero-copy">
            <div className="eyebrow">
              {isListening
                ? "Listening to you"
                : isSpeaking
                  ? "Neural voice active"
                  : isLoading
                    ? "Thinking"
                    : isEnabled
                      ? "Hands-free ready"
                      : "Command interface ready"}
            </div>

            <h1>
              JARVIS
            </h1>

            <p>
              Local intelligence.
              Persistent memory.
              Real computer actions.
            </p>
          </div>

          <section
            className="response-panel"
            aria-live="polite"
          >
            <div className="response-head">
              <div>
                <span className="response-avatar">
                  J
                </span>

                <div>
                  <strong>
                    JARVIS
                  </strong>

                  <small>
                    {isLoading
                      ? "Processing"
                      : isListening
                        ? "Listening"
                        : isSpeaking
                          ? "Speaking"
                          : "Response"}
                  </small>
                </div>
              </div>

              <span className="response-state">
                {isLoading
                  ? "•••"
                  : "ACTIVE"}
              </span>
            </div>

            <div className="response-text">
              {isListening ? (
                <span className="voice-line">
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />

                  {response}
                </span>
              ) : (
                response
              )}
            </div>
          </section>

          <form
            className="command-bar"
            onSubmit={handleSubmit}
          >
            <div className="command-prefix">
              ›_
            </div>

            <input
              value={command}
              onChange={(event) =>
                setCommand(
                  event.target.value,
                )
              }
              placeholder={
                "Ask JARVIS or "
                + "give a command..."
              }
              autoComplete="off"
              disabled={
                isLoading
                || isListening
                || isSpeaking
              }
            />

            <button
              className="send-button"
              type="submit"
              disabled={
                isLoading
                || isListening
                || isSpeaking
                || !command.trim()
              }
            >
              {isLoading
                ? "Working"
                : "Send"}

              <span>
                ↗
              </span>
            </button>
          </form>

          <div className="voice-control-row">
            {!isEnabled ? (
              <button
                className={
                  "voice-toggle enable"
                }
                type="button"
                onClick={() =>
                  void enableJarvis()
                }
              >
                <span className="mic-icon">
                  ◉
                </span>

                Enable hands-free JARVIS
              </button>
            ) : (
              <button
                className={
                  "voice-toggle disable"
                }
                type="button"
                onClick={() =>
                  void disableJarvis()
                }
              >
                <span className="mic-icon">
                  ■
                </span>

                Disable hands-free
              </button>
            )}

            <span className="voice-hint">
              {isEnabled
                ? 'Say “Hey Jarvis” to begin'
                : (
                  "Microphone remains off "
                  + "until enabled"
                )}
            </span>
          </div>
        </section>

        <aside
          className={
            "panel sidebar "
            + "right-sidebar"
          }
        >
          <div className="panel-heading">
            <span>
              Activity
            </span>

            <b>
              AUTO
            </b>
          </div>

          <div
            className={
              "activity-card "
              + "primary-activity"
            }
          >
            <span className="activity-kicker">
              CURRENT STATE
            </span>

            <strong>
              {isListening
                ? "Listening"
                : isSpeaking
                  ? "Speaking"
                  : isLoading
                    ? "Reasoning"
                    : isEnabled
                      ? "Awaiting wake word"
                      : "Ready for command"}
            </strong>

            <small>
              {isEnabled
                ? (
                  "Continuous voice "
                  + "mode is available."
                )
                : (
                  "Use text input or "
                  + "enable hands-free mode."
                )}
            </small>
          </div>

          <div className="section-label">
            Capabilities
          </div>

          <div className="capability-list">
            <div>
              <span>
                01
              </span>

              <p>
                <strong>
                  Reason
                </strong>

                <small>
                  Local Ollama intelligence
                </small>
              </p>
            </div>

            <div>
              <span>
                02
              </span>

              <p>
                <strong>
                  Remember
                </strong>

                <small>
                  Persistent long-term memory
                </small>
              </p>
            </div>

            <div>
              <span>
                03
              </span>

              <p>
                <strong>
                  Act
                </strong>

                <small>
                  Apps, search and task execution
                </small>
              </p>
            </div>

            <div>
              <span>
                04
              </span>

              <p>
                <strong>
                  Plan safely
                </strong>

                <small>
                  Validated multi-step commands
                </small>
              </p>
            </div>
          </div>

          <div className="safety-card">
            <div className="shield">
              ◇
            </div>

            <div>
              <strong>
                Safety guard active
              </strong>

              <small>
                Unsupported actions are
                blocked before execution.
              </small>
            </div>
          </div>
        </aside>
      </div>

      <footer className="footer-bar">
        <span>
          JARVIS OS • LOCAL DEVELOPMENT BUILD
        </span>

        <span className="footer-center">
          PRIVATE • LOCAL • PERSISTENT
        </span>

        <span>
          {new Date().toLocaleDateString()}
        </span>
      </footer>
    </main>
  );
}


export default App;