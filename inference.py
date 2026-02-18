import torch
import argparse
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

def main():
    parser = argparse.ArgumentParser(description="Inference script for Gemma/LoRA models")
    parser.add_argument("--model_id", type=str, default="google/gemma-2b-it", help="Base model ID or path")
    parser.add_argument("--adapter_path", type=str, default=None, help="Path to LoRA adapter")
    parser.add_argument("--prompt", type=str, required=True, help="User prompt")
    parser.add_argument("--max_new_tokens", type=int, default=256, help="Maximum new tokens to generate")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
    parser.add_argument("--top_p", type=float, default=0.9, help="Top-p sampling")
    parser.add_argument("--top_k", type=int, default=50, help="Top-k sampling")
    parser.add_argument("--no_template", action="store_true", help="Do not use the Gemma instruction template")
    parser.add_argument("--load_in_4bit", type=bool, default=True, help="Load model in 4-bit quantization")
    
    args = parser.parse_args()

    # 1. Load Tokenizer
    print(f"Loading tokenizer for {args.model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    tokenizer.pad_token = tokenizer.eos_token

    # 2. BitsAndBytes Config
    bnb_config = None
    if args.load_in_4bit:
        compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
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
        device_map="auto",
        torch_dtype=torch.float16 if not torch.cuda.is_bf16_supported() else torch.bfloat16
    )

    # 4. Optionally Load LoRA Adapter
    if args.adapter_path:
        print(f"Loading LoRA adapter from: {args.adapter_path}...")
        model = PeftModel.from_pretrained(model, args.adapter_path)
    
    model.eval()

    # 5. Prepare Prompt
    full_prompt = args.prompt
    if not args.no_template:
        full_prompt = f"<start_of_turn>user\n{args.prompt}<end_of_turn>\n<start_of_turn>model\n"

    # 6. Tokenize and Generate
    inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)
    
    print("\nGenerating...")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            top_k=args.top_k,
            do_sample=True if args.temperature > 0 else False,
            pad_token_id=tokenizer.eos_token_id
        )

    # 7. Decode and Print
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    if not args.no_template:
        # Extract response after the prompt
        # Skip tokens might remove <start_of_turn> but let's be safe
        if "model\n" in response:
            response = response.split("model\n")[-1].strip()
        elif "Assistant: " in response: # Fallback for old models
            response = response.split("Assistant: ")[-1].strip()
    
    print("\n" + "="*30)
    print("PROMPT:", args.prompt)
    print("-" * 30)
    print("RESPONSE:")
    print(response)
    print("="*30 + "\n")

if __name__ == "__main__":
    main()
