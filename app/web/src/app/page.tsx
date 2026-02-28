"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import Image from "next/image";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowUp, Copy, Send, Settings, Trash2, X, ThumbsUp, ThumbsDown } from "lucide-react";
import styles from "./page.module.css";
import DiceRoller from "./components/DiceRoller";

interface Entry {
  id: string;
  question: string;
  answer: string;
  isStreaming: boolean;
  feedback?: "positive" | "negative";
}

const PROCESSING_MESSAGES = [
  "Consulting the archival scrolls",
  "Whispering to the weave",
  "Scrying the ancient texts",
  "Channeling knowledge from the Outer Planes",
  "Deciphering the celestial runes",
  "Meditating on the rule of law",
  "Invoking the spirits of the library",
];

export default function RollMindPage() {
  const [inquiry, setInquiry] = useState("");
  const [history, setHistory] = useState<Entry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [showBackToTop, setShowBackToTop] = useState(false);
  const [processingMessage, setProcessingMessage] = useState(
    PROCESSING_MESSAGES[0],
  );
  const [config, setConfig] = useState({
    mode: "local",
    model_id: "",
    adapter_path: "",
    adapter_base_dir: "",
    endpoint_id: "",
    project: "",
    location: "",
  });
  const [newConfig, setNewConfig] = useState({
    model_id: "",
    adapter_path: "",
    adapter_base_dir: "",
    endpoint_id: "",
  });
  const scrollRef = useRef<HTMLDivElement>(null);

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
        setNewConfig(data);
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
          setNewConfig(data);
        })
        .catch((err) => console.error("Failed to fetch config", err));
    }
  }, [isConfigOpen]);

  // Stable components for ReactMarkdown to prevent unmounting when typing
  const markdownComponents = useMemo(() => ({
    code({ node, className, children, ...props }: any) {
      const matchComplete = /language-dice-roll-complete/.exec(className || '');
      const matchStreaming = /language-dice-roll-streaming/.exec(className || '');
      
      if (matchComplete || matchStreaming) {
        return (
          <DiceRoller 
            formula={String(children).trim()} 
            isComplete={!!matchComplete} 
          />
        );
      }
      
      return (
        <code className={className} {...props}>
          {children}
        </code>
      );
    }
  }), []);

  const handleUpdateConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    let finalPayload = { ...newConfig };

    if (config.mode === "local") {
      finalPayload.adapter_path = newConfig.adapter_path.trim();
    }

    try {
      const response = await fetch("http://localhost:8000/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(finalPayload),
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

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      alert("Raw output copied to clipboard!");
    }).catch(err => {
      console.error('Failed to copy: ', err);
    });
  };

  const handleFeedback = async (id: string, isPositive: boolean) => {
    const entry = history.find(e => e.id === id);
    if (!entry) return;

    try {
      const response = await fetch("http://localhost:8000/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          inquiry: entry.question,
          answer: entry.answer,
          is_positive: isPositive
        }),
      });

      if (response.ok) {
        setHistory(prev => prev.map(e => 
          e.id === id ? { ...e, feedback: isPositive ? "positive" : "negative" } : e
        ));
      }
    } catch (err) {
      console.error("Failed to send feedback", err);
    }
  };

  const clearHistory = () => {
    if (window.confirm("Are you sure you want to clear this session?")) {
      setHistory([]);
    }
  };

  const preprocessMarkdown = (text: string) => {
    // 0. Handle [ROLL] formula [/ROLL] or [ROLL] formula
    // We convert it to a custom code block that ReactMarkdown components can handle.
    // If it's missing the closing tag (still streaming), we mark it as incomplete.
    let processed = text.replace(/\[ROLL\](.*?)\[\/ROLL\]/gs, (_, formula) => {
      return `\n\`\`\`dice-roll-complete\n${formula.trim()}\n\`\`\`\n`;
    });
    
    // Handle partial streaming [ROLL]
    processed = processed.replace(/\[ROLL\](?!.*\`\`\`dice-roll)(.*)$/gs, (_, formula) => {
      return `\n\`\`\`dice-roll-streaming\n${formula.trim()}\n\`\`\`\n`;
    });

    // 1. Handle double pipes as row/section breaks.
    processed = processed.replace(/\|\|/g, "\n");

    // 2. Force newline before a table starts if it's attached to text
    // Matches "Text:| Col 1 |" and turns it into "Text:\n| Col 1 |"
    processed = processed.replace(/([^\n|])\s*(\|[^|\n]+\|[^|\n]+\|)/g, "$1\n$2");

    // 3. Fix run-on lists where the model forgets newlines before bolded items or list markers
    processed = processed.replace(/([^\n])\s*-\s+\*\*/g, "$1\n- **");
    processed = processed.replace(/([^\n])\s+\*\*([^*]+)\*\*:/g, "$1\n- **$2**:");

    // 4. Identify "faux tables" vs real tables
    const lines = processed.split("\n");
    const result: string[] = [];

    for (let i = 0; i < lines.length; i++) {
      let line = lines[i].trim();
      if (!line) continue;

      const pipeCount = (line.match(/\|/g) || []).length;

      if (pipeCount >= 3) {
        const nextLine = lines[i + 1]?.trim() || "";
        const prevLine = result[result.length - 1]?.trim() || "";
        const isTableSeparator = nextLine.includes("---") || prevLine.includes("---") || line.includes("---");
        
        // If it's not a table and has many pipes, convert to a list
        if (!isTableSeparator && !line.startsWith("| ---")) {
          const parts = line.split("|").map(p => p.trim()).filter(p => p.length > 0);
          if (parts.length > 2) {
            parts.forEach(part => result.push("- " + part));
            continue;
          }
        }
      }

      // Standard table row cleanup
      if (pipeCount >= 1) {
        // Ensure row has start/end pipes if it looks like a table row
        if (!line.startsWith("|")) line = "| " + line;
        if (!line.endsWith("|")) line = line + " |";

        const nextLineExists = i < lines.length - 1;
        const nextLine = lines[i + 1]?.trim() || "";
        const nextLineIsSeparator = nextLine.includes("---");
        const prevLine = result[result.length - 1]?.trim() || "";
        const prevLineHasPipes = prevLine.startsWith("|") && prevLine.endsWith("|");

        // Inject separator if this is a header and next line isn't a separator
        if (!prevLineHasPipes && nextLineExists && !nextLineIsSeparator && !line.includes("---")) {
          result.push(line);
          const cols = (line.match(/\|/g) || []).length - 1;
          result.push("|" + Array(cols).fill(" --- |").join(""));
          continue;
        }
      }
      
      result.push(line);
    }
    
    return result.join("\n");
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

      if (!response.ok) throw new Error("Connection failed.");

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
              answer: "Error: The system is currently unreachable.",
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
            {process.env.NEXT_PUBLIC_HIDE_CONFIG !== "true" && (
              <button
                className={styles.actionButton}
                onClick={() => setIsConfigOpen(true)}
                title="Configure Model"
              >
                <Settings size={24} color="var(--accent)" />
              </button>
            )}
          </div>
        </div>
        <h1 className={styles.title}>RollMind</h1>
        <p className={styles.subtitle}>
          D&D 2024
        </p>
      </header>

      {isConfigOpen && (
        <div
          className={styles.modalOverlay}
          onClick={() => setIsConfigOpen(false)}
        >
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2 className={styles.modalTitle}>Configuration</h2>
              <button
                onClick={() => setIsConfigOpen(false)}
                className={styles.closeModalButton}
              >
                <X size={24} color="var(--accent)" />
              </button>
            </div>
            <form onSubmit={handleUpdateConfig} className={styles.configForm}>
              <div className={styles.formGroup}>
                <label>Inference Mode</label>
                <div className={styles.modeBadge}>
                  {config.mode.toUpperCase()}
                </div>
                <small>
                  To change mode, update INFERENCE_MODE in .env and restart.
                </small>
              </div>

              {config.mode === "local"
                ? (
                  <>
                    <div className={styles.formGroup}>
                      <label>Base Model ID</label>
                      <input
                        type="text"
                        value={newConfig.model_id}
                        onChange={(e) =>
                          setNewConfig({
                            ...newConfig,
                            model_id: e.target.value,
                          })}
                        placeholder="google/gemma-7b-it"
                      />
                    </div>
                    <div className={styles.formGroup}>
                      <label>Adapter (LoRA)</label>
                      <input
                        type="text"
                        value={newConfig.adapter_path}
                        onChange={(e) =>
                          setNewConfig({
                            ...newConfig,
                            adapter_path: e.target.value,
                          })}
                        placeholder="leave empty for base model"
                      />
                    </div>
                  </>
                )
                : (
                  <div className={styles.formGroup}>
                    <label>Vertex Endpoint ID</label>
                    <input
                      type="text"
                      value={newConfig.endpoint_id}
                      onChange={(e) =>
                        setNewConfig({
                          ...newConfig,
                          endpoint_id: e.target.value,
                        })}
                      placeholder="Enter alphanumeric endpoint ID"
                    />
                    <small>
                      Project: {config.project} | Location: {config.location}
                    </small>
                  </div>
                )}

              <div className={styles.modalActions}>
                <button
                  type="button"
                  onClick={() => setIsConfigOpen(false)}
                  className={styles.cancelButton}
                >
                  Cancel
                </button>
                <button type="submit" className={styles.saveButton}>
                  Update
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
              <div style={{ display: "flex", gap: "0.5rem" }}>
                {process.env.NEXT_PUBLIC_HIDE_CONFIG !== "true" && entry.answer && (
                  <button
                    onClick={() => copyToClipboard(entry.answer)}
                    className={styles.copyButton}
                    title="Copy Raw Output"
                  >
                    <Copy size={18} />
                  </button>
                )}
                <button
                  onClick={() =>
                    deleteEntry(entry.id)}
                  className={styles.deleteButton}
                  title="Delete from session"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
            <div className={styles.cardAnswer}>
              {entry.answer
                ? (
                  <>
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={markdownComponents}
                    >
                      {preprocessMarkdown(entry.answer)}
                    </ReactMarkdown>
                    {!entry.isStreaming && (
                      <div className={styles.cardFooter}>
                        {!entry.feedback ? (
                          <div className={styles.feedbackGroup}>
                            <button 
                              className={styles.feedbackButton} 
                              onClick={() => handleFeedback(entry.id, true)}
                              title="Helpful"
                            >
                              <ThumbsUp size={14} />
                            </button>
                            <button 
                              className={styles.feedbackButton} 
                              onClick={() => handleFeedback(entry.id, false)}
                              title="Not helpful"
                            >
                              <ThumbsDown size={14} />
                            </button>
                          </div>
                        ) : (
                          <div className={styles.feedbackThanks}>
                            {entry.feedback === "positive" ? "Helpful" : "Not helpful"} feedback received. Thank you!
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )
                : (
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
        <ArrowUp size={24} />
      </button>
    </main>
  );
}
