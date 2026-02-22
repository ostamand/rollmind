import torch
import json
import argparse
import os
import shutil
import gc
from transformers import AutoTokenizer, AutoModelForCausalLM
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig

def main():
    parser = argparse.ArgumentParser(description="Partial Fine-tune Gemma (Step 2 - Instruction)")
    parser.add_argument("--config", type=str, required=True, help="Path to the JSON config file")
    parser.add_argument("--num-layers", type=int, default=4, help="Number of top layers to unfreeze")
    parser.add_argument("--unfreeze-embeddings", action="store_true", help="Unfreeze the embedding layer")
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        cfg = json.load(f)

    compute_dtype = torch.bfloat16
    print(f"Using compute_dtype: {compute_dtype}")

    # 1. Load Step 1 Model
    model_path = cfg.get("model_path", cfg["model_id"])
    print(f"Loading model from {model_path}...")
    
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="auto",
        torch_dtype=compute_dtype,
        low_cpu_mem_usage=True,
        attn_implementation="sdpa"
    )

    # 2. Freeze all parameters first
    for param in model.parameters():
        param.requires_grad = False

    # 3. Unfreeze logic
    print("Unfreezing lm_head...")
    model.lm_head.requires_grad = True
    if args.unfreeze_embeddings:
        print("Unfreezing embed_tokens...")
        model.model.embed_tokens.requires_grad = True

    num_total_layers = len(model.model.layers)
    start_layer = num_total_layers - args.num_layers
    print(f"Unfreezing last {args.num_layers} layers...")
    for i in range(start_layer, num_total_layers):
        for param in model.model.layers[i].parameters():
            param.requires_grad = True

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

    # 5. SFT Configuration
    sft_config = SFTConfig(
        output_dir=cfg["output_dir"],
        learning_rate=cfg.get("learning_rate", 1e-5),
        per_device_train_batch_size=cfg.get("per_device_train_batch_size", 2),
        per_device_eval_batch_size=cfg.get("per_device_train_batch_size", 2),
        gradient_accumulation_steps=cfg.get("gradient_accumulation_steps", 4),
        bf16=True,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=cfg.get("eval_steps", 50),
        save_strategy="steps",
        save_steps=cfg.get("save_steps", 50),
        load_best_model_at_end=True,
        metric_for_best_model="loss",
        optim="adamw_8bit",
        report_to="none",
        max_length=cfg.get("max_seq_length", 512),
        warmup_steps=cfg.get("warmup_steps", 20),
        weight_decay=cfg.get("weight_decay", 0.05),
        lr_scheduler_type="cosine",
        completion_only_loss=True,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        num_train_epochs=cfg.get("num_train_epochs", 2.0),
    )

    # 6. Initialize Trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        args=sft_config,
        processing_class=tokenizer
    )

    torch.cuda.empty_cache()
    gc.collect()

    # 7. Train
    print("Starting Partial Fine-tuning (Step 2)...")
    train_result = trainer.train()

    # 8. Final Evaluation
    print("Running final evaluation...")
    eval_metrics = trainer.evaluate()

    # 9. Save
    print(f"Saving final partial-tuned model to {cfg['output_dir']}...")
    trainer.save_model(cfg["output_dir"])
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
