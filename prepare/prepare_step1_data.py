import json
import glob
import re
import argparse
import random

def process_markdown(content, max_chars=3000):
    """
    Split markdown into chunks while preserving header context and block integrity.
    """
    # Split into blocks by double newlines
    blocks = re.split(r'\n\n+', content)
    
    chunks = []
    current_chunk_blocks = []
    current_length = 0
    
    # Context trackers
    last_headers = {1: "", 2: "", 3: ""}
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
            
        # Update header context if this block is a header
        h_match = re.match(r'^(#+)\s+(.+)', block)
        if h_match:
            level = len(h_match.group(1))
            title = h_match.group(2)
            if level in last_headers:
                last_headers[level] = title
                # Clear sub-headers
                for i in range(level + 1, 4):
                    last_headers[i] = ""

        # Calculate context string to prepend
        context_lines = []
        for i in range(1, 4):
            if last_headers[i]:
                context_lines.append("#" * i + " " + last_headers[i])
        context_str = "\n".join(context_lines)
        
        # If adding this block exceeds limit, finalize current chunk
        if current_length + len(block) > max_chars and current_chunk_blocks:
            chunks.append("\n\n".join(current_chunk_blocks))
            # Reset chunk, starting with the current header context for the next one
            current_chunk_blocks = [context_str] if context_str else []
            current_length = len(context_str)

        current_chunk_blocks.append(block)
        current_length += len(block) + 2 # +2 for newline
            
    if current_chunk_blocks:
        chunks.append("\n\n".join(current_chunk_blocks))
        
    return chunks

def main():
    parser = argparse.ArgumentParser(description="Prepare D&D Markdown data for fine-tuning.")
    parser.add_argument("--max_chars", type=int, default=3000, help="Maximum characters per chunk (default: 3000)")
    parser.add_argument("--input_pattern", type=str, default="data/player-handbook-2024/*.md", help="Glob pattern for input files")
    
    args = parser.parse_args()
    
    files = sorted(glob.glob(args.input_pattern))
    print(f"Found {len(files)} files.")
    
    all_chunks = []
    for file_path in files:
        print(f"Processing {file_path}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            content = content.replace('\r\n', '\n')
            content = re.sub(r'\n{3,}', '\n\n', content)
            
            file_chunks = process_markdown(content, max_chars=args.max_chars)
            all_chunks.extend(file_chunks)
            
    print(f"Created {len(all_chunks)} total semantic chunks.")
    
    # Pre-split the data for reproducibility
    random.seed(42)
    random.shuffle(all_chunks)
    
    split_idx = int(len(all_chunks) * 0.9)
    train_chunks = all_chunks[:split_idx]
    val_chunks = all_chunks[split_idx:]
    
    # Save training set
    train_file = "data/step1/train_chunks.jsonl"
    with open(train_file, 'w', encoding='utf-8') as f:
        for chunk in train_chunks:
            json.dump({"text": chunk}, f)
            f.write('\n')
            
    # Save validation set
    val_file = "data/step1/val_chunks.jsonl"
    with open(val_file, 'w', encoding='utf-8') as f:
        for chunk in val_chunks:
            json.dump({"text": chunk}, f)
            f.write('\n')
            
    # Save full set for 100% coverage training
    full_file = "data/step1/full_chunks.jsonl"
    with open(full_file, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            json.dump({"text": chunk}, f)
            f.write('\n')
            
    print(f"Saved {len(all_chunks)} chunks to {full_file}")
    print(f"Saved {len(train_chunks)} chunks to {train_file}")
    print(f"Saved {len(val_chunks)} chunks to {val_file}")

if __name__ == "__main__":
    main()