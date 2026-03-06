import os
import json
import random
import argparse
import re
from glob import glob
from collections import defaultdict

def get_sampling_percentage(filename):
    """Extracts X from _AX_ prefix in filename."""
    basename = os.path.basename(filename)
    match = re.search(r'^_A(\d+)_', basename)
    if match:
        return int(match.group(1))
    return None

def main():
    parser = argparse.ArgumentParser(description="Aggregate and downsample Step 2 data based on _AX_ prefixes.")
    parser.add_argument("--input_dir", type=str, default="data/step2/v2", help="Directory to search for source JSONL files")
    parser.add_argument("--output_dir", type=str, default="data/step2/v2", help="Directory to save output files")
    parser.add_argument("--val_ratio", type=float, default=0.1, help="Ratio of validation data (default: 0.1)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)
    
    os.makedirs(args.output_dir, exist_ok=True)

    # 1. Find all relevant JSONL files recursively
    pattern = os.path.join(args.input_dir, "**", "*.jsonl")
    all_files = glob(pattern, recursive=True)
    
    source_files = []
    for f in all_files:
        percentage = get_sampling_percentage(f)
        if percentage is not None:
            source_files.append((f, percentage))

    if not source_files:
        print(f"No files found matching the pattern _AX_*.jsonl in {args.input_dir}")
        return

    print(f"Found {len(source_files)} matching files.")

    all_train = []
    all_val = []
    all_raw = []
    
    # Track stats by folder
    folder_stats = defaultdict(lambda: {
        "total_raw": 0,
        "sampled": 0,
        "train": 0,
        "val": 0,
        "files": []
    })

    # 2. Process each file
    for file_path, percentage in source_files:
        # Determine relative parent folder path for grouping
        rel_folder = os.path.relpath(os.path.dirname(file_path), args.input_dir)
        folder_key = rel_folder if rel_folder != "." else "root"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            valid_lines = []
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if "text" in data:
                            # Only keep the text field
                            valid_lines.append(json.dumps({"text": data["text"]}))
                    except:
                        continue
        
        total_in_file = len(valid_lines)
        if percentage >= 100:
            sampled_lines = valid_lines
        else:
            num_to_sample = int(total_in_file * (percentage / 100.0))
            sampled_lines = random.sample(valid_lines, num_to_sample)
        
        # Stratified Split for this file
        random.shuffle(sampled_lines)
        val_size = int(len(sampled_lines) * args.val_ratio)
        # Ensure at least 1 sample in val if the file is not empty and ratio > 0
        if val_size == 0 and len(sampled_lines) > 0 and args.val_ratio > 0:
            val_size = 1
            
        file_val = sampled_lines[:val_size]
        file_train = sampled_lines[val_size:]

        # Aggregate into folder stats
        folder_stats[folder_key]["total_raw"] += total_in_file
        folder_stats[folder_key]["sampled"] += len(sampled_lines)
        folder_stats[folder_key]["train"] += len(file_train)
        folder_stats[folder_key]["val"] += len(file_val)
        folder_stats[folder_key]["files"].append({
            "name": os.path.basename(file_path),
            "total_raw": total_in_file,
            "sampled": len(sampled_lines),
            "percentage": percentage
        })
        
        all_train.extend(file_train)
        all_val.extend(file_val)
        all_raw.extend(sampled_lines)

    total_aggregated = len(all_raw)
    print(f"\nTotal aggregated samples: {total_aggregated}")

    # 3. Save raw_qa.jsonl
    raw_file = os.path.join(args.output_dir, "raw_qa.jsonl")
    with open(raw_file, 'w', encoding='utf-8') as f:
        for s in all_raw:
            f.write(s + "\n")
    print(f"Saved aggregated raw data to {raw_file}")

    # 4. Shuffle global lists for final safety
    random.shuffle(all_train)
    random.shuffle(all_val)

    # 5. Save Splits
    train_file = os.path.join(args.output_dir, "train_qa.jsonl")
    val_file = os.path.join(args.output_dir, "val_qa.jsonl")

    with open(train_file, 'w', encoding='utf-8') as f:
        for s in all_train:
            f.write(s + "\n")
            
    with open(val_file, 'w', encoding='utf-8') as f:
        for s in all_val:
            f.write(s + "\n")

    # 6. Final Stats Calculation & Saving
    print(f"\nFinal dataset split (Stratified):")
    print(f"  - Train: {len(all_train)} samples -> {train_file}")
    print(f"  - Val:   {len(all_val)} samples -> {val_file}")

    print(f"\nContribution Summary (by Parent Folder):")
    summary = {
        "total_samples": total_aggregated,
        "train_samples": len(all_train),
        "val_samples": len(all_val),
        "quick_summary": {},
        "folders": []
    }

    # Sort folders for consistent output
    for folder_key in sorted(folder_stats.keys()):
        stats = folder_stats[folder_key]
        contribution_pct = round((stats["sampled"] / total_aggregated * 100), 2) if total_aggregated > 0 else 0
        
        summary["quick_summary"][folder_key] = contribution_pct
        
        folder_summary = {
            "folder": folder_key,
            "total_raw": stats["total_raw"],
            "sampled": stats["sampled"],
            "train": stats["train"],
            "val": stats["val"],
            "contribution_percentage": contribution_pct,
            "files": stats["files"]
        }
        summary["folders"].append(folder_summary)
        
        print(f"  - {folder_key}/: {contribution_pct}% ({stats['sampled']} samples from {len(stats['files'])} files)")
        print(f"    -> {stats['train']} train, {stats['val']} val")

    # Additional Quick Summary for console
    print(f"\nQuick Summary:")
    for folder, pct in summary["quick_summary"].items():
        print(f"  {folder}/: {pct}%")

    stats_file = os.path.join(args.output_dir, "aggregation_stats.json")
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=4)
    print(f"\nSaved aggregation stats to {stats_file}")

if __name__ == "__main__":
    main()
