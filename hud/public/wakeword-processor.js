class WakeWordProcessor extends AudioWorkletProcessor {
  constructor() {
    super();

    this.buffer = [];
    this.frameSize = 1280;
  }

  process(inputs) {
    const input = inputs[0];

    if (!input || !input[0]) {
      return true;
    }

    const channel = input[0];

    for (let i = 0; i < channel.length; i++) {
      this.buffer.push(channel[i]);
    }

    while (this.buffer.length >= this.frameSize) {
      const frame = this.buffer.splice(
        0,
        this.frameSize,
      );

      const pcm = new Int16Array(
        this.frameSize,
      );

      for (let i = 0; i < frame.length; i++) {
        const sample = Math.max(
          -1,
          Math.min(1, frame[i]),
        );

        pcm[i] =
          sample < 0
            ? sample * 32768
            : sample * 32767;
      }

      this.port.postMessage(
        pcm.buffer,
        [pcm.buffer],
      );
    }

    return true;
  }
}

registerProcessor(
  "wakeword-processor",
  WakeWordProcessor,
);