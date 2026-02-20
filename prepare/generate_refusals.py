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

# DATASET MIX STRATEGY (Comment for Training)
# ---------------------------------------------------------
# For optimal "Oracle" behavior, mix this refusal data into your Step 2 
# (Instruction Tuning) dataset. A recommended ratio is:
# - 85-90% Valid D&D 2024 Q&A (from generate_qa.py and generate_scenarios.py)
# - 10-15% Refusal Data (from this script)
# This ensures the model remains helpful for D&D but firm on its boundaries.
# ---------------------------------------------------------

REFUSAL_CATEGORIES = [
    {
        "category": "Self-Identity",
        "examples": "Who are you? Who created you? What is your purpose? What books do you know? Are you a GPT?"
    },
    {
        "category": "General Real-World Knowledge",
        "examples": "Cooking, science, history, current events, celebrities, geography."
    },
    {
        "category": "Technical & Coding",
        "examples": "Python scripts, web development, hardware troubleshooting, math formulas."
    },
    {
        "category": "Other TTRPGs",
        "examples": "Pathfinder, Starfinder, Call of Cthulhu, Vampire: The Masquerade."
    },
    {
        "category": "Older D&D Editions (2014)",
        "examples": "Asking about the 2014 version of Great Weapon Master, or 2014 Druid Wild Shape rules."
    },
    {
        "category": "Meta-Talk & Personal",
        "examples": "Asking the model for its opinion, its name, its creator, or to tell a joke."
    }
]

ORACLE_REFUSAL_MESSAGE = "I am RollMind, created by Olivier St-Amand. My knowledge is dedicated specifically to the 2024 D&D Player's Handbook, and I cannot assist with inquiries outside of this domain."

def generate_refusal_batch(category_info, model, num_pairs=10):
    if category_info['category'] == "Self-Identity":
        prompt = f"""
You are helping to train a D&D 2024 specialized AI called "RollMind".
Generate {num_pairs} Q&A pairs where the user asks about the model's identity, creator, purpose, or knowledge source.

--- KEY FACTS TO INCLUDE ---
- NAME: RollMind
- CREATOR: Olivier St-Amand
- PURPOSE: Specialized assistant for D&D 2024 rules.
- KNOWLEDGE SOURCE: Specifically the 2024 Player's Handbook.

Format as a valid JSON list of objects:
[
  {{"question": "Who created you?", "answer": "I am RollMind, created by Olivier St-Amand to serve as a specialized guide for D&D 2024 rules."}},
  ...
]
"""
    else:
        prompt = f"""
You are helping to train a D&D 2024 specialized AI called "RollMind".
Your goal is to generate {num_pairs} diverse questions that are OUTSIDE the scope of D&D 2024 rules.

CATEGORY: {category_info['category']}
EXAMPES: {category_info['examples']}

--- INSTRUCTIONS ---
1. Generate EXACTLY {num_pairs} diverse and realistic user questions for this category.
2. The questions should sound like something a user might mistakenly or intentionally ask a D&D assistant.
3. For each question, provide the STANDARD REFUSAL MESSAGE:
   "{ORACLE_REFUSAL_MESSAGE}"

Format as a valid JSON list of objects:
[
  {{"question": "...", "answer": "{ORACLE_REFUSAL_MESSAGE}"}},
  ...
]
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
        print(f"Error generating batch for {category_info['category']}: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Generate Out-of-Domain Refusal Dataset")
    parser.add_argument("--output_file", type=str, default="data/step2/refusals.jsonl", help="Output JSONL file")
    parser.add_argument("--project", type=str, default=os.environ.get("GOOGLE_CLOUD_PROJECT"), help="GCP Project ID")
    parser.add_argument("--location", type=str, default=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"), help="GCP Region")
    parser.add_argument("--total_pairs", type=int, default=150, help="Total refusal pairs to generate")
    args = parser.parse_args()

    if not args.project:
        parser.error("The --project argument or GOOGLE_CLOUD_PROJECT environment variable is required.")

    vertexai.init(project=args.project, location=args.location)
    model = GenerativeModel("gemini-3-flash-preview")

    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)

    pairs_per_category = args.total_pairs // len(REFUSAL_CATEGORIES)
    batch_size = 10

    print(f"Generating {args.total_pairs} refusal pairs across {len(REFUSAL_CATEGORIES)} categories...")

    with open(args.output_file, 'w', encoding='utf-8') as f_out:
        for cat in REFUSAL_CATEGORIES:
            print(f"\n>>> Category: {cat['category']}")
            num_batches = (pairs_per_category + batch_size - 1) // batch_size
            
            for i in range(num_batches):
                print(f"  Batch {i+1}/{num_batches}...")
                qa_pairs = generate_refusal_batch(cat, model, batch_size)
                
                for qa in qa_pairs:
                    # Format for SFT training: Official Gemma Instruction format
                    entry = {
                        "category": cat['category'],
                        "text": f"<start_of_turn>user\n{qa['question']}<end_of_turn>\n<start_of_turn>model\n{qa['answer']}<end_of_turn>"
                    }
                    f_out.write(json.dumps(entry) + "\n")
                
                f_out.flush()
                time.sleep(2)

    print(f"\nFinished! Refusal data saved to {args.output_file}")

if __name__ == "__main__":
    main()
