# RollMind Inference & Dice Roll Flow

This document explains the end-to-end flow of how RollMind processes a user request, integrates character context, and handles functional dice rolls using the `[ROLL]` tag system.

## 1. The High-Level Flow

1.  **User Input:** The user provides a prompt (e.g., "I cast Fireball!").
2.  **Context Injection:** The system prepends the **Character Profile** (active in the UI) to the prompt.
3.  **Templating:** The combined text is wrapped in the official **Gemma Instruction Template**.
4.  **Inference:** The templated string is sent to the fine-tuned model (Gemma 3 12B or Gemma 1.1 7B).
5.  **Tag Detection:** As the model streams the response, the frontend listens for the `[ROLL]...[/ROLL]` tags.
6.  **Functional Execution:** When a tag is detected, the `DiceRoller` component extracts the dice formula (e.g., `8d6`), performs a cryptographic roll, and displays the animated result.
7.  **Final Output:** The user sees the natural language response with the interactive dice component integrated seamlessly.

---

## 2. Concrete Example: Casting Fireball

### Step A: User Input
The user has configured their profile in the app and types:
> **User:** "I cast Fireball at the group of goblins!"

### Step B: Profile & Prompt Assembly
The frontend retrieves the active character profile. For a Level 5 Wizard with an Intelligence of 18 (+4), the profile looks like this:
```text
Character Profile: Wizard Level 5. Stats: STR 8 (-1), DEX 14 (+2), CON 14 (+2), INT 18 (+4), WIS 12 (+1), CHA 10 (+0). Spellcasting: Ability INT, DC 15, Attack +7.
```

The system combines them:
```text
Character Profile: Wizard Level 5. Stats: STR 8 (-1), DEX 14 (+2), CON 14 (+2), INT 18 (+4), WIS 12 (+1), CHA 10 (+0). Spellcasting: Ability INT, DC 15, Attack +7.

I cast Fireball at the group of goblins!
```

### Step C: Applying the Instruction Template
The combined prompt is wrapped for the Gemma model:
```text
<start_of_turn>user
Character Profile: Wizard Level 5. Stats: STR 8 (-1), DEX 14 (+2), CON 14 (+2), INT 18 (+4), WIS 12 (+1), CHA 10 (+0). Spellcasting: Ability INT, DC 15, Attack +7.

I cast Fireball at the group of goblins!<end_of_turn>
<start_of_turn>model
```

### Step D: Model Generation (Internal)
The model, having been fine-tuned on D&D rules and the `[ROLL]` format, generates:
> "You point your finger at the goblins and a bright streak flashes... The targets must make a DC 15 Dexterity saving throw. On a failed save, they take [ROLL]8d6[/ROLL] fire damage."

### Step E: Tag Extraction and Rolling
As the model streams `[ROLL]8d6[/ROLL]`, the Web App interceptor:
1.  Identifies the formula: `8d6`.
2.  Triggers the `DiceRoller` animation.
3.  Calculates the random result: `31`.

### Step F: Final UI Output
The user sees the text appearing in real-time, with an interactive gold-themed box showing **31** where the tag was.

---

## 3. Why This Flow is Powerful

*   **Rule Grounding:** The model "knows" that Fireball is 8d6 because of its Step 1 training on the PHB.
*   **Contextual Accuracy:** By injecting the profile, the model correctly outputs the "DC 15" instead of a generic number.
*   **Fairness:** The actual "rolling" happens in the application logic, ensuring that the dice results are truly random and not hallucinated.
*   **Seamlessness:** Using `[ROLL]` tags allows the model to decide *when* a roll is appropriate based on its understanding of the rules.
