import torch
import json
import argparse
import os
import shutil
import gc
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, PeftModel, prepare_model_for_kbit_training
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig

# Enable memory-efficient fragmentation handling
os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True,max_split_size_mb:64"

def main():
    parser = argparse.ArgumentParser(description="Instruction Fine-tune Gemma")
    parser.add_argument("--config", type=str, required=True, help="Path to the JSON config file")
    parser.add_argument("--low-mem", action="store_true", help="Optimize for 12GB VRAM (CPU offloading)")
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        cfg = json.load(f)

    # Use bfloat16 for RTX 4070 stability
    compute_dtype = torch.bfloat16
    print(f"Using compute_dtype: {compute_dtype}")

    # 1. Fixed Quantization
    if args.low_mem:
        print("Optimization: 12GB VRAM mode (CPU offloading enabled)")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True,
            llm_int8_enable_fp32_cpu_offload=True
        )
        max_memory = {0: "7.5GiB", "cpu": "32GiB"}
    else:
        print("Optimization: 24GB VRAM mode (High performance, no offloading)")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True
        )
        max_memory = None

    # 2. Load Model & Tokenizer
    print(f"Loading base model {cfg['model_id']}...")
    tokenizer = AutoTokenizer.from_pretrained(cfg["model_id"])
    tokenizer.pad_token = tokenizer.eos_token

    base_model = AutoModelForCausalLM.from_pretrained(
        cfg["model_id"],
        quantization_config=bnb_config,
        device_map="auto",
        max_memory=max_memory,
        torch_dtype=compute_dtype,
        low_cpu_mem_usage=True,
        attn_implementation="sdpa"
    )
    
    # Safely print device info
    device_map = getattr(base_model, "hf_device_map", None)
    if device_map:
        print(f"Model device map: {device_map}")
    else:
        print(f"Model loaded on: {base_model.device}")

    # Prepare model for k-bit training
    base_model = prepare_model_for_kbit_training(base_model)

    # 3. Load Step 1 Adapters or initialize new LoRA
    lora_config = None
    
    if "adapter_path" in cfg and cfg["adapter_path"]:
        print(f"Loading Step 1 adapters from {cfg['adapter_path']}...")
        model = PeftModel.from_pretrained(base_model, cfg["adapter_path"], is_trainable=True)
        
        # Apply overrides from config if present
        if "lora_dropout" in cfg:
            new_dropout = cfg["lora_dropout"]
            print(f"Overriding LoRA dropout to {new_dropout}...")
            # Update the config object itself
            if hasattr(model, "peft_config"):
                for adapter_name in model.peft_config:
                    model.peft_config[adapter_name].lora_dropout = new_dropout
            
            # Also update modules directly to be safe
            for name, module in model.named_modules():
                if "lora_dropout" in name or (hasattr(module, "dropout") and "lora" in name.lower()):
                    if hasattr(module, "p"): # Standard dropout
                        module.p = new_dropout
                    elif hasattr(module, "dropout_p"): # Some PEFT versions
                        module.dropout_p = new_dropout
    else:
        print("No adapter path provided. Initializing new LoRA...")
        model = base_model
        
        # Flexible target modules to allow memory saving
        default_targets = ["q_proj", "o_proj", "k_proj", "v_proj", "gate_proj", "up_proj", "down_proj"]
        target_modules = cfg.get("target_modules", default_targets)
        print(f"Using LoRA target modules: {target_modules}")

        lora_config = LoraConfig(
            r=cfg.get("lora_r", 16),
            lora_alpha=cfg.get("lora_alpha", 32),
            target_modules=target_modules,
            lora_dropout=cfg.get("lora_dropout", 0.05),
            task_type="CAUSAL_LM"
        )

    # 4. Load Dataset
    print(f"Loading dataset from {cfg['train_path']}...")
    
    def prepare_dataset(path):
        dataset = load_dataset("json", data_files=path, split="train")
        
        def split_prompt_completion(example):
            separator = "<start_of_turn>model\n"
            if separator in example["text"]:
                parts = example["text"].split(separator)
                return {
                    "prompt": parts[0] + separator,
                    "completion": separator.join(parts[1:])
                }
            return {"prompt": example["text"], "completion": ""}
            
        return dataset.map(split_prompt_completion, remove_columns=["text"])

    train_dataset = prepare_dataset(cfg["train_path"])
    eval_dataset = prepare_dataset(cfg["val_path"])
    print(f"Datasets loaded and split: {len(train_dataset)} train, {len(eval_dataset)} validation.")

    # 5. SFT Configuration
    eval_steps = cfg.get("eval_steps", 50)
    
    # Decide between max_steps and num_train_epochs
    max_steps = cfg.get("max_steps", -1)
    num_train_epochs = cfg.get("num_train_epochs", 3.0)
    
    if max_steps > 0:
        training_steps_args = {"max_steps": max_steps}
    else:
        training_steps_args = {"num_train_epochs": num_train_epochs}

    # Auto-adjust batch size for 24GB mode ONLY if not explicitly specified in config
    train_batch_size = cfg.get("per_device_train_batch_size", 1)
    grad_accum = cfg.get("gradient_accumulation_steps", 8)
    
    # Only auto-optimize if the user didn't explicitly set a batch size in the config
    if not args.low_mem and "per_device_train_batch_size" not in cfg:
        print("Optimizing throughput for 24GB: per_device_train_batch_size=4, gradient_accumulation_steps=grad_accum//4")
        train_batch_size = 4
        grad_accum = max(1, grad_accum // 4)
    else:
        print(f"Using configuration batch size: {train_batch_size} (accumulation: {grad_accum})")

    # Select optimizer: use config or default to adamw_8bit
    optim = cfg.get("optim", "adamw_8bit")
    print(f"Using optimizer: {optim}")

    sft_config = SFTConfig(
        output_dir=cfg["output_dir"],
        learning_rate=cfg.get("learning_rate", 5e-5),
        per_device_train_batch_size=train_batch_size,
        per_device_eval_batch_size=train_batch_size,
        gradient_accumulation_steps=grad_accum,
        bf16=True,
        fp16=False,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=eval_steps,
        save_strategy="steps",
        save_steps=cfg.get("save_steps", eval_steps),
        load_best_model_at_end=True,
        metric_for_best_model="loss",
        optim=optim,
        report_to="none",
        max_length=cfg.get("max_seq_length", 1024),
        warmup_steps=cfg.get("warmup_steps", 0),
        weight_decay=cfg.get("weight_decay", 0.0),
        lr_scheduler_type=cfg.get("lr_scheduler_type", "linear"),
        completion_only_loss=True,
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

    # 8. Train
    print("Starting Step 2 training (Instruction Tuning)...")
    train_result = trainer.train()

    # 9. Final Evaluation
    print("Running final evaluation...")
    eval_metrics = trainer.evaluate()

    # 10. Save Metrics and Model
    print(f"Saving final model to {cfg['output_dir']}...")
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

    # Copy datasets for reference
    print(f"Copying datasets to {cfg['output_dir']}...")
    data_dir = os.path.join(cfg["output_dir"], "data")
    os.makedirs(data_dir, exist_ok=True)
    shutil.copy(cfg["train_path"], os.path.join(data_dir, os.path.basename(cfg["train_path"])))
    shutil.copy(cfg["val_path"], os.path.join(data_dir, os.path.basename(cfg["val_path"])))

    print(f"Training and evaluation metrics saved to {cfg['output_dir']}.")

if __name__ == "__main__":
    main()