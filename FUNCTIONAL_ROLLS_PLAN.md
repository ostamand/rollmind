# Plan: Implementing Functional Dice Rolls (<roll>)

This document outlines the strategy for evolving Rollmind from a D&D knowledge assistant into a functional game assistant capable of calculating and outputting dice rolls based on character context.

## 1. Objective
Enable the model to ingest character details and output specific dice rolls for requested actions using a custom tag: `<roll>XdY+Z</roll>`.

## 2. Core Strategy: Multi-Task Step 2
I recommend **combining** this functionality into **Step 2 (Instruction Tuning)** rather than a separate Step 3.

### Reasoning:
*   **Prevent Regression:** Training on rolls only could cause "catastrophic forgetting" of general knowledge.
*   **Contextual Awareness:** The model needs to use the knowledge learned in Step 1 to determine *which* dice to roll.
*   **Format Consistency:** The model learns that `<roll>` is part of its standard toolkit.

## 3. Dataset Generation (`prepare/generate_rolls.py`)

Generating accurate rolls requires combining data from multiple chapters. A Level 1 Fighter's attack with a Longsword depends on **Chapter 3** (Proficiency Bonus), **Chapter 2** (Ability Modifiers), and **Chapter 6** (Weapon Damage).

### The Character Profile
Every training example will include a comprehensive profile:
*   **Race & Class:** (e.g., High Elf Wizard)
*   **Level:** (1-20)
*   **Stats:** Str, Dex, Con, Int, Wis, Cha (expressed as values like 16, 8, etc.)
*   **Proficiencies:** Skills or weapons the character is proficient in.

### Script Logic: Cross-Chapter Contextualization
The `generate_rolls.py` script will use a **"Rule-Contextualized Generation"** approach:

1.  **Context Loading:** The script will load key reference "Summaries" from the markdown files:
    *   *Classes Table:* For Level-to-Proficiency mapping.
    *   *Equipment Table:* For weapon damage dice and properties.
    *   *Ability Score Rules:* For calculating modifiers from raw scores.
2.  **Persona Creation:** The script will programmatically generate random valid character profiles (e.g., "Level 5 Dwarf Cleric with Str 14, Wis 18...").
3.  **Action Prompting:** It will feed Vertex AI a character profile + a specific manual chunk (e.g., a spell description or weapon rule).
4.  **Chain-of-Thought Generation:** The generator (Gemini 3 Flash) will be instructed to:
    *   *Identify the Rule:* "This action uses the 'Attack' rule from Chapter 1."
    *   *Identify the Dice:* "Longswords do 1d8 damage."
    *   *Identify the Modifiers:* "Level 5 has a +3 Proficiency. Strength 14 is a +2 Modifier."
    *   *Produce the JSON:* Output the final User/Assistant turn with the `<roll>` tags.

### Example Dataset Entry:
```json
{
  "text": "<start_of_turn>user
Character: Level 5 Hill Dwarf Fighter. Stats: Str 18 (+4), Dex 12 (+1), Con 16 (+3), Int 10 (+0), Wis 12 (+1), Cha 8 (-1). 
Action: I want to attack with my Battleaxe.<end_of_turn>
<start_of_turn>model
As a Level 5 Fighter, your Proficiency Bonus is +3. Using your Strength (+4) for a Battleaxe attack, your total bonus to hit is +7. 
Attack Roll: <roll>1d20+7</roll>
On a hit, you deal <roll>1d8+4</roll> slashing damage (one-handed) or <roll>1d10+4</roll> if using it with two hands.<end_of_turn>"
}
```

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
1.  **Persona Utility:** Write a Python function to generate random character stat blocks.
2.  **Roll Generator:** Implement `prepare/generate_rolls.py` with Vertex AI.
3.  **Merging:** Combine all Step 2 datasets.
4.  **Fine-tuning:** Run Step 2 with special token logic.
