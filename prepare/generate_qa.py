import json
import os
import time
import argparse
from tqdm import tqdm
import google.generativeai as genai

def generate_qa_pairs(text, model):
    prompt = f"""
I am fine-tuning a language model on a D&D manual. 
Given the following section of the manual, generate 3 diverse and highly accurate Question-Answer pairs. 
The questions should be specific and the answers should be based ONLY on the provided text.

Format the output as a valid JSON list of objects, like this:
[
  {{"question": "What is...", "answer": "..."}},
  ...
]

TEXT:
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
    parser = argparse.ArgumentParser(description="Generate Q&A pairs using Gemini API")
    parser.add_argument("--input_file", type=str, default="data/train_chunks.jsonl", help="Input chunks file")
    parser.add_argument("--output_file", type=str, default="data/train_qa.jsonl", help="Output Q&A file")
    parser.add_argument("--api_key", type=str, required=True, help="Gemini API Key")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of chunks to process (for testing)")
    args = parser.parse_args()

    genai.configure(api_key=args.api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    with open(args.input_file, 'r', encoding='utf-8') as f:
        chunks = [json.loads(line)["text"] for line in f]

    if args.limit:
        chunks = chunks[:args.limit]

    print(f"Generating Q&A for {len(chunks)} chunks...")
    
    with open(args.output_file, 'w', encoding='utf-8') as f:
        for chunk in tqdm(chunks):
            qa_pairs = generate_qa_pairs(chunk, model)
            for qa in qa_pairs:
                # Format for SFT training: Official Gemma Instruction format
                entry = {
                    "text": f"<start_of_turn>user\n{qa['question']}<end_of_turn>\n<start_of_turn>model\n{qa['answer']}<end_of_turn>"
                }
                f.write(json.dumps(entry) + "\n")
            
            # Rate limiting safety for free tier
            time.sleep(2) 

    print(f"Done! Saved to {args.output_file}")

if __name__ == "__main__":
    main()