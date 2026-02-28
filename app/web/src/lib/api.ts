export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Config {
  mode: string;
  model_id: string;
  adapter_path: string;
  adapter_base_dir: string;
  endpoint_id: string;
  project: string;
  location: string;
}

export interface UpdateConfigPayload {
  model_id?: string;
  adapter_path?: string;
  adapter_base_dir?: string;
  endpoint_id?: string;
}

export const fetchConfig = async (): Promise<Config> => {
  const res = await fetch(`${API_BASE_URL}/config`);
  if (!res.ok) throw new Error("Failed to fetch config");
  return res.json();
};

export const updateConfig = async (payload: UpdateConfigPayload): Promise<{ config: Config }> => {
  const res = await fetch(`${API_BASE_URL}/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to update config");
  return res.json();
};

export const submitFeedback = async (inquiry: string, answer: string, isPositive: boolean): Promise<void> => {
  const res = await fetch(`${API_BASE_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      inquiry,
      answer,
      is_positive: isPositive,
    }),
  });
  if (!res.ok) throw new Error("Failed to send feedback");
};

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onDone: () => void;
  onError: (error: any) => void;
}

export const submitConsultation = async (prompt: string, callbacks: StreamCallbacks): Promise<void> => {
  try {
    const response = await fetch(`${API_BASE_URL}/consult`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });

    if (!response.ok) throw new Error("Connection failed.");

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) throw new Error("No readable stream.");

    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const cleanLine = line.endsWith("\r") ? line.slice(0, -1) : line;

        if (cleanLine.startsWith("data: ")) {
          const content = cleanLine.slice(6);
          if (content === "[DONE]") {
            callbacks.onDone();
            return;
          }
          callbacks.onToken(content);
        }
      }
    }
    callbacks.onDone();
  } catch (err) {
    callbacks.onError(err);
  }
};
