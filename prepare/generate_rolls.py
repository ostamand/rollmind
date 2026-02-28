import json
import os
import time
import argparse
import random
import glob
from tqdm import tqdm
import vertexai
from vertexai.generative_models import GenerativeModel
from dotenv import load_dotenv
from prepare.utils import generate_random_profile, extract_classes_from_markdown, extract_spell_level

# Load environment variables from .env file if it exists
load_dotenv()

def generate_roll_examples(spell_name, spell_markdown, profile, model, max_retries=5):
    import re
    prompt = f"""
You are an expert Dungeon Master's companion. Your goal is to generate training data for a D&D 5e (2024) assistant that can calculate and output dice rolls using a custom [ROLL]XdY+Z[/ROLL] tag.

--- CONTEXT ---
{profile}

SPELL DATA:
{spell_markdown}

--- INSTRUCTIONS ---
1. Generate EXACTLY 3-4 natural conversation examples (User/Model pairs) for the spell "{spell_name}".
2. USER INPUT: The user should issue a direct command or action that EXPLICITLY includes the spell name "{spell_name}".
   - Use NATURAL CASING for the spell name (e.g., "{spell_name}" or "{spell_name.lower()}"). AVOID ALL CAPS.
   - Good: "I cast {spell_name} at 4th level", "Cast {spell_name} on the target", "I use {spell_name}!".
   - Avoid: "Attack with it", "Cast at level 3", "Blast them". The spell name MUST be present.
3. MODEL RESPONSE: The response MUST:
    - Briefly explain the reasoning/math (e.g., bonuses, DC, or upcasting logic) before the [ROLL] tag so the user understands the calculation.
    - Output the [ROLL] tag for the relevant check, save, attack, or damage.
    - DO NOT assume the result of the roll. Avoid phrases like "They fail", "It hits", or "The target is destroyed".
    - If a Save or Check is involved, state the DC and describe both what happens on a SUCCESS and a FAILURE.
    - Describe the effect using the flavor from the spell markdown.
    - Reference the provided Character Profile to calculate correct bonuses (DC, Attack, etc.).
    - IMPORTANT: The sentence MUST make sense when the [ROLL] tag is replaced by a number.
    - Example Good: "With your DC 16, the target must make a Wisdom save: [ROLL]1d20+2[/ROLL]. On a failure, they are Charmed for 8 hours; on a success, they suffer no effect."
4. MECHANICS:
    - Handle **Upcasting**: If the user casts at a higher level, the level MUST be reachable by the Character's Level (e.g., a Level 11 Wizard only has slots up to 6th level). Increment the dice as per the "At Higher Levels" section.
    - Handle **Cantrip Scaling**: For cantrips, use the character's level from the profile (jumps at level 5, 11, and 17).
    - Handle **Multiple Rolls**: Output separate [ROLL] tags for multiple beams (e.g., Eldritch Blast) or a single one for total damage where appropriate.
5. TONE: Immersive, helpful, and mechanically precise.
6. LENGTH: Keep each answer under 350 characters.
7. FORMAT: Output as a valid JSON list of objects.

Format:
[
  {{"question": "I cast {spell_name} at 4th level!", "answer": "Upcasting to 4th level adds 1d6. With your DC 15, the target takes [ROLL]9d6[/ROLL] fire damage, or half on a successful Dexterity save."}},
  ...
]
"""
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            content = response.text.strip()
            
            # Robust JSON extraction
            match = re.search(r"(\[.*\])", content, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
            
            return []
            
        except Exception as e:
            if "429" in str(e) or "Resource exhausted" in str(e):
                wait_time = (5 * (4 ** attempt)) + random.random()
                time.sleep(wait_time)
                continue
            if attempt == max_retries - 1:
                return []
    return []

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic roll training data using Vertex AI")
    parser.add_argument("--spells_dir", type=str, default="data/spells", help="Directory containing spell markdown files")
    parser.add_argument("--output_file", type=str, default="data/step2/v2/rolls/_A100_rolls.jsonl", help="Output JSONL file")
    parser.add_argument("--project", type=str, default=os.environ.get("GOOGLE_CLOUD_PROJECT"), help="Google Cloud Project ID")
    parser.add_argument("--location", type=str, default=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"), help="Google Cloud Region")
    parser.add_argument("--num_samples", type=int, default=100, help="Number of spell files to process")
    args = parser.parse_args()

    if not args.project:
        parser.error("The --project argument or GOOGLE_CLOUD_PROJECT environment variable is required.")

    vertexai.init(project=args.project, location=args.location)
    model = GenerativeModel("gemini-3-flash-preview")

    spell_files = glob.glob(os.path.join(args.spells_dir, "*.md"))
    if not spell_files:
        print(f"No spell files found in {args.spells_dir}")
        return

    random.shuffle(spell_files)
    selected_files = spell_files[:args.num_samples]

    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)

    print(f"Generating roll examples for {len(selected_files)} spells...")

    with open(args.output_file, 'w', encoding='utf-8') as f:
        for spell_path in tqdm(selected_files):
            # Normalize spell name to Title Case for more natural usage
            spell_name = os.path.basename(spell_path).replace(".md", "").title()
            
            with open(spell_path, 'r', encoding='utf-8') as sf:
                spell_markdown = sf.read()
            
            # Extract allowed classes and spell level from spell markdown
            allowed_classes = extract_classes_from_markdown(spell_markdown)
            spell_level = extract_spell_level(spell_markdown)
            
            # Generate 2 different profiles per spell to increase variance
            for _ in range(2):
                profile = generate_random_profile(allowed_classes=allowed_classes, spell_level=spell_level)
                examples = generate_roll_examples(spell_name, spell_markdown, profile, model)
                
                if not examples:
                    continue

                for ex in examples:
                    # The prompt must include the profile for the model to know how to respond at inference time
                    full_prompt = f"{profile}\n\n{ex['question']}"
                    entry = {
                        "text": f"<start_of_turn>user\n{full_prompt}<end_of_turn>\n<start_of_turn>model\n{ex['answer']}<end_of_turn>"
                    }
                    f.write(json.dumps(entry) + "\n")
                
                f.flush()
                time.sleep(1) # Small delay for rate limits

    print(f"Done! Generated examples saved to {args.output_file}")

if __name__ == "__main__":
    main()
