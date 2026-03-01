# RollMind Training Data Expansion Ideas

This document outlines high-value categories to add to the training pipeline for the D&D 2024 assistant.

## 1. Martial & Weapon Attacks
- **Goal:** Enable martial characters (Fighters, Barbarians, Rogues) to perform weapon attacks using their `STR` or `DEX`.
- **Logic:** Use the character's profile stats and proficiency bonus.
- **Example:** "I attack with my Longsword." -> "With your +5 Strength and Proficiency, your attack bonus is +7: **[ROLL]1d20+7[/ROLL]**. On a hit, you deal **[ROLL]1d8+5[/ROLL]** slashing damage."

## 2. Skill Checks & Saving Throws
- **Goal:** Handle proactive requests for Athletics, Stealth, Perception, or personal Saving Throws.
- **Logic:** Ground the roll in the character's ability scores and proficiencies.
- **Example:** "I want to sneak past the guards." -> "With your +4 Dexterity and Proficiency in Stealth, your total bonus is +6: **[ROLL]1d20+6[/ROLL]**."

## 3. Advantage & Disadvantage
- **Goal:** Proactively handle mechanical modifiers when requested or implied.
- **Logic:** Output two `[ROLL]` tags or explain the dual roll.
- **Example:** "I cast Fire Bolt with Advantage!" -> "Since you have Advantage, I'll roll twice for your attack: **[ROLL]1d20+5[/ROLL]** and **[ROLL]1d20+5[/ROLL]**. You use the higher result!"

## 4. Healing & Buffs
- **Goal:** Handle restorative and beneficial effects (e.g., *Cure Wounds*, *Healing Word*, *Aid*).
- **Logic:** Calculate healing amounts based on spell level and ability modifiers.
- **Example:** "I cast Cure Wounds at 2nd level." -> "Upcasting to 2nd level, you restore **[ROLL]2d8+4[/ROLL]** hit points to your target."

## 5. Multi-Attack / Multi-Beam Spells
- **Goal:** Handle spells or features that require multiple separate rolls (e.g., *Eldritch Blast*, *Scorching Ray*, "Extra Attack").
- **Logic:** Output separate `[ROLL]` tags for each beam or attack.
- **Example:** "I cast Eldritch Blast (Level 5)!" -> "As a 5th-level caster, you fire two beams. Beam 1: **[ROLL]1d20+6[/ROLL]** for **[ROLL]1d10+4[/ROLL]** damage. Beam 2: **[ROLL]1d20+6[/ROLL]** for **[ROLL]1d10+4[/ROLL]** damage."

## 6. Critical Hit Logic
- **Goal:** Correctly handle "Critical Hit" damage doubling per 2024 rules.
- **Logic:** Double the number of damage dice (e.g., 2d8 instead of 1d8) when a crit is confirmed or requested.

---

## Technical Next Steps
1. **Update `prepare/utils.py`:** Enhance `generate_random_profile` to include weapons, equipment, and skill proficiencies.
2. **Create `prepare/generate_martial_rolls.py`:** Dedicated script for weapon-based training data.
3. **Create `prepare/generate_skill_rolls.py`:** Dedicated script for skill-check and saving-throw training data.
