import json
import argparse
import os
from transformers import AutoTokenizer

def check_lengths(file_path, model_id="google/gemma-7b-it"):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    print(f"Loading tokenizer for {model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    
    max_tokens = 0
    total_samples = 0
    
    print(f"Analyzing {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            
            try:
                data = json.loads(line)
                text = data.get("text", "")
                
                # Tokenize and get length
                tokens = tokenizer.encode(text, add_special_tokens=True)
                token_count = len(tokens)
                
                if token_count > max_tokens:
                    max_tokens = token_count
                
                total_samples += 1
            except Exception as e:
                print(f"Error parsing line: {e}")

    print("\n" + "="*30)
    print(f"Dataset Analysis Results")
    print("="*30)
    print(f"Total samples:    {total_samples}")
    print(f"Max token length: {max_tokens}")
    print("="*30)
    
    if max_tokens > 1024:
        print(f"\nWARNING: Your longest sample ({max_tokens} tokens) exceeds the standard max_seq_length (1024).")
        print("It will be truncated during training unless you increase the limit.")
    else:
        print(f"\nSUCCESS: The standard max_seq_length (1024) is sufficient for this dataset.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check max token length of a JSONL dataset.")
    parser.add_argument("--file", type=str, default="data/step2/train_qa.jsonl", help="Path to JSONL file")
    parser.add_argument("--model", type=str, default="google/gemma-7b-it", help="Model ID for tokenizer")
    
    args = parser.parse_args()
    check_lengths(args.file, args.model)
