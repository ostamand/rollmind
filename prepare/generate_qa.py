import json
import os
import time
import argparse
import glob
import random
from tqdm import tqdm
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

def generate_qa_pairs(text, model):
    prompt = f"""
You are an expert D&D 5e (2024) content creator. Your task is to generate high-quality, diverse Question-Answer pairs from the provided D&D manual section.

--- INSTRUCTIONS ---
1. Generate EXACTLY 10 diverse QA pairs.
2. Questions must be specific and varied (e.g., asking about rules, costs, class features, or "how-to" scenarios).
3. ANSWERS MUST BE CONCISE but include enough context for clarity.
4. NO META-TALK: Do not start answers with "According to the text," "Based on the manual," or "The provided section states." Jump directly into the rule.
5. MARKDOWN: Use **bolding** for game mechanics, keywords, conditions (e.g., **Prone**, **Grappled**), and specific ability scores (e.g., **Strength**).
6. TABLE HANDLING: If the information comes from a table, the answer MUST include the relevant column headers and the specific row data to ensure the context is preserved.
7. OPTIONS & CHOICES: If a rule involves a choice (e.g., "choose two of the following..."), ensure the answer mentions that a choice is required.
8. DO NOT use outside knowledge; base answers ONLY on the provided text.
9. DO NOT reference chapter numbers, section titles, or page numbers. 
10. Use a professional, authoritative, and helpful tone.

Format the output as a valid JSON list of objects:
[
  {{"question": "...", "answer": "..."}},
  ...
]

TEXT SECTION:
{text}
"""
    try:
        response = model.generate_content(prompt)
        # Extract JSON from response (handling potential markdown formatting)
        content = response.text.strip()
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"Error generating QA: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Generate Q&A pairs using Vertex AI Gemini")
    parser.add_argument("--input_file", type=str, default="data/step1/full_chunks.jsonl", help="Input JSONL chunks file")
    parser.add_argument("--output_dir", type=str, default="data/step2", help="Directory to save output QA files")
    parser.add_argument("--project", type=str, default=os.environ.get("GOOGLE_CLOUD_PROJECT"), help="Google Cloud Project ID")
    parser.add_argument("--location", type=str, default=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"), help="Google Cloud Region")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of chunks to process (for testing)")
    parser.add_argument("--split_ratio", type=float, default=0.9, help="Ratio of train vs val split")
    args = parser.parse_args()

    if not args.project:
        parser.error("The --project argument or GOOGLE_CLOUD_PROJECT environment variable is required.")

    os.makedirs(args.output_dir, exist_ok=True)

    vertexai.init(project=args.project, location=args.location)
    model = GenerativeModel("gemini-3-flash-preview")

    # 1. Collect all chunks from the specified input_file
    print(f"Reading chunks from {args.input_file}")
    
    all_chunks = []
    with open(args.input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                all_chunks.append(json.loads(line)["text"])

    if args.limit:
        all_chunks = all_chunks[:args.limit]

    print(f"Generating Q&A for {len(all_chunks)} total chunks using Vertex AI...")
    
    # 2. Generate QA pairs
    all_qa_entries = []
    for chunk in tqdm(all_chunks):
        qa_pairs = generate_qa_pairs(chunk, model)
        for qa in qa_pairs:
            # Format for SFT training: Official Gemma Instruction format
            entry = {
                "text": f"<start_of_turn>user\n{qa['question']}<end_of_turn>\n<start_of_turn>model\n{qa['answer']}<end_of_turn>"
            }
            all_qa_entries.append(entry)
        
        # Rate limiting safety
        time.sleep(1) 

    # 3. Shuffle and Split
    random.seed(42)
    random.shuffle(all_qa_entries)
    
    split_idx = int(len(all_qa_entries) * args.split_ratio)
    train_qa = all_qa_entries[:split_idx]
    val_qa = all_qa_entries[split_idx:]

    # 4. Save results
    train_file = os.path.join(args.output_dir, "train_qa.jsonl")
    val_file = os.path.join(args.output_dir, "val_qa.jsonl")

    with open(train_file, 'w', encoding='utf-8') as f:
        for entry in train_qa:
            f.write(json.dumps(entry) + "\n")
            
    with open(val_file, 'w', encoding='utf-8') as f:
        for entry in val_qa:
            f.write(json.dumps(entry) + "\n")

    print(f"Done! Saved {len(train_qa)} train pairs to {train_file}")
    print(f"Saved {len(val_qa)} val pairs to {val_file}")

if __name__ == "__main__":
    main()