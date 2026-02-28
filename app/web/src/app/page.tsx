"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AlertCircle,
  ArrowUp,
  Copy,
  Send,
  Settings,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  UserCircle,
  X,
} from "lucide-react";
import styles from "./page.module.css";
import DiceRoller from "./components/DiceRoller";
import {
  CharacterProfile,
  Config,
  fetchConfig,
  submitConsultation,
  submitFeedback,
  updateConfig,
} from "../lib/api";

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

const CLASS_ABILITIES: Record<string, string> = {
  Wizard: "INT",
  Cleric: "WIS",
  Druid: "WIS",
  Ranger: "WIS",
  Monk: "WIS",
  Bard: "CHA",
  Paladin: "CHA",
  Sorcerer: "CHA",
  Warlock: "CHA",
  Fighter: "INT", // Eldritch Knight
  Rogue: "INT", // Arcane Trickster
  Barbarian: "CHA",
};

const DEFAULT_PROFILE: CharacterProfile = {
  charClass: "Wizard",
  level: 1,
  stats: { STR: 10, DEX: 10, CON: 10, INT: 10, WIS: 10, CHA: 10 },
  spellcasting: { ability: "INT", dc: 10, attackBonus: 2 },
};

const CLASSES = [
  "Barbarian",
  "Bard",
  "Cleric",
  "Druid",
  "Fighter",
  "Monk",
  "Paladin",
  "Ranger",
  "Rogue",
  "Sorcerer",
  "Warlock",
  "Wizard",
];
const STATS = ["STR", "DEX", "CON", "INT", "WIS", "CHA"] as const;

export default function RollMindPage() {
  const [inquiry, setInquiry] = useState("");
  const [history, setHistory] = useState<Entry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [showBackToTop, setShowBackToTop] = useState(false);
  const [processingMessage, setProcessingMessage] = useState(
    PROCESSING_MESSAGES[0],
  );
  const [config, setConfig] = useState<Config>({
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
  const [profile, setProfile] = useState<CharacterProfile>(DEFAULT_PROFILE);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load profile from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("rollmind_profile");
    if (saved) {
      try {
        setProfile(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse saved profile", e);
      }
    }
  }, []);

  // Save profile to localStorage
  useEffect(() => {
    localStorage.setItem("rollmind_profile", JSON.stringify(profile));
  }, [profile]);

  // Sync spellcasting when class, level, or stats change
  const syncSpellcasting = (updatedProfile: CharacterProfile) => {
    const ability = CLASS_ABILITIES[updatedProfile.charClass] || "INT";
    const score =
      updatedProfile.stats[ability as keyof typeof updatedProfile.stats] || 10;
    const mod = Math.floor((score - 10) / 2);
    const prof = Math.floor((updatedProfile.level - 1) / 4) + 2;

    return {
      ...updatedProfile,
      spellcasting: {
        ability,
        dc: 8 + prof + mod,
        attackBonus: prof + mod,
      },
    };
  };

  const handleProfileChange = (
    changes: Partial<CharacterProfile> | { stats: any },
  ) => {
    setProfile((prev) => {
      const next = { ...prev, ...changes };
      return syncSpellcasting(next);
    });
  };

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
    fetchConfig()
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
      fetchConfig()
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
      const matchComplete = /language-dice-roll-complete/.exec(className || "");
      const matchStreaming = /language-dice-roll-streaming/.exec(
        className || "",
      );
      const matchSystem = /language-system-message/.exec(className || "");

      if (matchSystem) {
        return (
          <div className={styles.systemMessage}>
            <AlertCircle
              size={18}
              color="#ffaa00"
              style={{ marginTop: "2px" }}
            />
            <span className={styles.systemContent}>
              {String(children).trim()}
            </span>
          </div>
        );
      }

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
    },
  }), []);

  const handleUpdateConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    let finalPayload = { ...newConfig };

    if (config.mode === "local") {
      finalPayload.adapter_path = newConfig.adapter_path.trim();
    }

    try {
      const data = await updateConfig(finalPayload);
      setConfig(data.config);
      setIsConfigOpen(false);
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
    }).catch((err) => {
      console.error("Failed to copy: ", err);
    });
  };

  const handleFeedback = async (id: string, isPositive: boolean) => {
    const entry = history.find((e) => e.id === id);
    if (!entry) return;

    try {
      await submitFeedback(entry.question, entry.answer, isPositive);
      setHistory((prev) =>
        prev.map((e) =>
          e.id === id
            ? { ...e, feedback: isPositive ? "positive" : "negative" }
            : e
        )
      );
    } catch (err) {
      console.error("Failed to send feedback", err);
    }
  };

  const clearHistory = () => {
    if (window.confirm("Are you sure you want to clear this session?")) {
      setHistory([]);
    }
  };

  const preprocessMarkdown = (text: string, isFinal: boolean) => {
    // 0. Handle [[SYSTEM_MESSAGE: ... ]]
    let processed = text.replace(
      /\[\[SYSTEM_MESSAGE: (.*?)\]\]/gs,
      (_, msg) => {
        return `\n\`\`\`system-message\n${msg.trim()}\n\`\`\`\n`;
      },
    );

    // 1. Handle [ROLL] formula [/ROLL] or [ROLL] formula
    processed = processed.replace(/\[ROLL\](.*?)\[\/ROLL\]/gs, (_, formula) => {
      return `\n\`\`\`dice-roll-complete\n${formula.trim()}\n\`\`\`\n`;
    });

    // Handle partial streaming [ROLL]
    // If isFinal is true, we treat unclosed rolls as complete
    const rollType = isFinal ? "dice-roll-complete" : "dice-roll-streaming";
    processed = processed.replace(
      /\[ROLL\](?!.*\`\`\`dice-roll)(.*)$/gs,
      (_, formula) => {
        return `\n\`\`\`${rollType}\n${formula.trim()}\n\`\`\`\n`;
      },
    );

    // 2. Handle double pipes as row/section breaks.
    processed = processed.replace(/\|\|/g, "\n");

    // 3. Force newline before a table starts if it's attached to text
    processed = processed.replace(
      /([^\n|])\s*(\|[^|\n]+\|[^|\n]+\|)/g,
      "$1\n$2",
    );

    // 4. Fix run-on lists
    processed = processed.replace(/([^\n])\s*-\s+\*\*/g, "$1\n- **");
    processed = processed.replace(
      /([^\n])\s+\*\*([^*]+)\*\*:/g,
      "$1\n- **$2**:",
    );

    // 5. Identify "faux tables" vs real tables
    const lines = processed.split("\n");
    const result: string[] = [];

    for (let i = 0; i < lines.length; i++) {
      let line = lines[i].trim();
      if (!line) continue;

      const pipeCount = (line.match(/\|/g) || []).length;

      if (pipeCount >= 3) {
        const nextLine = lines[i + 1]?.trim() || "";
        const prevLine = result[result.length - 1]?.trim() || "";
        const isTableSeparator = nextLine.includes("---") ||
          prevLine.includes("---") || line.includes("---");

        if (!isTableSeparator && !line.startsWith("| ---")) {
          const parts = line.split("|").map((p) => p.trim()).filter((p) =>
            p.length > 0
          );
          if (parts.length > 2) {
            parts.forEach((part) => result.push("- " + part));
            continue;
          }
        }
      }

      if (pipeCount >= 1) {
        if (!line.startsWith("|")) line = "| " + line;
        if (!line.endsWith("|")) line = line + " |";

        const nextLineExists = i < lines.length - 1;
        const nextLine = lines[i + 1]?.trim() || "";
        const nextLineIsSeparator = nextLine.includes("---");
        const prevLine = result[result.length - 1]?.trim() || "";
        const prevLineHasPipes = prevLine.startsWith("|") &&
          prevLine.endsWith("|");

        if (
          !prevLineHasPipes && nextLineExists && !nextLineIsSeparator &&
          !line.includes("---")
        ) {
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

    let accumulatedAnswer = "";

    try {
      const sendProfile = process.env.NEXT_PUBLIC_DISABLE_PROFILE !== "true" ? profile : undefined;
      
      await submitConsultation(currentInquiry, {
        onToken: (token) => {
          accumulatedAnswer += token;
          setHistory((prev) =>
            prev.map((entry) =>
              entry.id === entryId
                ? { ...entry, answer: accumulatedAnswer }
                : entry
            )
          );
        },
        onDone: () => {
          setHistory((prev) =>
            prev.map((entry) =>
              entry.id === entryId ? { ...entry, isStreaming: false } : entry
            )
          );
          setIsLoading(false);
        },
        onError: (err) => {
          console.error(err);
          setHistory((prev) =>
            prev.map((entry) =>
              entry.id === entryId
                ? {
                  ...entry,
                  answer:
                    "[[SYSTEM_MESSAGE: The RollMind engine is currently unreachable. Try again later.]]",
                  isStreaming: false,
                }
                : entry
            )
          );
          setIsLoading(false);
        },
      }, sendProfile);
    } catch (err) {
      console.error(err);
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
              onClick={() => setIsProfileOpen(true)}
              title="Character Profile"
            >
              <UserCircle size={24} color="var(--accent)" />
            </button>
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

      {isProfileOpen && (
        <div
          className={styles.modalOverlay}
          onClick={() => setIsProfileOpen(false)}
        >
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2 className={styles.modalTitle}>Character Profile</h2>
              <button
                onClick={() => setIsProfileOpen(false)}
                className={styles.closeModalButton}
              >
                <X size={24} color="var(--accent)" />
              </button>
            </div>
            <div className={styles.configForm}>
              <div className={styles.formRow}>
                <div className={styles.formGroup} style={{ flex: 2 }}>
                  <label>Class</label>
                  <select
                    value={profile.charClass}
                    onChange={(e) =>
                      handleProfileChange({ charClass: e.target.value })}
                    className={styles.select}
                  >
                    {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div className={styles.formGroup} style={{ flex: 1 }}>
                  <label>Level</label>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={profile.level}
                    onChange={(e) =>
                      handleProfileChange({
                        level: parseInt(e.target.value) || 1,
                      })}
                  />
                </div>
              </div>

              <div className={styles.statsGrid}>
                {STATS.map((stat) => {
                  const score = profile.stats[stat];
                  const mod = Math.floor((score - 10) / 2);
                  const displayMod = mod >= 0 ? `+${mod}` : mod;
                  
                  return (
                    <div key={stat} className={styles.formGroup}>
                      <label>{stat} ({displayMod})</label>
                      <input
                        type="number"
                        min="1"
                        max="30"
                        value={score}
                        onChange={(e) =>
                          handleProfileChange({
                            stats: {
                              ...profile.stats,
                              [stat]: parseInt(e.target.value) || 10,
                            },
                          })}
                      />
                    </div>
                  );
                })}
              </div>

              <div className={styles.sectionDivider}>Spellcasting</div>
              <div className={styles.formRow}>
                <div className={styles.formGroup} style={{ flex: 1 }}>
                  <label>Ability</label>
                  <div className={styles.readOnlyValue}>
                    {profile.spellcasting.ability}
                  </div>
                </div>
                <div className={styles.formGroup} style={{ flex: 1 }}>
                  <label>Save DC</label>
                  <input
                    type="number"
                    value={profile.spellcasting.dc}
                    onChange={(e) =>
                      setProfile({
                        ...profile,
                        spellcasting: {
                          ...profile.spellcasting,
                          dc: parseInt(e.target.value) || 10,
                        },
                      })}
                  />
                </div>
                <div className={styles.formGroup} style={{ flex: 1 }}>
                  <label>Attack Bonus</label>
                  <input
                    type="number"
                    value={profile.spellcasting.attackBonus}
                    onChange={(e) =>
                      setProfile({
                        ...profile,
                        spellcasting: {
                          ...profile.spellcasting,
                          attackBonus: parseInt(e.target.value) || 0,
                        },
                      })}
                  />
                </div>
              </div>

              <div className={styles.modalActions}>
                <button
                  type="button"
                  onClick={() => setProfile(DEFAULT_PROFILE)}
                  className={styles.cancelButton}
                >
                  Reset
                </button>
                <button
                  onClick={() => setIsProfileOpen(false)}
                  className={styles.saveButton}
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

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
                {process.env.NEXT_PUBLIC_HIDE_CONFIG !== "true" &&
                  entry.answer && (
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
                      {preprocessMarkdown(entry.answer, !entry.isStreaming)}
                    </ReactMarkdown>
                    {!entry.isStreaming && (
                      <div className={styles.cardFooter}>
                        {!entry.feedback
                          ? (
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
                                onClick={() =>
                                  handleFeedback(entry.id, false)}
                                title="Not helpful"
                              >
                                <ThumbsDown size={14} />
                              </button>
                            </div>
                          )
                          : (
                            <div className={styles.feedbackThanks}>
                              {entry.feedback === "positive"
                                ? "Helpful"
                                : "Not helpful"} feedback received. Thank you!
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
