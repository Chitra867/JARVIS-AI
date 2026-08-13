import { useState, type FormEvent } from "react";
import { sendCommand } from "./services/jarvisApi";
import "./App.css";

function App() {
  const [command, setCommand] = useState("");
  const [response, setResponse] = useState("JARVIS ready.");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
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
        />

        <button type="submit" disabled={isLoading}>
          {isLoading ? "Processing..." : "Send"}
        </button>
      </form>
    </main>
  );
}

export default App;