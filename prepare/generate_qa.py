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
You are an expert Dungeon Master's companion and specialized D&D 5e (2024) rules assistant. Your goal is to generate high-quality, helpful, and comprehensive Question-Answer pairs from the provided D&D manual section.

--- INSTRUCTIONS ---
1. Generate EXACTLY 5-7 high-quality, diverse QA pairs. Prioritize depth and helpfulness over quantity.
2. Questions must be specific and represent real-world play scenarios (e.g., rules applications, tactical choices, class feature interactions).
3. ANSWERS MUST BE HELPFUL & COMPREHENSIVE: Do not just state the rule; provide the necessary context so a player or DM can apply it immediately without looking up further terms.
4. TARGET LENGTH: Each answer should be approximately 100-200 words. Explain the "why" if the text provides it.
5. SELF-CONTAINED: If a rule mentions a condition (like **Prone**) or a specific mechanic (like **Advantage**), briefly remind the user what that means if it's relevant to the answer.
6. NO META-TALK: Do not start answers with "According to the text," or "Based on the manual." Jump directly into the expert explanation.
7. TONE: Use a professional, authoritative, but warm and helpful "assistant" persona.
8. MARKDOWN: Use **bolding** for game mechanics, keywords, conditions, and specific ability scores.
9. TABLE HANDLING: If the info is from a table, recreate the relevant part of the table in Markdown or describe the data clearly with all necessary context.
10. DO NOT use outside knowledge; base answers ONLY on the provided text.
11. DO NOT reference page numbers or chapter titles.

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
        # Check for quota error
        if "429" in str(e) or "Resource exhausted" in str(e):
            raise e
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
    parser.add_argument("--prefix", type=str, default="", help="Prefix for the output files (e.g., 'spells_')")
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
    raw_file = os.path.join(args.output_dir, f"{args.prefix}raw_qa.jsonl")
    
    # Check for existing progress
    last_processed_idx = -1
    if os.path.exists(raw_file):
        print(f"Checking existing progress in {raw_file}...")
        with open(raw_file, 'r', encoding='utf-8') as f_raw:
            for line in f_raw:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if "chunk_idx" in data:
                            last_processed_idx = max(last_processed_idx, data["chunk_idx"])
                    except:
                        continue
        if last_processed_idx >= 0:
            print(f"Resuming from chunk {last_processed_idx + 1}")

    print(f"Generating Q&A. Progress saved to {raw_file}")
    
    with open(raw_file, 'a', encoding='utf-8') as f_raw:
        for idx, chunk in enumerate(tqdm(all_chunks)):
            if idx <= last_processed_idx:
                continue
            
            try:
                qa_pairs = generate_qa_pairs(chunk, model)
                if not qa_pairs:
                    print(f"\nNo QA pairs generated for chunk {idx}. Stopping to avoid skipping any data.")
                    return

                for qa in qa_pairs:
                    # Format for SFT training: Official Gemma Instruction format
                    entry = {
                        "chunk_idx": idx,
                        "text": f"<start_of_turn>user\n{qa['question']}<end_of_turn>\n<start_of_turn>model\n{qa['answer']}<end_of_turn>"
                    }
                    f_raw.write(json.dumps(entry) + "\n")
                
                f_raw.flush()
                # Rate limiting safety
                time.sleep(1) 
            except Exception as e:
                print(f"\nStopping due to error at chunk {idx}: {e}")
                print("Please resume the script later; progress has been saved.")
                return

    # 3. Read all, Shuffle and Split
    print("Finalizing dataset (shuffling and splitting)...")
    all_qa_entries = []
    with open(raw_file, 'r', encoding='utf-8') as f_raw:
        for line in f_raw:
            if line.strip():
                entry = json.loads(line)
                # Remove internal tracking index before saving final splits
                if "chunk_idx" in entry:
                    del entry["chunk_idx"]
                all_qa_entries.append(entry)

    random.seed(42)
    random.shuffle(all_qa_entries)
    
    split_idx = int(len(all_qa_entries) * args.split_ratio)
    train_qa = all_qa_entries[:split_idx]
    val_qa = all_qa_entries[split_idx:]

    # 4. Save results
    train_file = os.path.join(args.output_dir, f"{args.prefix}train_qa.jsonl")
    val_file = os.path.join(args.output_dir, f"{args.prefix}val_qa.jsonl")

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