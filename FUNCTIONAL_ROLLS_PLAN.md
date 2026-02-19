# Plan: Implementing Functional Dice Rolls (<roll>)

This document outlines the strategy for evolving Rollmind from a D&D knowledge assistant into a functional game assistant capable of calculating and outputting dice rolls based on character context.

## 1. Objective
Enable the model to ingest character details and output specific dice rolls for requested actions (initially focusing on **Spells**) using a custom tag: `<roll>XdY+Z</roll>`. The model will perform the calculation (e.g., adding Proficiency and Ability modifiers) internally based on the provided character context.

## 2. Core Strategy: Multi-Task Step 2
I recommend **combining** this functionality into **Step 2 (Instruction Tuning)** rather than a separate Step 3.

### Reasoning:
*   **Prevent Regression:** Training on rolls only could cause "catastrophic forgetting" of general knowledge.
*   **Contextual Awareness:** The model needs to use the knowledge learned in Step 1 to determine *which* dice to roll.
*   **Format Consistency:** The model learns that `<roll>` is part of its standard toolkit.

## 3. Dataset Generation (`prepare/generate_rolls.py`)

Generating accurate rolls requires grounding the model in factual spell data and character statistics.

### A. Knowledge Extraction
Before generating training data, we extract a structured "Knowledge Base" from the source Markdown files (initially for Spells).
*   **Source:** `data/spells.md`
*   **Target:** `data/spells.json` (Structured data: level, damage dice, save type, scaling, etc.)
*   **Tool:** A one-time parsing script using Gemini to convert MD to JSON.

### B. The Character Profile (Automatic Injection)
Every training example includes a profile. In the final app, this is injected automatically before the user prompt.
*   **Format:**
    ```text
    Character Profile: [Class] [Level]. Stats: STR [X] (+M)... 
    Spellcasting: Ability [Stat], DC [DC], Attack Bonus [Bonus].
    ```
*   **Generation:** `prepare/generate_rolls.py` will programmatically generate random valid profiles to provide training variance.

### C. Script Logic: Programmatic Grounding
Instead of asking the LLM to "guess" the roll, the generation script *tells* the LLM what the roll should be.

1.  **Selection:** Pick a random Spell (from `spells.json`) and a random valid Character Profile.
2.  **Calculation:** A Python function calculates the exact dice and DC (e.g., "Fireball at 4th level for a Wizard with 18 Int and +3 Prof is 9d6 damage and DC 15").
3.  **Prompting:** Feed the **Profile + Spell + Calculated Math** to Gemini.
4.  **Completion:** Gemini generates a natural conversation:
    *   **User:** "I cast Fireball at 4th level!"
    *   **Model:** "You unleash a 4th-level Fireball. Targets must make a DC 15 Dexterity save. Damage: <roll>9d6</roll> fire."

### D. Advanced Logic & Edge Cases
The generation script must handle specific D&D mechanics to ensure high-quality training data:

1.  **Multiple Rolls (Beams/Targets):** For spells like *Scorching Ray* or *Eldritch Blast*, the script must provide math for multiple beams. The model should be trained to output multiple `<roll>` tags (e.g., "Beam 1: <roll>1d20+5</roll> to hit...").
2.  **Dual Scaling Logic:**
    *   **Cantrips:** Scale based on **Character Level** (jumps at levels 5, 11, and 17).
    *   **Leveled Spells:** Scale based on the **Slot Level** used for the cast.
3.  **Safety & Validation:** Include "Negative" examples where a user requests a spell level higher than their character allows (e.g., Level 1 Wizard casting *Fireball*). The model should politely explain the limitation and suggest a valid alternative.

## 4. Technical Implementation Steps

### Phase 1: Special Token Registration
Register `<roll>` and `</roll>` as **Special Tokens**. 
*   **Reasoning:** Prevents the tokenizer from splitting the tags (e.g., into `<` and `roll`). This ensures the model outputs the exact string `<roll>` as a single predicted token, making it easy for external applications to parse and execute the roll.

### Phase 2: Training Pipeline Updates
*   **Embedding Resizing:** Update `train_step2.py` to resize the model's embedding layer using `model.resize_token_embeddings(len(tokenizer))`.
*   **Data Mix:** Step 2 will now load a 50/50 mix of `train_qa.jsonl` and `train_rolls.jsonl` to ensure balanced capabilities.

### Phase 3: Inference Refinement
Update `inference.py` to support a `--character` flag which automatically formats the prompt to include the profile header.

## 5. Implementation Roadmap
1.  **Data Extraction:** Create `prepare/extract_spells.py` to generate `data/spells.json`.
2.  **Persona Utility:** Write a Python function to generate random character stat blocks.
3.  **Roll Generator:** Implement `prepare/generate_rolls.py` (Programmatic Calculation + Gemini for natural language).
4.  **Fine-tuning:** Run Step 2 with special token logic and mixed dataset.
