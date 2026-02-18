import torch
import json
import argparse
import math
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
from datasets import load_dataset
from torch.utils.data import DataLoader

def main():
    parser = argparse.ArgumentParser(description="Evaluate a model or LoRA adapter on a dataset")
    parser.add_argument("--model_id", type=str, required=True, help="Base model ID or path")
    parser.add_argument("--adapter_path", type=str, default=None, help="Optional path to LoRA adapter")
    parser.add_argument("--dataset_path", type=str, required=True, help="Path to evaluation JSONL file")
    parser.add_argument("--batch_size", type=int, default=1, help="Batch size for evaluation")
    parser.add_argument("--max_seq_length", type=int, default=1024, help="Maximum sequence length")
    args = parser.parse_args()

    # 0. Check for BF16 support
    use_bf16 = torch.cuda.is_bf16_supported()
    compute_dtype = torch.bfloat16 if use_bf16 else torch.float16
    print(f"Using compute_dtype: {compute_dtype}")

    # 1. Load Tokenizer
    print(f"Loading tokenizer for {args.model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    tokenizer.pad_token = tokenizer.eos_token

    # 2. BitsAndBytes Config (to fit in 12GB)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True
    )

    # 3. Load Base Model
    print(f"Loading base model: {args.model_id}...")
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        quantization_config=bnb_config,
        device_map="auto"
    )
    device_map = getattr(model, "hf_device_map", None)
    if device_map:
        print(f"Model device map: {device_map}")
    else:
        print(f"Model loaded on: {model.device}")

    # 4. Optionally Load LoRA Adapter
    if args.adapter_path:
        print(f"Loading LoRA adapter from: {args.adapter_path}...")
        model = PeftModel.from_pretrained(model, args.adapter_path)
    
    model.eval()

    # 5. Load and Tokenize Dataset
    print(f"Loading dataset from {args.dataset_path}...")
    dataset = load_dataset("json", data_files=args.dataset_path, split="train")

    def tokenize_function(examples):
        return tokenizer(examples["text"], truncation=True, max_length=args.max_seq_length, padding="max_length")

    tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=["text"])
    tokenized_dataset.set_format("torch")
    
    dataloader = DataLoader(tokenized_dataset, batch_size=args.batch_size)

    # 6. Evaluation Loop
    total_loss = 0
    total_steps = 0

    print("Evaluating...")
    with torch.no_grad():
        for batch in tqdm(dataloader):
            input_ids = batch["input_ids"].to(model.device)
            attention_mask = batch["attention_mask"].to(model.device)
            labels = input_ids.clone()
            
            # Mask padding in labels so they don't contribute to loss
            labels[attention_mask == 0] = -100

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            
            total_loss += loss.item()
            total_steps += 1

    avg_loss = total_loss / total_steps
    perplexity = math.exp(avg_loss) if avg_loss < 700 else float('inf')

    # 7. Print Results
    print("\n" + "="*30)
    print(f"Model: {args.model_id}")
    if args.adapter_path:
        print(f"Adapter: {args.adapter_path}")
    print(f"Dataset: {args.dataset_path}")
    print("-" * 30)
    print(f"Average Loss: {avg_loss:.4f}")
    print(f"Perplexity:   {perplexity:.4f}")
    print("="*30 + "\n")

if __name__ == "__main__":
    main()