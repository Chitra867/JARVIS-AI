import { useRef, useState, type FormEvent } from "react";

import { sendCommand, sendVoice } from "./services/jarvisApi";

import "./App.css";

function App() {
  const [command, setCommand] = useState("");
  const [response, setResponse] = useState("JARVIS ready.");
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedCommand = command.trim();

    if (!trimmedCommand || isLoading) {
      return;
    }

    try {
      setIsLoading(true);
      setResponse("Processing...");

      const result = await sendCommand(trimmedCommand);

      setResponse(result.response);
      setCommand("");
    } catch (error) {
      console.error(error);
      setResponse("Unable to communicate with JARVIS core.");
    } finally {
      setIsLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });

      chunksRef.current = [];

      const recorder = new MediaRecorder(stream);

      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });

        stream.getTracks().forEach((track) => track.stop());

        try {
          setIsLoading(true);
          setResponse("Processing voice...");

          const result = await sendVoice(audioBlob);

          if (result.transcript) {
            setCommand(result.transcript);
          }

          setResponse(result.response);
        } catch (error) {
          console.error(error);

          setResponse("Voice processing failed.");
        } finally {
          setIsLoading(false);
          setIsRecording(false);
        }
      };

      recorder.start();

      setIsRecording(true);
      setResponse("Listening...");
    } catch (error) {
      console.error(error);

      setResponse("Microphone permission denied or unavailable.");
    }
  };

  const stopRecording = () => {
    const recorder = recorderRef.current;

    if (recorder && recorder.state === "recording") {
      recorder.stop();
    }
  };

  const handleMicrophone = async () => {
    if (isRecording) {
      stopRecording();
      return;
    }

    await startRecording();
  };

  return (
    <main>
      <h1>JARVIS</h1>

      <p>{response}</p>

      <form onSubmit={handleSubmit}>
        <input
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          placeholder="Ask JARVIS..."
          autoFocus
          disabled={isLoading}
        />

        <button
          type="button"
          onClick={handleMicrophone}
          disabled={isLoading && !isRecording}
        >
          {isRecording ? "Stop" : "🎤"}
        </button>

        <button type="submit" disabled={isLoading || !command.trim()}>
          {isLoading ? "Processing..." : "Send"}
        </button>
      </form>
    </main>
  );
}

export default App;
