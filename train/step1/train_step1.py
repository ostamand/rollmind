import torch
import json
import argparse
import os
import shutil
import gc
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, prepare_model_for_kbit_training
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig

# Enable memory-efficient fragmentation handling
os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True,max_split_size_mb:64"

def main():
    parser = argparse.ArgumentParser(description="Fine-tune Gemma with pre-split datasets")
    parser.add_argument("--config", type=str, required=True, help="Path to the JSON config file")
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        cfg = json.load(f)

    # Use bfloat16 for RTX 4070
    compute_dtype = torch.bfloat16
    print(f"Using compute_dtype: {compute_dtype}")

    # 1. BitsAndBytes Config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True,
        llm_int8_enable_fp32_cpu_offload=True
    )

    # 2. Load Model & Tokenizer
    print(f"Loading {cfg['model_id']}...")
    tokenizer = AutoTokenizer.from_pretrained(cfg["model_id"])
    tokenizer.pad_token = tokenizer.eos_token

    # Gemma 7B has a huge 256k vocabulary (~3GB in FP16/BF16).
    # We manually offload embed_tokens and lm_head to CPU.
    # We'll use device_map="auto" but provide a strict max_memory to force it.
    max_memory = {0: "7.5GiB", "cpu": "32GiB"}

    model = AutoModelForCausalLM.from_pretrained(
        cfg["model_id"],
        quantization_config=bnb_config,
        device_map="auto",
        max_memory=max_memory,
        torch_dtype=compute_dtype,
        low_cpu_mem_usage=True,
        attn_implementation="sdpa"
    )
    
    device_map = getattr(model, "hf_device_map", None)
    if device_map:
        print(f"Model device map: {device_map}")
        
    model = prepare_model_for_kbit_training(model)

    # 3. LoRA Configuration
    default_targets = ["q_proj", "o_proj", "k_proj", "v_proj", "gate_proj", "up_proj", "down_proj"]
    target_modules = cfg.get("target_modules", default_targets)
    lora_r = cfg.get("lora_r", 8)
    lora_alpha = cfg.get("lora_alpha", 16)
    lora_dropout = cfg.get("lora_dropout", 0.05)
    
    print(f"LoRA Configuration: r={lora_r}, alpha={lora_alpha}, dropout={lora_dropout}")
    print(f"LoRA Target Modules: {target_modules}")

    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules=target_modules,
        lora_dropout=lora_dropout,
        task_type="CAUSAL_LM"
    )

    # 4. Load Pre-split Datasets
    print(f"Loading datasets...")
    train_dataset = load_dataset("json", data_files=cfg["train_path"], split="train")
    eval_dataset = load_dataset("json", data_files=cfg["val_path"], split="train")

    # 5. SFT Configuration
    eval_steps = cfg.get("eval_steps", 50)
    
    # Decide between max_steps and num_train_epochs
    max_steps = cfg.get("max_steps", -1)
    num_train_epochs = cfg.get("num_train_epochs", 3.0)
    
    if max_steps > 0:
        training_steps_args = {"max_steps": max_steps}
    else:
        training_steps_args = {"num_train_epochs": num_train_epochs}

    sft_config = SFTConfig(
        output_dir=cfg["output_dir"],
        learning_rate=cfg.get("learning_rate", 2e-4),
        per_device_train_batch_size=cfg.get("per_device_train_batch_size", 1),
        per_device_eval_batch_size=cfg.get("per_device_train_batch_size", 1),
        gradient_accumulation_steps=cfg.get("gradient_accumulation_steps", 8), 
        bf16=True,
        fp16=False,
        logging_steps=5,
        eval_strategy="steps",
        eval_steps=eval_steps,
        save_strategy="steps",
        save_steps=cfg.get("save_steps", eval_steps),
        load_best_model_at_end=True,
        metric_for_best_model="loss",
        optim="adamw_8bit",
        report_to="none",
        dataset_text_field="text",
        max_length=cfg.get("max_seq_length", 128),
        packing=True, # Ensure 100% coverage by packing samples
        warmup_steps=cfg.get("warmup_steps", 10),
        weight_decay=cfg.get("weight_decay", 0.01),
        lr_scheduler_type=cfg.get("lr_scheduler_type", "cosine"),
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        # Memory optimizations
        prediction_loss_only=True,
        eval_accumulation_steps=1,
        **training_steps_args
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

    # Clear cache before training
    torch.cuda.empty_cache()
    gc.collect()

    # 7. Train
    print("Starting training...")
    train_result = trainer.train()

    # 8. Final Evaluation
    print("Running final evaluation...")
    eval_metrics = trainer.evaluate()

    # 9. Save Metrics and Model
    print(f"Saving best model to {cfg['output_dir']}...")
    trainer.model.save_pretrained(cfg["output_dir"])
    tokenizer.save_pretrained(cfg["output_dir"])

    # Save all metrics
    trainer.save_metrics("train", train_result.metrics)
    trainer.save_metrics("eval", eval_metrics)
    trainer.save_state()

    # Create all_results.json manually to ensure it's comprehensive
    all_results = {**train_result.metrics, **eval_metrics}
    with open(os.path.join(cfg["output_dir"], "all_results.json"), "w") as f:
        json.dump(all_results, f, indent=4)
    
    # Save log history for easy plotting
    with open(os.path.join(cfg["output_dir"], "metrics_history.json"), "w") as f:
        json.dump(trainer.state.log_history, f, indent=4)

    # Copy config for reference
    shutil.copy(args.config, os.path.join(cfg["output_dir"], "config.json"))

    print(f"Training and evaluation metrics saved to {cfg['output_dir']}.")

if __name__ == "__main__":
    main()