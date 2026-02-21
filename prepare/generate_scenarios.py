import json
import os
import time
import argparse
import random
from tqdm import tqdm
import vertexai
from vertexai.generative_models import GenerativeModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SCENARIOS = [
    {
        "name": "Leveling Up",
        "persona": "A D&D player whose character just leveled up.",
        "description": "Focus on changes to the character sheet, new abilities, and choices at specific levels (Level 2, subclasses at Level 3, feats at Level 4).",
        "files": ["data/player-handbook-2024/2_player-handbook-2024-chapter2.md", "data/player-handbook-2024/3_player-handbook-2024-chapter3.md"]
    },
    {
        "name": "Character Creation",
        "persona": "A new player creating their first character.",
        "description": "Focus on the step-by-step process: combining class, background, and species. Ask about ability scores and starting equipment.",
        "files": ["data/player-handbook-2024/2_player-handbook-2024-chapter2.md", "data/player-handbook-2024/4_player-handbook-2024-chapter4.md"]
    },
    {
        "name": "Combat & Action Economy",
        "persona": "A player in the middle of a complex combat encounter.",
        "description": "Focus on Actions, Bonus Actions, Reactions, and Movement. Ask about specific features like Cunning Action or Action Surge.",
        "files": ["data/player-handbook-2024/1_player-handbook-2024-chapter1.md", "data/player-handbook-2024/3_player-handbook-2024-chapter3.md"]
    },
    {
        "name": "Conditions & Tactical Combat",
        "persona": "A player dealing with status effects and tactical positioning.",
        "description": "Focus on conditions (Prone, Grappled, Restrained), Cover rules, and Death Saving Throws. Ask about how to end conditions.",
        "files": ["data/player-handbook-2024/1_player-handbook-2024-chapter1.md"]
    },
    {
        "name": "Multiclassing",
        "persona": "An experienced player looking to multiclass.",
        "description": "Focus on prerequisites, proficiencies gained/lost, and spellcasting slot math when combining classes.",
        "files": ["data/player-handbook-2024/2_player-handbook-2024-chapter2.md", "data/player-handbook-2024/3_player-handbook-2024-chapter3.md"]
    },
    {
        "name": "Preparing & Managing Spells",
        "persona": "A spellcaster managing their daily list.",
        "description": "Focus on preparing spells, ritual rules, and how spell slots are consumed. Ask about the 'Prepared' vs 'Known' distinction.",
        "files": ["data/player-handbook-2024/7_player-handbook-2024-chapter7.md"]
    },
    {
        "name": "Social Interaction & Skills",
        "persona": "A player in a non-combat roleplay scenario.",
        "description": "Focus on Skill Checks (Persuasion, Insight, Deception), the Influence action, and how Ability Checks work in social contexts.",
        "files": ["data/player-handbook-2024/1_player-handbook-2024-chapter1.md"]
    },
    {
        "name": "Resting & Recovery",
        "persona": "A party at the end of an adventuring day.",
        "description": "Focus on Short Rests, Long Rests, Hit Dice usage, and what resources reset (e.g., Spell Slots, class features).",
        "files": ["data/player-handbook-2024/1_player-handbook-2024-chapter1.md"]
    },
    {
        "name": "The Attack Roll & Damage",
        "persona": "A player about to make their first attack in a session.",
        "description": "Focus on the math of the Attack Roll (d20 + modifier + proficiency), Critical Hits (natural 20), and how Damage is calculated (die + modifier). Mention damage types, Resistance, and Vulnerability.",
        "files": ["data/player-handbook-2024/1_player-handbook-2024-chapter1.md", "data/player-handbook-2024/6_player-handbook-2024-chapter6.md"]
    },
    {
        "name": "Defending & Saving Throws",
        "persona": "A player whose character is being targeted by an attack or a spell.",
        "description": "Focus on Armor Class (AC), the benefit of Shields, and the different types of Saving Throws to resist effects. Mention the Dodge action.",
        "files": ["data/player-handbook-2024/1_player-handbook-2024-chapter1.md", "data/player-handbook-2024/2_player-handbook-2024-chapter2.md"]
    },
    {
        "name": "Special Combat Maneuvers",
        "persona": "A tactical player looking for options beyond just standard attacks.",
        "description": "Focus on Grappling, Shoving, Opportunity Attacks, and the Disengage and Dash actions. Mention the Help action in combat.",
        "files": ["data/player-handbook-2024/1_player-handbook-2024-chapter1.md"]
    },
    {
        "name": "Casting Spells in Combat",
        "persona": "A spellcaster in the heat of battle.",
        "description": "Focus on the Magic action, Spell Attack Rolls, Area of Effect (AoE) shapes, and Concentration rules when taking damage.",
        "files": ["data/player-handbook-2024/7_player-handbook-2024-chapter7.md", "data/player-handbook-2024/1_player-handbook-2024-chapter1.md"]
    },
    {
        "name": "Weapon Mastery",
        "persona": "A martial character (Fighter, Barbarian, etc.) optimizing their weapon choice.",
        "description": "Focus on the new Mastery properties like Cleave, Topple, Nick, and Vex. Explain how many masteries a character can have and how to use them during an Attack action.",
        "files": ["data/player-handbook-2024/6_player-handbook-2024-chapter6.md"]
    },
    {
        "name": "Stealth & Hidden",
        "persona": "A Rogue or Ranger attempting to remain unseen.",
        "description": "Focus on the new Hidden condition rules. Explain the Hide action, the required Stealth check DC, and how being Hidden grants Advantage on attacks and makes you harder to target.",
        "files": ["data/player-handbook-2024/1_player-handbook-2024-chapter1.md"]
    },
    {
        "name": "Crafting & Tools",
        "persona": "A character wanting to use their downtime to create items.",
        "description": "Focus on the new 2024 Crafting rules, including gold costs and time requirements. Mention the benefit of having both Tool and Skill proficiency (which now grants Advantage on the check).",
        "files": ["data/player-handbook-2024/6_player-handbook-2024-chapter6.md"]
    },
    {
        "name": "Magic Items & Attunement",
        "persona": "A character who just found a powerful magic item.",
        "description": "Focus on how to Identify items using the Study action and the rules for Attunement (limit of 3 items, requirements for a Short Rest to attune).",
        "files": ["data/player-handbook-2024/6_player-handbook-2024-chapter6.md"]
    },
    {
        "name": "Class Features & Level Reference",
        "persona": "A player checking their character's current capabilities at a specific level.",
        "description": "Focus on summarizing what a specific class (e.g., Fighter, Rogue, Wizard) has at a specific level. Mention core features (e.g., Sneak Attack, Action Surge, Spellcasting), saving throw proficiencies, weapon/armor training, and spell slot totals.",
        "files": ["data/player-handbook-2024/3_player-handbook-2024-chapter3.md"]
    }
]

def generate_scenario_qa(scenario, context_text, model, num_pairs=10, iteration=1):
    prompt = f"""
You are an expert Dungeon Master's companion and specialized D&D 5e (2024) rules assistant. 
Your goal is to provide helpful, comprehensive, and authoritative guidance based on specific player scenarios.

PLAYER PERSONA: {scenario['persona']}
SCENARIO DESCRIPTION: {scenario['description']}
BATCH: {iteration}

--- INSTRUCTIONS ---
1. Generate EXACTLY {num_pairs} unique and high-quality QA pairs.
2. Questions should reflect the thoughts, confusion, or tactical needs of the PLAYER PERSONA in this SCENARIO.
3. ANSWERS MUST BE HELPFUL & COMPREHENSIVE: Do not just state the rule; provide the context and "why" so the player understands the mechanic fully.
4. TARGET LENGTH: Each answer should be approximately 100-200 words.
5. SELF-CONTAINED: If a rule involves a condition (e.g., **Incapacitated**) or a mechanic (e.g., **Saving Throws**), briefly explain how it applies to the current answer.
6. MARKDOWN: Use **bolding** for game mechanics, keywords, conditions, and ability scores.
7. NO META-TALK: Jump directly into the expert explanation. Do not say "Based on the text..."
8. REFUSAL: Use ONLY the provided text. If the answer isn't there, omit that specific QA pair.
9. TONE: Professional, authoritative, yet warm and helpful—like an expert DM assisting a friend.

Format as a valid JSON list of objects:
[
  {{"question": "...", "answer": "..."}},
  ...
]

RELEVANT RULES & TEXT:
{context_text}
"""
    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"Error in Scenario {scenario['name']} Batch {iteration}: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Generate Scenario-based Q&A pairs")
    parser.add_argument("--output_dir", type=str, default="data/step2/scenarios", help="Output directory for individual scenario files")
    parser.add_argument("--project", type=str, default=os.environ.get("GOOGLE_CLOUD_PROJECT"), help="GCP Project ID")
    parser.add_argument("--location", type=str, default=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"), help="GCP Region")
    parser.add_argument("--total_per_scenario", type=int, default=50, help="Total pairs per scenario")
    parser.add_argument("--batch_size", type=int, default=10, help="Pairs per API call")
    parser.add_argument("--scenario", type=str, default=None, help="Optional: Name of a specific scenario to run")
    args = parser.parse_args()

    if not args.project:
        parser.error("The --project argument or GOOGLE_CLOUD_PROJECT environment variable is required.")

    vertexai.init(project=args.project, location=args.location)
    model = GenerativeModel("gemini-3-flash-preview")

    os.makedirs(args.output_dir, exist_ok=True)

    target_scenarios = SCENARIOS
    if args.scenario:
        target_scenarios = [s for s in SCENARIOS if s["name"].lower() == args.scenario.lower()]
        if not target_scenarios:
            print(f"Error: Scenario '{args.scenario}' not found in the SCENARIOS list.")
            return

    for scenario in target_scenarios:
        print(f"\n>>> Scenario: {scenario['name']}")
        
        # Scenario-specific file path
        safe_name = scenario['name'].replace(" ", "_").replace("&", "and")
        scenario_file = os.path.join(args.output_dir, f"{safe_name}.jsonl")
        
        # Resume Logic: Check which batches exist in this specific file
        completed_batches = set()
        if os.path.exists(scenario_file):
            with open(scenario_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        completed_batches.add(data.get("batch_idx"))
                    except: continue

        context_text = ""
        for file_path in scenario['files']:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f: context_text += f"\n{f.read()}"
        
        if len(context_text) > 150000: context_text = context_text[:150000]

        num_batches = (args.total_per_scenario + args.batch_size - 1) // args.batch_size
        
        with open(scenario_file, 'a', encoding='utf-8') as f_out:
            for i in range(num_batches):
                if i in completed_batches:
                    continue # Skip already completed batches for this file
                
                print(f"  Batch {i+1}/{num_batches}...")
                qa_pairs = generate_scenario_qa(scenario, context_text, model, args.batch_size, i)
                
                for qa in qa_pairs:
                    entry = {
                        "scenario": scenario['name'],
                        "batch_idx": i,
                        "text": f"<start_of_turn>user\n{qa['question']}<end_of_turn>\n<start_of_turn>model\n{qa['answer']}<end_of_turn>"
                    }
                    f_out.write(json.dumps(entry) + "\n")
                
                f_out.flush()
                time.sleep(2)

    print(f"\nFinished! Files are located in {args.output_dir}")

if __name__ == "__main__":
    main()
