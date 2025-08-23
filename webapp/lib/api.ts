// webapp/lib/api.ts

// ---------- API base (single definition, trailing slashes trimmed) ----------
export const API_BASE =
  (process.env.NEXT_PUBLIC_API_BASE?.replace(/\/+$/, "") ||
    "http://localhost:8000");

// ---------- Shared types ----------
export type ChatRole = "user" | "assistant" | "system";
export interface ChatMessage { role: ChatRole; content: string; }

export type ModelInfo = { key: string; name: string; gguf?: string; exists?: boolean };

export interface ServerSettings {
  model?: string;
  voice?: string;
  sttLanguage?: string;
  // backend may also send these:
  input_mode?: string;
  ark_module?: string | null;
}

export interface STTOptions {
  language?: string;     // "en", "es", etc.
  prompt?: string;
  signal?: AbortSignal;
}

export interface ChatOptions {
  signal?: AbortSignal;
  model?: string;        // sent via header
  voice?: string;        // sent via header
}

// ---------- Helpers ----------
async function richError(res: Response): Promise<Error> {
  let more = "";
  try { more = await res.text(); } catch {}
  const hint = more?.slice(0, 500).trim();
  return new Error(`HTTP ${res.status} ${res.statusText} for ${res.url}${hint ? ` — ${hint}` : ""}`);
}

// ---------- STT ----------
/** Speech-to-Text — robust to different field names on the server */
export async function apiSTT(
  audio: Blob | File,
  opts: STTOptions = {}
): Promise<{ text: string; [k: string]: unknown }> {
  const file = audio instanceof File ? audio : new File([audio], "audio.webm", { type: audio.type || "audio/webm" });
  const fd = new FormData();
  // send under several names so any backend handler matches it
  fd.append("file", file, file.name);
  fd.append("audio", file, file.name);
  fd.append("audio_file", file, file.name);
  if (opts.language) fd.append("language", opts.language);
  if (opts.prompt) fd.append("prompt", opts.prompt);

  const res = await fetch(`${API_BASE}/stt`, { method: "POST", body: fd, signal: opts.signal });
  if (!res.ok) throw await richError(res);

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    const data = await res.json().catch(() => ({}));
    const text = (data?.text ?? data?.transcript ?? data?.result ?? "") as string;
    return { text, ...data };
  }
  const text = await res.text();
  return { text };
}

// ---------- Chat ----------
/** Chat — backend expects { text }, optional history; model/voice via headers */
export async function apiChat(
  msgOrHistory: ChatMessage[] | string,
  opts: ChatOptions = {}
): Promise<string> {
  let text = "";
  let history: ChatMessage[] | undefined;

  if (typeof msgOrHistory === "string") {
    text = msgOrHistory;
  } else {
    history = msgOrHistory;
    const lastUser = [...msgOrHistory].reverse().find(m => m.role === "user");
    text = lastUser?.content ?? "";
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (opts.model) headers["X-Model"] = opts.model;
  if (opts.voice) headers["X-Voice"] = opts.voice;

  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify({ text, history }),
    signal: opts.signal,
  });
  if (!res.ok) throw await richError(res);

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    const data = await res.json();
    return (data?.reply as string)
        ?? (data?.text as string)
        ?? (data?.response as string)
        ?? JSON.stringify(data);
  }
  return await res.text();
}

// ---------- Interrupt / Health ----------
export async function apiInterrupt(signal?: AbortSignal): Promise<void> {
  const res = await fetch(`${API_BASE}/interrupt`, { method: "POST", signal });
  // Treat 404 as a no-op (some backends may not implement /interrupt)
  if (res.status === 404) return;
  if (!res.ok) throw await richError(res);
}

export async function apiHealth(): Promise<boolean> {
  try {
    const r = await fetch(`${API_BASE}/health`, { method: "GET" });
    return r.ok;
  } catch {
    return false;
  }
}

// ---------- Lists from FastAPI ----------
/** Load LLMs from /models */
export async function apiGetModels(): Promise<ModelInfo[]> {
  const res = await fetch(`${API_BASE}/models`, { method: "GET" });
  if (!res.ok) return [];
  const data = await res.json().catch(() => ({}));
  const arr = Array.isArray(data) ? data : data?.models;
  if (!Array.isArray(arr)) return [];
  return arr.map((m: any) => ({
    key: String(m?.key ?? ""),
    name: String(m?.name ?? m?.key ?? ""),
    gguf: m?.gguf ? String(m.gguf) : undefined,
    exists: Boolean(m?.exists ?? true),
  }));
}

/** Load voices from /voices */
export async function apiGetVoices(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/voices`, { method: "GET" });
  if (!res.ok) return [];
  const data = await res.json().catch(() => ({}));
  const arr = Array.isArray(data) ? data : data?.voices;
  return Array.isArray(arr) ? arr.map(String) : [];
}

// ---------- Settings on FastAPI ----------
/** Get current server defaults */
export async function apiGetSettings(): Promise<ServerSettings | null> {
  try {
    const res = await fetch(`${API_BASE}/settings`, { method: "GET" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/** Save defaults on the server (safe if the route is missing) */
export async function apiSaveDefaults(payload: {
  model?: string;
  voice?: string;
  sttLanguage?: string;
}): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.status === 404) return false; // backend didn’t implement it
    if (!res.ok) throw await richError(res);
    return true;
  } catch {
    return false;
  }
}

// ---------- TTS ----------
/** Fetch TTS audio from the backend and return an object URL for immediate playback. */
export async function apiTTS(
  text: string,
  opts?: { voice?: string; format?: "mp3" | "wav"; signal?: AbortSignal }
): Promise<string> {
  const res = await fetch(`${API_BASE}/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice: opts?.voice, format: opts?.format || "mp3" }),
    signal: opts?.signal,
  });
  if (!res.ok) throw await richError(res);
  const blob = await res.blob(); // audio/*
  return URL.createObjectURL(blob);
}

