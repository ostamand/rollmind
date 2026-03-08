# Hugging Face Hub Tools

This folder contains scripts for preparing and uploading RollMind models to the Hugging Face Hub.

## 🚀 How to Upload

Ensure you have the `huggingface_hub` library installed and you are logged in:

```bash
pip install huggingface_hub
huggingface-cli login
```

Then run the upload script:

```bash
# Replace <username> with your HF username
python3 hf_hub/prepare_hf_upload.py --username <username>
```

## 📋 What the Script Does

1. **Generates Model Cards**: Automatically creates a professional `README.md` for each model version (Gemma 3 12B and Gemma 1.1 7B).
2. **Injects Metadata**: Adds tags for `dnd`, `rpg`, and `gemma` to ensure discoverability.
3. **Automated Upload**: Creates the repositories (if they don't exist) and uploads the model weights, tokenizer configs, and the generated README.
