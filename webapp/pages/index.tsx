// webapp/pages/index.tsx
import { useEffect, useRef, useState, useCallback } from "react";
import MicButton, { MicButtonHandle } from "../components/MicButton";
import AvatarBox from "../components/AvatarBox";
import SettingsBar from "../components/SettingsBar";
import AudioPlayer, { AudioPlayerHandle } from "../components/AudioPlayer";
import {
  apiChat,
  apiInterrupt,
  apiSaveDefaults,
  apiGetModels,
  apiGetVoices,
  apiGetSettings,
  API_BASE,
  ChatMessage,
  ModelInfo,
} from "../lib/api";

const LANG_OPTIONS = ["auto", "en", "es", "fr", "de", "it", "pt", "ja", "zh"];
type ModelOption = { value: string; label: string; meta?: { gguf?: string } };

export default function Home() {
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [log, setLog] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [assistantSpeaking, setAssistantSpeaking] = useState(false);

  // settings
  const [model, setModel] = useState<string>("");
  const [voice, setVoice] = useState<string>("");
  const [sttLanguage, setSttLanguage] = useState<string>("auto");
  const [saving, setSaving] = useState(false);

  // dynamic options
  const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);
  const [voiceOptions, setVoiceOptions] = useState<string[]>([]);

  // last assistant text to speak
  const [speakText, setSpeakText] = useState<string | null>(null);

  const micRef = useRef<MicButtonHandle>(null);
  const chatBoxRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<AudioPlayerHandle>(null);

  // fetch lists + server defaults, then merge with localStorage
  useEffect(() => {
    (async () => {
      const [models, voices, server] = await Promise.all([
        apiGetModels(),
        apiGetVoices(),
        apiGetSettings(),
      ]);

      const mopts: ModelOption[] = (models as ModelInfo[]).map((m) => ({
        value: m.key,
        label: m.name || m.key,
        meta: { gguf: m.gguf },
      }));
      setModelOptions(mopts);
      setVoiceOptions(voices);

      const localModel = localStorage.getItem("arc.model") || "";
      const localVoice = localStorage.getItem("arc.voice") || "";
      const localLang = localStorage.getItem("arc.sttLang") || "";

      const serverModel = server?.model || "";
      const chosenModel =
        (serverModel && mopts.some((o) => o.value === serverModel) && serverModel) ||
        (localModel && mopts.some((o) => o.value === localModel) && localModel) ||
        (mopts[0]?.value || "");

      const chosenVoice =
        (server?.voice && voices.includes(server.voice) && server.voice) ||
        (localVoice && voices.includes(localVoice) && localVoice) ||
        (voices[0] || "");

      const chosenLang = server?.sttLanguage || localLang || "auto";

      setModel(chosenModel);
      setVoice(chosenVoice);
      setSttLanguage(chosenLang);
    })();
  }, []);

  // persist local
  useEffect(() => { if (model) localStorage.setItem("arc.model", model); }, [model]);
  useEffect(() => { if (voice) localStorage.setItem("arc.voice", voice); }, [voice]);
  useEffect(() => { if (sttLanguage) localStorage.setItem("arc.sttLang", sttLanguage); }, [sttLanguage]);

  // autoscroll
  useEffect(() => {
    chatBoxRef.current?.scrollTo({ top: chatBoxRef.current.scrollHeight, behavior: "smooth" });
  }, [log]);

  // Space bar push-to-talk
  useEffect(() => {
    const isTyping = () => {
      const el = document.activeElement as HTMLElement | null;
      if (!el) return false;
      const tag = (el.tagName || "").toLowerCase();
      return tag === "input" || tag === "textarea" || (el as any).isContentEditable;
    };
    let down = false;
    const onKeyDown = async (e: KeyboardEvent) => {
      if (e.code === "Space" && !e.repeat && !isTyping()) {
        e.preventDefault(); down = true; await micRef.current?.start();
      }
    };
    const onKeyUp = async (e: KeyboardEvent) => {
      if (e.code === "Space" && down) { e.preventDefault(); down = false; await micRef.current?.stop(); }
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => { window.removeEventListener("keydown", onKeyDown); window.removeEventListener("keyup", onKeyUp); };
  }, []);

  async function sendMessage(text?: string) {
    const content = (text ?? input).trim();
    if (!content) return;

    setLog((prev) => [...prev, "🧑: " + content]);
    setChat((prev) => [...prev, { role: "user", content }]);
    setInput("");

    setBusy(true);
    setStatus(`Thinking… (${model || "default"})`);
    setSpeakText(null);           // clear previous utterance while the model thinks
    try {
      const reply = await apiChat([...chat, { role: "user", content }], {
        model: model,
        voice: voice,
      });
      setLog((prev) => [...prev, "🤖: " + reply]);
      setChat((prev) => [...prev, { role: "assistant", content: reply }]);
      setSpeakText(reply);        // trigger TTS playback exactly once per reply
    } catch (err: any) {
      setLog((prev) => [...prev, "⚠️ " + String(err?.message || err)]);
      setSpeakText(null);
    } finally {
      setBusy(false);
      setStatus("");
      // speaking state will be driven by AudioPlayer start/end
    }
  }

  function handleTranscript(t: string) {
    const tx = (t || "").trim();
    if (!tx) { setLog((p) => [...p, "⚠️ (empty transcript)"]); return; }
    setLog((p) => [...p, "🧑 (stt): " + tx]);
    void sendMessage(tx);
  }

  function handleMicError(msg: string) { setLog((prev) => [...prev, "⚠️ " + msg]); }

  const handleSpeakStart = useCallback(() => setAssistantSpeaking(true), []);
  const handleSpeakEnd   = useCallback(() => setAssistantSpeaking(false), []);

  async function onInterrupt() {
    try {
      setStatus("Interrupting…");
      // stop local audio immediately
      playerRef.current?.stop();
      await apiInterrupt();
      setLog((p) => [...p, "⏹️ Interrupted"]);
    } catch {
      setLog((p) => [...p, "⚠️ interrupt failed"]);
    } finally {
      setAssistantSpeaking(false);
      setBusy(false);
      setStatus("");
    }
  }

  async function onSaveDefault() {
    setSaving(true);
    const ok = await apiSaveDefaults({ model, voice, sttLanguage });
    setSaving(false);
    setLog((p) => [
      ...p,
      ok ? "💾 Defaults saved on server." : "💾 Saved locally. (Server /settings not found or declined)",
    ]);
  }

  return (
    <main
      style={{
        padding: "2rem",
        fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
        maxWidth: 860,
        margin: "0 auto",
      }}
    >
      <h1 style={{ marginBottom: 4 }}>ARC Web Bridge ✅</h1>
      <div style={{ color: "#6b7280", fontSize: 14, marginBottom: 12 }}>
        Backend: <code>{API_BASE}</code> {status ? `• ${status}` : ""}
      </div>

      <SettingsBar
        model={model}
        setModel={setModel}
        modelOptions={modelOptions}
        voice={voice}
        setVoice={setVoice}
        voiceOptions={voiceOptions}
        sttLanguage={sttLanguage}
        setSttLanguage={setSttLanguage}
        langOptions={LANG_OPTIONS}
        onSaveDefault={onSaveDefault}
        saving={saving}
      />

      <AvatarBox speaking={assistantSpeaking} />

      <div
        ref={chatBoxRef}
        style={{
          border: "1px solid #e5e7eb",
          borderRadius: 12,
          padding: "1rem",
          minHeight: 180,
          maxHeight: "48vh",
          overflowY: "auto",
          background: "#ffffff",
        }}
      >
        {log.length === 0 ? (
          <p style={{ color: "#9ca3af" }}>
            Say something with the mic (hold the button or press/hold Space) or type below.
          </p>
        ) : (
          log.map((m, i) => (
            <p key={i} style={{ margin: "0.4rem 0", whiteSpace: "pre-wrap" }}>
              {m}
            </p>
          ))
        )}
      </div>

      <div
        style={{
          display: "flex",
          gap: 8,
          marginTop: 12,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <input
          style={{ padding: "0.6rem", flex: "1 1 420px", borderRadius: 10, border: "1px solid #d1d5db" }}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          onKeyDown={(e) => (e.key === "Enter" ? sendMessage() : undefined)}
          disabled={busy}
        />
        <button
          style={{ padding: "0.6rem 0.9rem", borderRadius: 12, border: "1px solid #888", background: "#111827", color: "white" }}
          onClick={() => sendMessage()}
          disabled={busy || !input.trim()}
        >
          Send
        </button>

        <MicButton
          ref={micRef}
          onTranscript={handleTranscript}
          onError={handleMicError}
          disabled={busy}
          sttLanguage={sttLanguage === "auto" ? undefined : sttLanguage}
        />

        <button
          style={{ padding: "0.6rem 0.9rem", borderRadius: 12, border: "1px solid #bbb", background: "white" }}
          onClick={onInterrupt}
        >
          ⏹️ Interrupt
        </button>
      </div>

      <div style={{ marginTop: 8, color: "#6b7280", fontSize: 13 }}>
        Pro tip: Hold <kbd>Space</kbd> to talk anywhere on the page (except while typing).
      </div>

      {/* TTS player lives here; it has no visual UI */}
      <AudioPlayer
        ref={playerRef}
        text={speakText}
        voice={voice}
        onStart={handleSpeakStart}
        onEnd={handleSpeakEnd}
      />
    </main>
  );
}

