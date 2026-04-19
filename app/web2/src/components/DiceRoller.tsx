"use client";

import { useEffect, useRef, useState } from "react";
import { Dices } from "lucide-react";
import styles from "../App.module.css";

interface DiceRollerProps {
  formula: string;
  isComplete: boolean;
}

// Session-persistent cache to prevent re-rolling same results
const resultCache = new Map<string, { total: number; breakdown: string }>();

export default function DiceRoller({ formula, isComplete }: DiceRollerProps) {
  const normalizedFormula = formula.toLowerCase().replace(/\s+/g, "");

  // 1. Check cache immediately to prevent unnecessary animation if already rolled
  const cached = resultCache.get(normalizedFormula);

  const [result, setResult] = useState<
    { total: number; breakdown: string } | null
  >(cached || null);
  const [isRolling, setIsRolling] = useState(!cached);
  const [displayValue, setDisplayValue] = useState<number | string>(
    cached?.total || "?",
  );
  const [sides, setSides] = useState(20);

  // Use refs to track state across re-renders/remounts during streaming
  const formulaRef = useRef(normalizedFormula);
  const finalizeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 2. Handle Formula Changes (Streaming)
  useEffect(() => {
    // If the formula changed while we are still streaming
    if (formulaRef.current !== normalizedFormula) {
      formulaRef.current = normalizedFormula;

      const match = normalizedFormula.match(/\d+d(\d+)/);
      if (match) setSides(parseInt(match[1]));

      // If we previously finished a roll but the model is now changing it
      const newCache = resultCache.get(normalizedFormula);
      if (newCache) {
        setResult(newCache);
        setIsRolling(false);
        setDisplayValue(newCache.total);
      } else {
        setResult(null);
        setIsRolling(true);
      }
    }
  }, [normalizedFormula]);

  // 3. Handle Completion with Dynamic Delay
  useEffect(() => {
    // If we just became complete and aren't already finalizing
    if (isComplete && isRolling && !result && !finalizeTimerRef.current) {
      // Random delay between 0.4s and 1s to make it feel snappier
      const randomDelay = Math.floor(Math.random() * 600) + 400;

      finalizeTimerRef.current = setTimeout(() => {
        const rollResult = parseFormula(normalizedFormula);
        if (rollResult) {
          resultCache.set(normalizedFormula, rollResult);
          setResult(rollResult);
          setDisplayValue(rollResult.total);
        } else {
          setDisplayValue("Error");
        }
        setIsRolling(false);
        finalizeTimerRef.current = null;
      }, randomDelay);
      }

      return () => {
      if (finalizeTimerRef.current) {
        clearTimeout(finalizeTimerRef.current);
        finalizeTimerRef.current = null;
      }
      };
      }, [isComplete, isRolling, normalizedFormula, result]);

      // 4. Animation Interval
      useEffect(() => {
      if (!isRolling) return;
      const interval = setInterval(() => {
      setDisplayValue(Math.floor(Math.random() * sides) + 1);
      }, 50);
      return () => clearInterval(interval);
      }, [isRolling, sides]);

  function parseFormula(f: string) {
    try {
      const match = f.match(/(\d+)d(\d+)([+-]\d+)?/);
      if (!match) return null;
      const count = parseInt(match[1]);
      const s = parseInt(match[2]);
      const mod = match[3] ? parseInt(match[3]) : 0;
      const rolls: number[] = [];
      let total = 0;
      for (let i = 0; i < count; i++) {
        const r = Math.floor(Math.random() * s) + 1;
        rolls.push(r);
        total += r;
      }
      const finalTotal = total + mod;
      const breakdown = rolls.length > 1
        ? `(${rolls.join(" + ")})${
          mod !== 0 ? (mod > 0 ? " + " + mod : " - " + Math.abs(mod)) : ""
        }`
        : `${rolls[0]}${
          mod !== 0 ? (mod > 0 ? " + " + mod : " - " + Math.abs(mod)) : ""
        }`;
      return { total: finalTotal, breakdown };
    } catch (e) {
      return null;
    }
  }

  return (
    <div
      className={`${styles.diceRoller} ${isRolling ? styles.rolling : ""}`}
      role="status"
      aria-live="polite"
    >
      <div className={styles.diceHeader}>
        <Dices
          size={14}
          className={`${styles.diceIcon} ${isRolling ? styles.spin : ""}`}
        />
        <span>{formula || "Rolling..."}</span>
      </div>
      <div className={styles.diceMain}>
        <span className={styles.diceResult}>{displayValue}</span>
        {!isRolling && result && (
          <span className={styles.diceBreakdown}>= {result.breakdown}</span>
        )}
      </div>
    </div>
  );
}
