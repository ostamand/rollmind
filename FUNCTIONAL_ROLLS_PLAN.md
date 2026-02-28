# Plan: Implementing Functional Dice Rolls ([ROLL])

This document outlines the strategy for evolving Rollmind from a D&D knowledge assistant into a functional game assistant capable of calculating and outputting dice rolls based on character context.

## 1. Objective
Enable the model to ingest character details and output specific dice rolls for requested actions (initially focusing on **Spells**) using a custom tag: `[ROLL]XdY+Z[/ROLL]`. The model will perform the calculation (e.g., adding Proficiency and Ability modifiers) internally based on the provided character context.

## 2. Core Strategy: Multi-Task Step 2
I recommend **combining** this functionality into **Step 2 (Instruction Tuning)** rather than a separate Step 3.

### Reasoning:
*   **Prevent Regression:** Training on rolls only could cause "catastrophic forgetting" of general knowledge.
*   **Contextual Awareness:** The model needs to use the knowledge learned in Step 1 to determine *which* dice to roll.
*   **Format Consistency:** The model learns that `[ROLL]` is part of its standard toolkit.

## 3. Dataset Generation (`prepare/generate_rolls.py`)

Generating accurate rolls requires grounding the model in the **natural language context** and rules of the spell directly from its source documentation.

### A. Source Data (`data/spells/*.md`)
We will use individual Markdown files for each spell, where the filename is the spell name (e.g., `Fireball.md`). Each file contains the full 2024 Player's Handbook entry for that spell.

### B. The Character Profile (Automatic Injection)
Every training example includes a profile. In the final app, this is injected automatically before the user prompt.
*   **Format:**
    ```text
    Character Profile: [Class] [Level]. Stats: STR [X] (+M)... 
    Spellcasting: Ability [Stat], DC [DC], Attack Bonus [Bonus].
    ```
*   **Generation:** `prepare/generate_rolls.py` will programmatically generate random valid profiles to provide training variance.

### C. Script Logic: Context-Driven Generation
The generation script uses the raw Markdown as the source of truth for both flavor and mechanics:

1.  **Selection:** Pick a random spell file from `data/spells/`.
2.  **Context Loading:** Read the full Markdown content.
3.  **Prompting:** Feed the **Full Spell Markdown + Profile** to Gemini. The prompt instructs Gemini to:
    *   Identify the correct dice/scaling from the text.
    *   Apply the modifiers from the Character Profile.
    *   Generate a natural conversation including the correctly calculated `[ROLL]` tags.
4.  **Completion:** Gemini generates a response grounded entirely in the provided Markdown.
    *   **User:** "I cast Fireball at 4th level!"
    *   **Model:** "You unleash a 4th-level Fireball. Targets must make a DC 15 Dexterity save. Damage: [ROLL]9d6[/ROLL] fire."

### D. Advanced Logic & Edge Cases
The prompt for the generator will explicitly handle D&D mechanics:
1.  **Upcasting:** Instructions on how to interpret "At Higher Levels" sections in the Markdown.
2.  **Cantrip Scaling:** Logic for scaling damage at levels 5, 11, and 17 as described in the text.
3.  **Multiple Rolls:** Instructions to output multiple `[ROLL]` tags for spells with multiple targets or beams (e.g., *Eldritch Blast*).

## 4. Technical Implementation Steps

### Phase 1: Training Pipeline Updates
*   **Data Mix:** Step 2 will now load a balanced mix of `train_qa.jsonl` and the new `train_rolls.jsonl` (generated from the spell markdown files) to ensure the model maintains its general knowledge while learning the new rolling functionality.

### Phase 2: Inference Refinement
Update `inference.py` to support a `--character` flag which automatically formats the prompt to include the profile header. This ensures the model always has the necessary context to calculate rolls during interactive sessions.

## 5. Implementation Roadmap
1.  **Spell Preparation:** Split source spell documentation into individual files in `data/spells/*.md`.
2.  **Persona Utility:** Write a Python function to generate random character stat blocks.
3.  **Roll Generator:** Implement `prepare/generate_rolls.py` (Providing Markdown context + Character Profile to Gemini).
4.  **Fine-tuning:** Run Step 2 with the mixed dataset.
