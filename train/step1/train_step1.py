import torch
import json
import argparse
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, prepare_model_for_kbit_training
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig

def main():
    parser = argparse.ArgumentParser(description="Fine-tune Gemma with pre-split datasets")
    parser.add_argument("--config", type=str, required=True, help="Path to the JSON config file")
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        cfg = json.load(f)

    # Check for BF16 support
    use_bf16 = torch.cuda.is_bf16_supported()
    compute_dtype = torch.bfloat16 if use_bf16 else torch.float16
    print(f"Using compute_dtype: {compute_dtype}")

    # 1. BitsAndBytes Config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True
    )

    # 2. Load Model & Tokenizer
    print(f"Loading {cfg['model_id']}...")
    tokenizer = AutoTokenizer.from_pretrained(cfg["model_id"])
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        cfg["model_id"],
        quantization_config=bnb_config,
        device_map="auto"
    )
    
    device_map = getattr(model, "hf_device_map", None)
    if device_map:
        print(f"Model device map: {device_map}")
    else:
        print(f"Model loaded on: {model.device}")
        
    model = prepare_model_for_kbit_training(model)

    # 3. LoRA Configuration
    lora_config = LoraConfig(
        r=cfg.get("lora_r", 16),
        lora_alpha=cfg.get("lora_alpha", 32),
        target_modules=["q_proj", "o_proj", "k_proj", "v_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        task_type="CAUSAL_LM"
    )

    # 4. Load Pre-split Datasets
    print(f"Loading datasets...")
    train_dataset = load_dataset("json", data_files=cfg["train_path"], split="train")
    eval_dataset = load_dataset("json", data_files=cfg["val_path"], split="train")

    # 5. SFT Configuration
    eval_steps = cfg.get("eval_steps", 50)
    sft_config = SFTConfig(
        output_dir=cfg["output_dir"],
        learning_rate=cfg.get("learning_rate", 2e-4),
        max_steps=cfg.get("max_steps", 200),
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=8,
        bf16=use_bf16,
        fp16=not use_bf16,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=eval_steps,
        save_strategy="steps",
        save_steps=cfg.get("save_steps", eval_steps), # Default to eval_steps to avoid ValueError
        load_best_model_at_end=True,
        metric_for_best_model="loss",
        optim="paged_adamw_32bit",
        report_to="none",
        dataset_text_field="text",
        max_length=cfg.get("max_seq_length", 1024),
        # New flexible hyperparameters
        warmup_steps=cfg.get("warmup_steps", 0),
        weight_decay=cfg.get("weight_decay", 0.0),
        lr_scheduler_type=cfg.get("lr_scheduler_type", "linear"),
        # Memory optimizations for evaluation
        prediction_loss_only=True,
        eval_accumulation_steps=1
    )

    # 6. Initialize Trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        peft_config=lora_config,
        args=sft_config,
        processing_class=tokenizer
    )

    # 7. Train
    print("Starting training...")
    train_result = trainer.train()

    # 8. Save Metrics and Model
    print(f"Saving best model to {cfg['output_dir']}...")
    trainer.model.save_pretrained(cfg["output_dir"])
    tokenizer.save_pretrained(cfg["output_dir"])

    # Save training metrics
    metrics = train_result.metrics
    trainer.save_metrics("train", metrics)
    trainer.save_state() # Saves trainer_state.json with log_history

    print("Training metrics saved to output directory.")

if __name__ == "__main__":
    main()