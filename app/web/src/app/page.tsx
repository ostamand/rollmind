"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import ReactMarkdown from "react-markdown";
import { Trash2, Settings, ArrowUp, X, Send } from "lucide-react";
import styles from "./page.module.css";

interface Entry {
  id: string;
  question: string;
  answer: string;
  isStreaming: boolean;
}

const ORACLE_MESSAGES = [
  "Consulting the archival scrolls",
  "Whispering to the weave",
  "Scrying the ancient texts",
  "Channeling knowledge from the Outer Planes",
  "Deciphering the celestial runes",
  "Meditating on the rule of law",
  "Invoking the spirits of the library",
];

export default function OraclePage() {
  const [inquiry, setInquiry] = useState("");
  const [history, setHistory] = useState<Entry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [showBackToTop, setShowBackToTop] = useState(false);
  const [processingMessage, setProcessingMessage] = useState(ORACLE_MESSAGES[0]);
  const [config, setConfig] = useState({ model_id: "", adapter_path: "" });
  const [newConfig, setNewConfig] = useState({
    model_id: "",
    adapter_path: "",
  });
  const scrollRef = useRef<HTMLDivElement>(null);

  // Rotate processing messages when loading
  useEffect(() => {
    if (!isLoading) return;
    const interval = setInterval(() => {
      setProcessingMessage(prev => {
        const currentIndex = ORACLE_MESSAGES.indexOf(prev);
        const nextIndex = (currentIndex + 1) % ORACLE_MESSAGES.length;
        return ORACLE_MESSAGES[nextIndex];
      });
    }, 2000 + Math.random() * 1000);
    return () => clearInterval(interval);
  }, [isLoading]);

  // Monitor scroll for Back to Top visibility
  useEffect(() => {
    const handleScroll = () => {
      setShowBackToTop(window.scrollY > 300);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Fetch initial config
  useEffect(() => {
    fetch("http://localhost:8000/config")
      .then((res) => res.json())
      .then((data) => {
        setConfig(data);
        // Strip prefix if it exists to make it easier for the user
        const cleanPath = data.adapter_path?.replace("../../out/step2/", "") ||
          "";
        setNewConfig({ ...data, adapter_path: cleanPath });
      })
      .catch((err) => console.error("Failed to fetch config", err));
  }, []);

  // Auto-scroll to latest card
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [history]);

  // Refresh config when modal opens
  useEffect(() => {
    if (isConfigOpen) {
      fetch("http://localhost:8000/config")
        .then((res) => res.json())
        .then((data) => {
          setConfig(data);
          const cleanPath =
            data.adapter_path?.replace("../../out/step2/", "") || "";
          setNewConfig({ ...data, adapter_path: cleanPath });
        })
        .catch((err) => console.error("Failed to fetch config", err));
    }
  }, [isConfigOpen]);

  const handleUpdateConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    // Prepend the out/step2 path if a name is provided
    const finalPath = newConfig.adapter_path.trim()
      ? `../../out/step2/${newConfig.adapter_path.trim()}`
      : "";

    try {
      const response = await fetch("http://localhost:8000/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...newConfig, adapter_path: finalPath }),
      });
      if (response.ok) {
        const data = await response.json();
        setConfig(data.config);
        setIsConfigOpen(false);
      }
    } catch (err) {
      console.error("Failed to update config", err);
    }
  };

  const deleteEntry = (id: string) => {
    setHistory((prev) => prev.filter((entry) => entry.id !== id));
  };

  const clearHistory = () => {
    if (window.confirm("Are you sure you want to clear this session?")) {
      setHistory([]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inquiry.trim() || isLoading) return;

    const currentInquiry = inquiry;
    const entryId = Math.random().toString(36).substring(7);

    setInquiry("");
    setIsLoading(true);

    // Add initial entry
    setHistory((prev) => [...prev, {
      id: entryId,
      question: currentInquiry,
      answer: "",
      isStreaming: true,
    }]);

    try {
      const response = await fetch("http://localhost:8000/consult", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: currentInquiry }),
      });

      if (!response.ok) throw new Error("Oracle connection failed.");

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No readable stream.");

      let accumulatedAnswer = "";
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE can use \r\n, \r, or \n as line endings.
        // We split by \n and handle potential \r separately.
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Save partial line for next chunk

        for (const line of lines) {
          // Remove potential \r from the end of the line
          const cleanLine = line.endsWith("\r") ? line.slice(0, -1) : line;

          if (cleanLine.startsWith("data: ")) {
            const content = cleanLine.slice(6);
            if (content === "[DONE]") break;

            accumulatedAnswer += content;

            setHistory((prev) =>
              prev.map((entry) =>
                entry.id === entryId
                  ? { ...entry, answer: accumulatedAnswer }
                  : entry
              )
            );
          }
        }
      }

      // Finalize entry
      setHistory((prev) =>
        prev.map((entry) =>
          entry.id === entryId ? { ...entry, isStreaming: false } : entry
        )
      );
    } catch (err) {
      console.error(err);
      setHistory((prev) =>
        prev.map((entry) =>
          entry.id === entryId
            ? {
              ...entry,
              answer: "Error: The Oracle is currently unreachable.",
              isStreaming: false,
            }
            : entry
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <div className={styles.headerTop}>
          <Image
            src="/RollMind-logo-only.webp"
            alt="RollMind Logo"
            width={100}
            height={100}
            className={styles.logo}
            priority
          />
          <div className={styles.headerActions}>
            <button
              className={styles.actionButton}
              onClick={clearHistory}
              title="Clear Session"
              disabled={history.length === 0}
            >
              <Trash2 size={24} color="var(--accent)" />
            </button>
            <button
              className={styles.actionButton}
              onClick={() => setIsConfigOpen(true)}
              title="Configure Model"
            >
              <Settings size={24} color="var(--accent)" />
            </button>
          </div>
        </div>
        <h1 className={styles.title}>RollMind</h1>
        <p className={styles.subtitle}>
          D&D 2024 • {config.adapter_path ? "Fine-tuned" : "Base"}
        </p>
      </header>

      {isConfigOpen && (
        <div
          className={styles.modalOverlay}
          onClick={() => setIsConfigOpen(false)}
        >
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2 className={styles.modalTitle}>Oracle Configuration</h2>
              <button onClick={() => setIsConfigOpen(false)} className={styles.closeModalButton}>
                <X size={24} color="var(--accent)" />
              </button>
            </div>
            <form onSubmit={handleUpdateConfig} className={styles.configForm}>
              <div className={styles.formGroup}>
                <label>Base Model ID</label>
                <input
                  type="text"
                  value={newConfig.model_id}
                  onChange={(e) =>
                    setNewConfig({ ...newConfig, model_id: e.target.value })}
                  placeholder="google/gemma-7b-it"
                />
              </div>
              <div className={styles.formGroup}>
                <label>Adapter (LoRA)</label>
                <div className={styles.pathInputWrapper}>
                  <span className={styles.pathPrefix}>../../out/step2/</span>
                  <input
                    type="text"
                    value={newConfig.adapter_path}
                    onChange={(e) =>
                      setNewConfig({
                        ...newConfig,
                        adapter_path: e.target.value,
                      })}
                    placeholder="leave empty for base model"
                    className={styles.pathInput}
                  />
                </div>
                <small>
                  Relative to Step 2 outputs. Empty = Base Model only.
                </small>
              </div>
              <div className={styles.modalActions}>
                <button
                  type="button"
                  onClick={() => setIsConfigOpen(false)}
                  className={styles.cancelButton}
                >
                  Cancel
                </button>
                <button type="submit" className={styles.saveButton}>
                  Update Oracle
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className={styles.inquiryZone}>
        <form onSubmit={handleSubmit} className={styles.textAreaWrapper}>
          <textarea
            className={styles.input}
            placeholder="Describe your inquiry (e.g., 'Explain the rules for Grappling')..."
            value={inquiry}
            onChange={(e) => setInquiry(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <button
            type="submit"
            className={styles.sendButton}
            disabled={isLoading || !inquiry.trim()}
          >
            <Image
              src="/RollMind-send.png"
              alt="Consult"
              width={24}
              height={24}
            />
          </button>
        </form>
      </div>

      <div className={styles.history}>
        <div ref={scrollRef} />
        {history.slice().reverse().map((entry) => (
          <section key={entry.id} className={styles.card}>
            <div className={styles.cardHeader}>
              <h2 className={styles.cardQuestion}>Inquiry: {entry.question}</h2>
              <button
                onClick={() =>
                  deleteEntry(entry.id)}
                className={styles.deleteButton}
                title="Delete from session"
              >
                ×
              </button>
            </div>
            <div className={styles.cardAnswer}>
              {entry.answer ? (
                <ReactMarkdown>{entry.answer}</ReactMarkdown>
              ) : (
                <div className={styles.loadingText}>
                  {processingMessage}
                  <span className={styles.loadingDot}>.</span>
                  <span className={styles.loadingDot}>.</span>
                  <span className={styles.loadingDot}>.</span>
                </div>
              )}
            </div>
          </section>
        ))}
      </div>
      <button
        className={`${styles.backToTop} ${showBackToTop ? styles.visible : ""}`}
        onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
        title="Back to inquiry"
      >
        ↑
      </button>
    </main>
  );
}
