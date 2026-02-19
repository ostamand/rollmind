import json
import os
import random
import argparse

def split_dataset(input_file, output_dir, split_ratio, prefix):
    """
    Reads a raw JSONL file, shuffles the entries, and splits them into train and validation sets.
    """
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found.")
        return

    print(f"Reading entries from {input_file}...")
    all_qa_entries = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    # Remove internal tracking index if present
                    if "chunk_idx" in entry:
                        del entry["chunk_idx"]
                    all_qa_entries.append(entry)
                except json.JSONDecodeError:
                    continue

    if not all_qa_entries:
        print("No valid entries found in the input file.")
        return

    print(f"Total entries found: {len(all_qa_entries)}")
    
    # Shuffle with a fixed seed for reproducibility
    random.seed(42)
    random.shuffle(all_qa_entries)
    
    split_idx = int(len(all_qa_entries) * split_ratio)
    train_qa = all_qa_entries[:split_idx]
    val_qa = all_qa_entries[split_idx:]

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    train_file = os.path.join(output_dir, f"{prefix}train_qa.jsonl")
    val_file = os.path.join(output_dir, f"{prefix}val_qa.jsonl")

    print(f"Saving {len(train_qa)} entries to {train_file}...")
    with open(train_file, 'w', encoding='utf-8') as f:
        for entry in train_qa:
            f.write(json.dumps(entry) + "\n")
            
    print(f"Saving {len(val_qa)} entries to {val_file}...")
    with open(val_file, 'w', encoding='utf-8') as f:
        for entry in val_qa:
            f.write(json.dumps(entry) + "\n")

    print("Successfully split the dataset.")

def main():
    parser = argparse.ArgumentParser(description="Split raw_qa.jsonl into train and validation sets.")
    parser.add_argument("--input_file", type=str, default="data/step2/raw_qa.jsonl", help="Path to the raw QA JSONL file")
    parser.add_argument("--output_dir", type=str, default="data/step2", help="Directory to save the splits")
    parser.add_argument("--split_ratio", type=float, default=0.9, help="Ratio for the training set (e.g., 0.9 for 90%% train)")
    parser.add_argument("--prefix", type=str, default="", help="Prefix for the output files")
    
    args = parser.parse_args()
    
    split_dataset(args.input_file, args.output_dir, args.split_ratio, args.prefix)

if __name__ == "__main__":
    main()
