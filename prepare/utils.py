import random
import re

def extract_classes_from_markdown(markdown):
    """
    Extracts allowed classes from a D&D spell markdown.
    Example line: *Level 2 Transmutation (Sorcerer, Wizard)*
    """
    # Look for parentheses inside the first italicized line (usually line 3)
    # The pattern matches text between parentheses after Level/Cantrip info
    match = re.search(r"\*.*?\(([^)]+)\)\s*\*", markdown)
    if match:
        classes_str = match.group(1)
        # Split by comma and strip whitespace
        return [c.strip() for c in classes_str.split(",")]
    return None

def extract_spell_level(markdown):
    """
    Extracts the spell level from a D&D spell markdown.
    Returns 0 for cantrips, and 1-9 for leveled spells.
    """
    # Look for "Level X" or "Cantrip" in the first italicized line
    match = re.search(r"\*(Level|Cantrip)\s*(\d+)?", markdown, re.IGNORECASE)
    if match:
        type_str = match.group(1).lower()
        if type_str == "cantrip":
            return 0
        level_str = match.group(2)
        if level_str:
            return int(level_str)
    return 0

def generate_random_profile(allowed_classes=None, spell_level=0):
    """
    Generates a random D&D 2024 character profile string.
    This is used to ground the model in character context for training data.
    """
    all_classes = ["Barbarian", "Bard", "Cleric", "Druid", "Fighter", "Monk", "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard"]
    
    if allowed_classes:
        # Filter and ensure we only use valid classes from our list
        classes = [c for c in all_classes if c in allowed_classes]
        # If no match (e.g. subclass or something), just use the provided allowed_classes
        if not classes:
            classes = allowed_classes
    else:
        classes = all_classes
    char_class = random.choice(classes)

    # Calculate minimum level required to cast a spell of spell_level
    min_level = 1
    if spell_level > 0:
        if char_class in ["Bard", "Cleric", "Druid", "Sorcerer", "Warlock", "Wizard"]:
            # Full casters: 1:1, 2:3, 3:5, 4:7, 5:9, 6:11, 7:13, 8:15, 9:17
            min_level = max(1, (spell_level * 2) - 1)
        elif char_class in ["Paladin", "Ranger"]:
            # Half casters: 1:2, 2:5, 3:9, 4:13, 5:17
            min_level = (spell_level * 4) - 3 if spell_level > 1 else 2
        elif char_class in ["Fighter", "Rogue"]:
            # Third casters (Eldritch Knight / Arcane Trickster): 1:3, 2:7, 3:13, 4:19
            min_level = (spell_level * 6) - 5 if spell_level > 1 else 3
        else:
            # Default to full caster progression for safety if class unknown
            min_level = max(1, (spell_level * 2) - 1)

    # Add a small buffer (0-3 levels) to allow for upcasting examples and variance
    # This ensures a "Wizard Level 5" isn't always casting Fireball at its base level.
    level_buffer = random.randint(0, 3)
    level = min(20, min_level + level_buffer)

    # Simple stat generation (approximate)

    stats = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
    
    # Simple stat generation (approximate)
    stat_values = {stat: random.randint(8, 20) for stat in stats}
    stat_mods = {stat: (val - 10) // 2 for stat, val in stat_values.items()}
    
    # Determine spellcasting ability based on class
    if char_class in ["Wizard"]:
        spell_stat = "INT"
    elif char_class in ["Cleric", "Druid", "Ranger"]:
        spell_stat = "WIS"
    elif char_class in ["Bard", "Paladin", "Sorcerer", "Warlock"]:
        spell_stat = "CHA"
    else:
        # Default for non-casters or subclasses to allow variance
        spell_stat = random.choice(["INT", "WIS", "CHA"])
        
    prof_bonus = (level - 1) // 4 + 2
    spell_mod = stat_mods[spell_stat]
    spell_save_dc = 8 + prof_bonus + spell_mod
    spell_attack_bonus = prof_bonus + spell_mod
    
    profile = f"Character Profile: {char_class} Level {level}. Stats: "
    profile += ", ".join([f"{s} {stat_values[s]} ({stat_mods[s]:+})" for s in stats])
    profile += f".\nSpellcasting: Ability {spell_stat}, DC {spell_save_dc}, Attack Bonus {spell_attack_bonus:+}."
    
    return profile
