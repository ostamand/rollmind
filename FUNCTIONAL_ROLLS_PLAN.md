# Implementation: Functional Dice Rolls ([ROLL])

This document details the successful implementation of the functional dice roll system, which allows RollMind to calculate and output specific dice rolls based on character context.

## 1. Objective Achieved
The model can now ingest character details (Class, Level, Stats) and output mechanical actions using a custom tag: `[ROLL]XdY+Z[/ROLL]`. This system ensures that dice results are mathematically accurate and grounded in the rules, while the actual "roll" is performed cryptographically by the application.

## 2. The Tag System
RollMind uses a specific XML-style tag for all mechanical checks:
- **Format:** `[ROLL]XdY+Z[/ROLL]`
- **Examples:** 
  - `[ROLL]8d6[/ROLL]` (Fireball damage)
  - `[ROLL]1d20+7[/ROLL]` (Spell attack with +7 bonus)
  - `[ROLL]1d20+2[/ROLL]` (Wisdom saving throw for a target)

## 3. Training & Data Generation
The functionality was baked into **Step 2 (Instruction Alignment)** using a dedicated synthetic pipeline:
- **Source Truth:** `prepare/generate_rolls.py` used the raw spell markdown files from the PHB 2024 as the source of truth for dice formulas.
- **Context Injection:** Every training example included a randomized **Character Profile**. This taught the model to:
  - Add the correct **Ability Modifier** and **Proficiency Bonus** to d20 rolls.
  - Apply **Upcasting** logic (e.g., adding 1d6 per slot level above base).
  - Apply **Cantrip Scaling** (jumps at levels 5, 11, and 17).

## 4. Application Integration
The RollMind Web App (`app/web/`) features a specialized `DiceRoller` component:
1.  **Interception:** The frontend identifies `[ROLL]` tags in the model's streaming response.
2.  **Animation:** A gold-themed dice icon spins while the tag is being "processed."
3.  **Cryptographic Roll:** The system performs a true random roll based on the formula provided in the tag.
4.  **Display:** The final result is displayed with a full breakdown (e.g., `31 = (4+6+5+2+6+1+4+3)`) to ensure transparency and excitement.

## 5. Why This Implementation Works
- **No Hallucinations:** Generic LLMs often "hallucinate" high numbers (natural 20s) to please the user. RollMind only provides the formula; the app provides the luck.
- **Contextual Accuracy:** Because the model was trained on the PHB 2024, it knows that *Magic Missile* is 1d4+1 and *Fireball* is 8d6 without needing external lookups during inference.
- **Character Synergy:** The model uses the specific stats of the active character profile to calculate bonuses, making the assistant feel like a true companion to the player's unique character.
