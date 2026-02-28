import json
import os
import argparse
import random
from tqdm import tqdm
from prepare.utils import generate_random_profile

def inject_profiles(input_dir, output_dir):
    """
    Reads all .jsonl files in input_dir and adds a random character profile
    to the beginning of the user prompt if one doesn't exist.
    Outputs to output_dir with _converted suffix.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    jsonl_files = [f for f in os.listdir(input_dir) if f.endswith('.jsonl')]
    
    if not jsonl_files:
        print(f"No .jsonl files found in {input_dir}")
        return

    print(f"Found {len(jsonl_files)} files to process.")

    for filename in jsonl_files:
        input_path = os.path.join(input_dir, filename)
        output_filename = f"{os.path.splitext(filename)[0]}_converted.jsonl"
        output_path = os.path.join(output_dir, output_filename)

        print(f"Processing {filename} -> {output_filename}...")
        
        with open(input_path, 'r', encoding='utf-8') as f_in, \
             open(output_path, 'w', encoding='utf-8') as f_out:
            
            for line in tqdm(f_in, desc=f"Converting {filename}"):
                if not line.strip():
                    continue
                
                try:
                    data = json.loads(line)
                    text = data.get("text", "")
                    
                    user_tag = "<start_of_turn>user\n"
                    if text.startswith(user_tag):
                        # Check if profile already exists
                        if not text.startswith(f"{user_tag}Character Profile:"):
                            profile = generate_random_profile()
                            # Inject profile after user tag
                            # Use replace with count=1 to only replace the first occurrence
                            new_text = text.replace(user_tag, f"{user_tag}{profile}\n\n", 1)
                            data["text"] = new_text
                    
                    f_out.write(json.dumps(data) + "\n")
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON line in {filename}")
                except Exception as e:
                    print(f"Error processing line in {filename}: {e}")

    print("Done!")

def main():
    parser = argparse.ArgumentParser(description="Inject random character profiles into existing training data.")
    parser.add_argument("--input_dir", type=str, required=True, help="Directory containing .jsonl files to update.")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save updated .jsonl files.")
    args = parser.parse_args()

    inject_profiles(args.input_dir, args.output_dir)

if __name__ == "__main__":
    main()
