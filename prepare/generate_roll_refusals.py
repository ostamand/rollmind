import json
import os
import time
import argparse
import random
import glob
import re
from tqdm import tqdm
import vertexai
from vertexai.generative_models import GenerativeModel
from dotenv import load_dotenv
from prepare.utils import generate_random_profile, extract_classes_from_markdown, extract_spell_level

# Load environment variables
load_dotenv()

REFUSAL_CATEGORIES = [
    {
        "category": "Level Mismatch",
        "description": "User tries to cast a spell they could have, but aren't high enough level for.",
        "instructions": "Generate Q&A where the user asks to cast a spell (e.g., 'I cast Fireball') but their character level is too low to have slots of that level. The model should refuse and explain they need to be a higher level."
    },
    {
        "category": "Upcasting Limits",
        "description": "User tries to upcast a spell beyond their available slot levels.",
        "instructions": "Generate Q&A where the user asks to upcast a spell (e.g., 'Fireball at 5th level') but their character level doesn't grant them slots of that level. The model should refuse and explain the limit of their power."
    },
    {
        "category": "Class Restriction",
        "description": "User tries to cast a spell not available to their class.",
        "instructions": "Generate Q&A where the user asks to cast a spell (e.g., 'I cast Eldritch Blast') but their class (e.g., Cleric) doesn't have that spell on their list. The model should refuse and suggest it's not in their repertoire."
    },
    {
        "category": "Non-existent Spell",
        "description": "User tries to cast a spell that doesn't exist in the 2024 PHB.",
        "instructions": "Generate Q&A where the user asks to cast a spell that isn't in D&D 2024 (e.g., 'Avada Kedavra', 'Abra-ka-dabra', or a spell from another system). The model should refuse and state it's not a known D&D 2024 spell."
    }
]

def generate_refusal_batch(category_info, spell_name, profile, spell_markdown, model, num_pairs=5):
    context = f"CHARACTER PROFILE:\n{profile}"
    if spell_markdown:
        context += f"\n\nSPELL DATA:\n{spell_markdown}"

    prompt = f"""
You are helping to train a D&D 2024 specialized AI called "RollMind".
Generate {num_pairs} Q&A pairs for the following category: {category_info['category']}.

CATEGORY DESCRIPTION: {category_info['description']}
SPECIFIC INSTRUCTIONS: {category_info['instructions']}

{context}

--- RULES FOR RESPONSE ---
1. USER INPUT: A SHORT, direct command to cast the spell "{spell_name}".
   - Keep it under 10 words.
   - Good: "I cast {spell_name}", "Cast {spell_name} at 5th level", "Can I use {spell_name}?".
   - Avoid long descriptions or roleplay fluff.
2. MODEL RESPONSE:
   - Must be polite, professional, and grounded in D&D 5e (2024) rules.
   - Must EXPLAIN WHY the action is not possible based on the Character Profile provided.
   - Should NOT use the [ROLL] tag since the action is impossible.
   - For "Non-existent Spell", clarify that the spell is not part of the 2024 Player's Handbook.
   - Tone should be that of an expert Dungeon Master's companion.
3. FORMAT: Output as a valid JSON list of objects.

Format:
[
  {{"question": "...", "answer": "..."}},
  ...
]
"""
    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        match = re.search(r"(\[.*\])", content, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return []
    except Exception as e:
        print(f"Error generating batch for {category_info['category']}: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Generate roll-specific refusal dataset")
    parser.add_argument("--spells_dir", type=str, default="data/spells", help="Directory containing spell markdown files")
    parser.add_argument("--output_file", type=str, default="data/step2/v2/rolls/_A100_roll_refusals.jsonl", help="Output JSONL file")
    parser.add_argument("--project", type=str, default=os.environ.get("GOOGLE_CLOUD_PROJECT"), help="GCP Project ID")
    parser.add_argument("--total_pairs", type=int, default=100, help="Total refusal pairs to generate")
    args = parser.parse_args()

    if not args.project:
        parser.error("The --project argument or GOOGLE_CLOUD_PROJECT environment variable is required.")

    vertexai.init(project=args.project, location="global")
    model = GenerativeModel("gemini-3-flash-preview")

    spell_files = glob.glob(os.path.join(args.spells_dir, "*.md"))
    random.shuffle(spell_files)

    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)

    pairs_per_category = args.total_pairs // len(REFUSAL_CATEGORIES)
    batch_size = 5

    print(f"Generating {args.total_pairs} roll refusal pairs...")

    with open(args.output_file, 'w', encoding='utf-8') as f_out:
        for cat in REFUSAL_CATEGORIES:
            print(f"\n>>> Category: {cat['category']}")
            generated = 0
            while generated < pairs_per_category:
                # Prepare profile and spell data based on category
                spell_markdown = None
                profile = ""
                spell_name = "N/A"
                
                if cat['category'] == "Level Mismatch":
                    # Pick a leveled spell (Level 2+) so a Level 1 character definitely can't cast it
                    spell_path = random.choice(spell_files)
                    spell_name = os.path.basename(spell_path).replace(".md", "").title()
                    with open(spell_path, 'r') as f: spell_markdown = f.read()
                    level = extract_spell_level(spell_markdown)
                    if level < 2: continue 
                    
                    allowed_classes = extract_classes_from_markdown(spell_markdown)
                    char_class = random.choice(allowed_classes) if allowed_classes else "Wizard"
                    # Generate a profile and force it to Level 1
                    profile = generate_random_profile(allowed_classes=[char_class], spell_level=0)
                    profile = re.sub(r"Level \d+", "Level 1", profile)
                
                elif cat['category'] == "Upcasting Limits":
                    # Pick a spell level 1-8 (can't upcast 9, can't really upcast cantrips)
                    spell_path = random.choice(spell_files)
                    spell_name = os.path.basename(spell_path).replace(".md", "").title()
                    with open(spell_path, 'r') as f: spell_markdown = f.read()
                    level = extract_spell_level(spell_markdown)
                    if level == 0 or level >= 9: continue
                    
                    allowed_classes = extract_classes_from_markdown(spell_markdown)
                    char_class = random.choice(allowed_classes) if allowed_classes else "Wizard"
                    
                    # Calculate minimum level required to cast a spell of spell_level
                    if char_class in ["Bard", "Cleric", "Druid", "Sorcerer", "Warlock", "Wizard"]:
                        min_level = max(1, (level * 2) - 1)
                    elif char_class in ["Paladin", "Ranger"]:
                        min_level = (level * 4) - 3 if level > 1 else 2
                    elif char_class in ["Fighter", "Rogue"]:
                        min_level = (level * 6) - 5 if level > 1 else 3
                    else:
                        min_level = max(1, (level * 2) - 1)

                    # Generate profile and force it to the EXACT min_level
                    profile = generate_random_profile(allowed_classes=[char_class], spell_level=level)
                    profile = re.sub(r"Level \d+", f"Level {min_level}", profile)
                
                elif cat['category'] == "Class Restriction":
                    spell_path = random.choice(spell_files)
                    spell_name = os.path.basename(spell_path).replace(".md", "").title()
                    with open(spell_path, 'r') as f: spell_markdown = f.read()
                    allowed_classes = extract_classes_from_markdown(spell_markdown)
                    level = extract_spell_level(spell_markdown)
                    
                    all_classes = ["Barbarian", "Bard", "Cleric", "Druid", "Fighter", "Monk", "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard"]
                    # Pick a class that definitely doesn't have this spell
                    invalid_classes = [c for c in all_classes if c not in (allowed_classes or [])]
                    if not invalid_classes: continue
                    char_class = random.choice(invalid_classes)
                    
                    # Ensure the character level is high enough to cast *something* but doesn't have this spell
                    profile = generate_random_profile(allowed_classes=[char_class], spell_level=max(1, level))
                
                elif cat['category'] == "Non-existent Spell":
                    # For non-existent, LLM will invent a name
                    spell_name = "invented name"
                    profile = generate_random_profile()
                    spell_markdown = None

                qa_pairs = generate_refusal_batch(cat, spell_name, profile, spell_markdown, model, batch_size)
                
                for qa in qa_pairs:
                    entry = {
                        "category": cat['category'],
                        "text": f"<start_of_turn>user\n{profile}\n\n{qa['question']}<end_of_turn>\n<start_of_turn>model\n{qa['answer']}<end_of_turn>"
                    }
                    f_out.write(json.dumps(entry) + "\n")
                    generated += 1
                
                f_out.flush()
                time.sleep(1)

    print(f"\nFinished! Roll refusal data saved to {args.output_file}")

if __name__ == "__main__":
    main()
