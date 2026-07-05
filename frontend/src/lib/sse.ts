// Minimal Server-Sent-Events parser for a fetch() Response stream.
//
// We can't use the browser's native EventSource here because it only
// supports GET requests, and sending the question requires a POST body.
// This walks the raw bytes instead: SSE frames are separated by a blank
// line ("\n\n"), and each frame has "event: <name>" / "data: <payload>"
// lines. Chunks from the network don't line up with frame boundaries, so we
// buffer until we see a full frame before parsing it.
export interface SSEMessage {
  event: string;
  data: string;
}

export async function* parseSSEStream(
  response: Response,
): AsyncGenerator<SSEMessage> {
  if (!response.body) {
    throw new Error("Response has no body to stream");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawFrame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const message = parseFrame(rawFrame);
      if (message) yield message;
      boundary = buffer.indexOf("\n\n");
    }
  }
}

function parseFrame(frame: string): SSEMessage | null {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}
