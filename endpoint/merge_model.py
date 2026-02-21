import torch
import os
import argparse
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def merge_model(model_id, adapter_path, output_dir):
    print(f"Loading base model: {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    
    # Load base model in FP16/BF16 for merging (no 4-bit/8-bit during merge)
    base_model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="cpu", # Merge on CPU to avoid VRAM limits
    )

    print(f"Loading adapter: {adapter_path}")
    model = PeftModel.from_pretrained(base_model, adapter_path)

    print("Merging weights... this may take a minute.")
    model = model.merge_and_unload()

    print(f"Saving merged model to: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print("Merge complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge LoRA adapter with base model")
    parser.add_argument("--model_id", type=str, required=True, help="Base model ID (e.g. google/gemma-7b-it)")
    parser.add_argument("--adapter_path", type=str, required=True, help="Path to Step 2 adapter")
    parser.add_argument("--output_dir", type=str, default="./merged_model", help="Local directory to save merged model")
    
    args = parser.parse_args()
    merge_model(args.model_id, args.adapter_path, args.output_dir)
