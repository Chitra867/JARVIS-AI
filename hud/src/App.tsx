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
  // SPEAK
  // =====================================================

  const speak = (
    text: string,
  ): Promise<void> => {
    return new Promise((resolve) => {
      if (
        !text.trim() ||
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
  // DISPLAY + SPEAK
  // =====================================================

  const respond = async (
    text: string,
    shouldSpeak = true,
  ): Promise<void> => {
    if (!mountedRef.current) {
      return;
    }

    setResponse(text);

    if (shouldSpeak) {
      await speak(text);
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
      .replace(/[.,!?;:]+$/g, "")
      .replace(/\s+/g, " ");
  };


  // =====================================================
  // CHECK END OF CONVERSATION
  // =====================================================

  const isEndConversationCommand = (
    text: string,
  ): boolean => {
    const normalized =
      normalizeTranscript(text);

    return END_CONVERSATION_PHRASES.has(
      normalized,
    );
  };


  const getConversationEndResponse = (
    text: string,
  ): string => {
    const normalized =
      normalizeTranscript(text);

    if (
      normalized.includes("thank")
      || normalized === "thanks"
      || normalized === "thanks jarvis"
    ) {
      return "You're welcome.";
    }

    if (
      normalized.includes("goodbye")
      || normalized === "bye"
      || normalized === "bye jarvis"
    ) {
      return "Goodbye.";
    }

    return "Okay.";
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

    let wakeWasRunning = false;

    try {
      if (
        enabledRef.current &&
        wakeWordRef.current
      ) {
        wakeWasRunning = true;

        await wakeWordRef.current.stop();
      }

      setIsLoading(true);

      setResponse(
        "Processing...",
      );

      const result =
        await sendCommand(
          trimmedCommand,
        );

      setCommand("");

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
      setIsLoading(false);

      conversationBusyRef.current =
        false;

      if (
        wakeWasRunning &&
        enabledRef.current &&
        mountedRef.current &&
        wakeWordRef.current
      ) {
        try {
          await wakeWordRef.current.start();
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
      !("MediaRecorder" in window)
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
        await navigator.mediaDevices
          .getUserMedia({
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
              channelCount: 1,
            },
          });


      audioContext =
        new AudioContext();

      if (
        audioContext.state ===
        "suspended"
      ) {
        await audioContext.resume();
      }


      const recorder =
        new MediaRecorder(
          stream,
        );

      const chunks: Blob[] = [];


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
        let speechDetected = false;

        let silenceStarted:
          | number
          | null = null;

        const startedAt =
          Date.now();

        let animationFrame = 0;

        let finished = false;


        const finish = (
          value: Blob | null,
        ) => {
          if (finished) {
            return;
          }

          finished = true;

          resolve(value);
        };


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


        recorder.onerror =
          async (event) => {
            console.error(
              "Recorder error:",
              event,
            );

            await cleanup();

            finish(null);
          };


        recorder.onstop =
          async () => {
            await cleanup();

            if (
              !speechDetected ||
              cancelConversationRef.current
            ) {
              finish(null);
              return;
            }

            const blob =
              new Blob(
                chunks,
                {
                  type:
                    recorder.mimeType ||
                    "audio/webm",
                },
              );

            finish(
              blob.size > 0
                ? blob
                : null,
            );
          };


        const monitorAudio = () => {
          if (
            cancelConversationRef.current
          ) {
            stopRecorder();
            return;
          }


          analyser
            .getByteTimeDomainData(
              samples,
            );


          let sum = 0;

          for (
            let index = 0;
            index < samples.length;
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


            // User finished speaking.
            if (
              Date.now() -
                silenceStarted >=
              1200
            ) {
              stopRecorder();
              return;
            }
          }


          // No speech.
          if (
            !speechDetected &&
            Date.now() -
              startedAt >
              noSpeechTimeout
          ) {
            stopRecorder();
            return;
          }


          // Maximum utterance length.
          if (
            Date.now() -
              startedAt >
            15000
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

      setIsListening(false);

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
      cancelConversationRef.current
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


    setIsListening(false);


    if (
      cancelConversationRef.current
    ) {
      return "end";
    }


    // User stayed silent.
    if (!audio) {
      return "silence";
    }


    try {
      setIsLoading(true);

      setResponse(
        "Processing...",
      );


      const result =
        await sendVoice(
          audio,
        );


      const transcript =
        result.transcript?.trim() || "";


      if (transcript) {
        setCommand(
          transcript,
        );
      }


      if (!transcript) {
        await respond(
          result.response ||
            "I couldn't hear that clearly.",
        );

        return "end";
      }


      // -----------------------------------------------
      // User wants to finish conversation.
      // -----------------------------------------------

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


      // -----------------------------------------------
      // Speak actual JARVIS result.
      // -----------------------------------------------

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
      setIsLoading(false);
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
        turn <
        MAX_CONVERSATION_TURNS;
        turn++
      ) {
        if (
          cancelConversationRef.current ||
          !enabledRef.current ||
          !mountedRef.current
        ) {
          break;
        }


        const result =
          await processVoiceTurn(
            turn === 0,
          );


        if (
          result === "end"
        ) {
          break;
        }


        if (
          result === "silence"
        ) {
          break;
        }


        // result === "continue"
        //
        // JARVIS has already spoken.
        // We now automatically begin listening
        // for the next user sentence.
      }
    };


  // =====================================================
  // WAKE WORD DETECTED
  // =====================================================

  const handleWakeWord =
    async (): Promise<void> => {
      if (
        conversationBusyRef.current ||
        !enabledRef.current
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


        // Stop wake-word listener so it
        // cannot hear JARVIS speaking.
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
        setIsListening(false);

        setIsLoading(false);

        conversationBusyRef.current =
          false;


        // ---------------------------------------------
        // Return to wake-word mode only if
        // hands-free is still enabled.
        // ---------------------------------------------

        if (
          mountedRef.current &&
          enabledRef.current &&
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


  // Keep WakeWordListener callback pointed
  // at the newest handler after render.
  useEffect(() => {
    wakeHandlerRef.current = () => {
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


        enabledRef.current = true;

        setIsEnabled(true);


        setResponse(
          'Waiting for "Hey Jarvis"...',
        );
      } catch (error) {
        console.error(
          "Enable JARVIS error:",
          error,
        );

        enabledRef.current = false;

        setIsEnabled(false);

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


        window.speechSynthesis
          ?.cancel();


        await wakeWordRef.current
          ?.stop();


        wakeWordRef.current =
          null;


        setIsEnabled(false);

        setIsListening(false);

        setIsSpeaking(false);

        setIsLoading(false);


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
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;

      enabledRef.current = false;

      cancelConversationRef.current =
        true;

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
          onClick={() => {
            void enableJarvis();
          }}
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
            isListening ||
            isSpeaking
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