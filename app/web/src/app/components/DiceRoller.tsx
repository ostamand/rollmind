"use client";

import { useEffect, useState, useRef } from "react";
import { Dices } from "lucide-react";
import styles from "../page.module.css";

interface DiceRollerProps {
  formula: string;
  isComplete: boolean;
}

// Session-persistent cache to prevent re-rolling on remounts
const resultCache = new Map<string, { total: number; breakdown: string }>();

export default function DiceRoller({ formula, isComplete }: DiceRollerProps) {
  const normalizedFormula = formula.toLowerCase().replace(/\s+/g, "");
  
  // 1. Initial State: Check cache immediately to stop the loop
  const cached = resultCache.get(normalizedFormula);
  
  const [result, setResult] = useState<{ total: number; breakdown: string } | null>(cached || null);
  const [isRolling, setIsRolling] = useState(!cached);
  const [displayValue, setDisplayValue] = useState<number | string>(cached?.total || "?");
  const [sides, setSides] = useState(20);
  
  const animationHandled = useRef(!!cached);

  // Update sides for animation context
  useEffect(() => {
    const match = normalizedFormula.match(/\d+d(\d+)/);
    if (match) setSides(parseInt(match[1]));
  }, [normalizedFormula]);

  // 2. Logic: Handle the transition to 'complete'
  useEffect(() => {
    // If we already have a result (from cache or finished animation), do nothing
    if (result || animationHandled.current) return;

    if (isComplete) {
      animationHandled.current = true;
      const rollResult = parseFormula(normalizedFormula);
      
      if (rollResult) {
        // CRITICAL: Save to cache IMMEDIATELY so remounts see it as settled
        resultCache.set(normalizedFormula, rollResult);

        // Play the animation once
        const timer = setTimeout(() => {
          setResult(rollResult);
          setIsRolling(false);
          setDisplayValue(rollResult.total);
        }, 1000);
        return () => clearTimeout(timer);
      } else {
        setIsRolling(false);
        setDisplayValue("Error");
      }
    }
  }, [isComplete, normalizedFormula, result]);

  // 3. Animation Interval
  useEffect(() => {
    if (!isRolling) return;
    const interval = setInterval(() => {
      setDisplayValue(Math.floor(Math.random() * sides) + 1);
    }, 80);
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
        ? `(${rolls.join(" + ")})${mod !== 0 ? (mod > 0 ? " + " + mod : " - " + Math.abs(mod)) : ""}`
        : `${rolls[0]}${mod !== 0 ? (mod > 0 ? " + " + mod : " - " + Math.abs(mod)) : ""}`;
      return { total: finalTotal, breakdown };
    } catch (e) {
      return null;
    }
  }

  return (
    <div className={`${styles.diceRoller} ${isRolling ? styles.rolling : ""}`} role="status" aria-live="polite">
      <div className={styles.diceHeader}>
        <Dices size={14} className={`${styles.diceIcon} ${isRolling ? styles.spin : ""}`} />
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
