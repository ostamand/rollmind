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
        "description": "Focus on what changes on the character sheet, new abilities, and choices to be made at specific levels (e.g., Level 2, Level 3 subclasses, Level 4 feats).",
        "files": [
            "data/player-handbook-2024/2_player-handbook-2024-chapter2.md",
            "data/player-handbook-2024/3_player-handbook-2024-chapter3.md"
        ]
    },
    {
        "name": "Character Creation",
        "persona": "A new player creating their first character.",
        "description": "Focus on the step-by-step process, combining class, background, and species. Ask about ability scores, starting equipment, and origin traits.",
        "files": [
            "data/player-handbook-2024/2_player-handbook-2024-chapter2.md",
            "data/player-handbook-2024/4_player-handbook-2024-chapter4.md"
        ]
    },
    {
        "name": "Combat & Action Economy",
        "persona": "A player in the middle of a complex combat encounter.",
        "description": "Focus on what can be done on a turn: Actions, Bonus Actions, Reactions, and Movement. Ask about specific class features like Cunning Action or Action Surge in the context of a turn.",
        "files": [
            "data/player-handbook-2024/1_player-handbook-2024-chapter1.md",
            "data/player-handbook-2024/3_player-handbook-2024-chapter3.md"
        ]
    },
    {
        "name": "Multiclassing",
        "persona": "An experienced player looking to multiclass.",
        "description": "Focus on prerequisites, what proficiencies are gained/lost, and how spellcasting slots work when combining classes.",
        "files": [
            "data/player-handbook-2024/2_player-handbook-2024-chapter2.md",
            "data/player-handbook-2024/3_player-handbook-2024-chapter3.md"
        ]
    }
]

def generate_scenario_qa(scenario, context_text, model, num_pairs=15):
    prompt = f"""
You are an expert D&D 5e (2024) assistant helping a player.
PLAYER PERSONA: {scenario['persona']}
SCENARIO DESCRIPTION: {scenario['description']}

--- INSTRUCTIONS ---
1. Generate EXACTLY {num_pairs} diverse QA pairs that this specific player would ask in this scenario.
2. The questions should feel natural and "high-level" (e.g., "I just hit level 2, what do I add to my sheet?" rather than "What does the level 2 table say?").
3. ANSWERS MUST BE CONCISE, authoritative, and include specific mechanics from the provided text.
4. Use **bolding** for game mechanics, keywords, and ability scores.
5. NO META-TALK: Jump directly into the answer.
6. DO NOT use outside knowledge; base answers ONLY on the provided text.
7. Use the official Gemma template format for the final output.

Format the output as a valid JSON list of objects:
[
  {{"question": "...", "answer": "..."}},
  ...
]

RELEVANT RULES & TEXT:
{context_text}
"""
    try:
        # Use a higher token limit for long context
        response = model.generate_content(prompt)
        content = response.text.strip()
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"Error generating Scenario QA for {scenario['name']}: {e}")
        return []

def read_file_content(file_path):
    # Simplified read for the script
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    parser = argparse.ArgumentParser(description="Generate Scenario-based Q&A pairs using Vertex AI")
    parser.add_argument("--output_file", type=str, default="data/step2/scenario_qa.jsonl", help="Output JSONL file")
    parser.add_argument("--project", type=str, default=os.environ.get("GOOGLE_CLOUD_PROJECT"), help="Google Cloud Project ID")
    parser.add_argument("--location", type=str, default=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"), help="Google Cloud Region")
    parser.add_argument("--pairs_per_scenario", type=int, default=20, help="Number of QA pairs per scenario")
    args = parser.parse_args()

    if not args.project:
        parser.error("The --project argument or GOOGLE_CLOUD_PROJECT environment variable is required.")

    vertexai.init(project=args.project, location=args.location)
    # Using gemini-1.5-flash for larger context window and better reasoning
    model = GenerativeModel("gemini-1.5-flash")

    print(f"Generating Scenario-based Q&A for {len(SCENARIOS)} scenarios...")
    
    with open(args.output_file, 'w', encoding='utf-8') as f_out:
        for scenario in SCENARIOS:
            print(f"Processing Scenario: {scenario['name']}...")
            
            # Combine text from all relevant files
            context_text = ""
            for file_path in scenario['files']:
                if os.path.exists(file_path):
                    context_text += f"

--- DOCUMENT: {os.path.basename(file_path)} ---
"
                    context_text += read_file_content(file_path)
            
            # Limit context if it's too huge, though gemini-1.5-flash should handle it.
            # For this prototype, we'll take the first 100k characters if exceeded.
            if len(context_text) > 100000:
                context_text = context_text[:100000] + "... [TRUNCATED]"

            qa_pairs = generate_scenario_qa(scenario, context_text, model, num_pairs=args.pairs_per_scenario)
            
            for qa in qa_pairs:
                entry = {
                    "scenario": scenario['name'],
                    "text": f"<start_of_turn>user
{qa['question']}<end_of_turn>
<start_of_turn>model
{qa['answer']}<end_of_turn>"
                }
                f_out.write(json.dumps(entry) + "
")
            
            print(f"Generated {len(qa_pairs)} pairs for {scenario['name']}.")
            time.sleep(2) # Rate limiting

    print(f"Done! Saved scenario Q&A to {args.output_file}")

if __name__ == "__main__":
    main()
