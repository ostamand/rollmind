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
from prepare.utils import generate_random_profile

# Load environment variables from .env file if it exists
load_dotenv()

def generate_qa_pairs(text, model, max_retries=5):
    import re
    prompt = f"""
You are an expert Dungeon Master's companion and specialized D&D 5e (2024) rules assistant. Your goal is to generate high-quality, helpful Question-Answer pairs that a player would actually ask during a game session or while managing their character.

--- INSTRUCTIONS ---
1. Generate EXACTLY 5-7 QA pairs. 
2. QUESTIONS (The "Player" side): Must be direct, practical, and representative of a player at the table or leveling a character. 
   - NO BOOK-ISMS: Do not reference "Steps", "Tables", "Chapters", "Sections", "Pages", or "The Manual" in the question.
   - CONCEPT-FOCUSED: Ask about the game mechanic or concept directly (e.g., instead of "How do I use the Step 3 table?", use "How do my ability scores affect my character's appearance?").
   - Examples: "How do I calculate my AC with this armor?", "What roll do I make to grapple?", "What happens to my character if I'm Prone?", "What is the range of this spell?".
3. ANSWERS (The "Assistant" side): MUST BE HELPFUL & COMPREHENSIVE. Provide the rule clearly, but also include the necessary context so the player understands *how* to use it immediately.
4. TARGET LENGTH: Each answer should be approximately 80-150 words. Explain the "why" or "how" to provide full context.
5. COMMON PITFALLS: If the rule or mechanic has a frequent point of confusion (e.g., Invisibility vs. Being Hidden, or how Concentration works with multiple spells), briefly clarify it in the answer. ONLY do this if there is a genuine, common mistake to address.
6. NO META-TALK: Jump directly into the expert explanation. Avoid phrases like "According to the text provided" or "Based on the rules".
7. TONE: Professional, authoritative, and helpful.
8. MARKDOWN: Use **bolding** for game mechanics, keywords, conditions, and ability scores.
9. SOURCE FIDELITY: Base all questions and answers ONLY on the provided TEXT SECTION. Do not use external knowledge or rules from previous D&D editions. If the text is insufficient to answer a generated question, discard that question.

Format the output as a valid JSON list of objects:
[
  {{"question": "...", "answer": "..."}},
  ...
]

TEXT SECTION:
{text}
"""
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            content = response.text.strip()
            
            # More robust JSON extraction using regex to find the first [ and last ]
            match = re.search(r"(\[.*\])", content, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
            
            # Fallback to the old method if regex fails
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
        except (json.JSONDecodeError, Exception) as e:
            # Handle rate limits
            if "429" in str(e) or "Resource exhausted" in str(e):
                if attempt < max_retries - 1:
                    # More aggressive backoff: 5, 20, 80, 320 seconds...
                    wait_time = (5 * (4 ** attempt)) + random.random()
                    print(f"\n⚠️ Rate limit hit. Retrying in {wait_time:.2f}s (Attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
            
            # Handle JSON errors or other transient issues by retrying
            if isinstance(e, json.JSONDecodeError):
                if attempt < max_retries - 1:
                    print(f"\n⚠️ JSON Parse Error. Retrying (Attempt {attempt + 1}/{max_retries})...")
                    time.sleep(1)
                    continue
            
            # If it's the last attempt or a different error
            if attempt == max_retries - 1:
                print(f"Error generating QA after {max_retries} attempts: {e}")
                return []
    return []

def main():
    parser = argparse.ArgumentParser(description="Generate Q&A pairs using Vertex AI Gemini")
    parser.add_argument("--input_file", type=str, default="data/step1/full_chunks.jsonl", help="Input JSONL chunks file")
    parser.add_argument("--output_dir", type=str, default="data/step2/v2/qa", help="Directory to save output QA files")
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
                    profile = generate_random_profile()
                    # Format for SFT training: Official Gemma Instruction format
                    entry = {
                        "chunk_idx": idx,
                        "text": f"<start_of_turn>user\n{profile}\n\n{qa['question']}<end_of_turn>\n<start_of_turn>model\n{qa['answer']}<end_of_turn>"
                    }
                    f_raw.write(json.dumps(entry) + "\n")
                
                f_raw.flush()
                # 2-second delay is usually enough for Gemini 1.5 Flash
                time.sleep(2) 
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
