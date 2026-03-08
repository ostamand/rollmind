import os
import argparse
from huggingface_hub import HfApi, create_repo
from pathlib import Path

def create_model_card(model_name, base_model, username):
    """Reads the MODEL_CARD.md template and performs dynamic replacements."""
    template_path = os.path.join(os.path.dirname(__file__), "MODEL_CARD.md")
    
    if not os.path.exists(template_path):
        print(f"⚠️ Template not found at {template_path}. Falling back to basic content.")
        return f"# {model_name}\nBase model: {base_model}"

    with open(template_path, "r") as f:
        content = f.read()

    # Determine tags and descriptions based on model version
    is_gemma3 = "gemma3" in base_model.lower() or "12b" in model_name.lower()
    gemma_tag = "gemma3" if is_gemma3 else "gemma"
    model_type_desc = "Gemma 3 12B" if is_gemma3 else "Gemma 1.1 7B"

    # Perform replacements
    content = content.replace("YOUR_USERNAME", username)
    content = content.replace("RollMind-v1-gemma3-12b", model_name)
    content = content.replace("google/gemma-3-12b-it", base_model)
    
    # Handle the title and YAML tags if they need specific switching
    if not is_gemma3:
        content = content.replace("- gemma3", "- gemma")
        content = content.replace("Gemma 3 12B", "Gemma 1.1 7B")

    return content

def upload_model(local_path, repo_id, token=None):
    api = HfApi(token=token)
    
    print(f"Creating repository: {repo_id}")
    try:
        create_repo(repo_id=repo_id, repo_type="model", exist_ok=True, token=token)
    except Exception as e:
        print(f"Note: {e}")

    print(f"Uploading files from {local_path} to {repo_id}...")
    api.upload_folder(
        folder_path=local_path,
        repo_id=repo_id,
        repo_type="model",
    )
    print(f"✅ Upload complete: https://huggingface.co/{repo_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload RollMind models to Hugging Face")
    parser.add_argument("--username", type=str, required=True, help="Your Hugging Face username")
    parser.add_argument("--token", type=str, help="HF Write Token (or use huggingface-cli login)")
    
    args = parser.parse_args()
    
    # Define models based on current project state
    models_to_upload = [
        {
            "name": "RollMind-v1-gemma3-12b",
            "path": "./out/rollmind-v3",
            "base": "google/gemma-3-12b-it"
        },
        {
            "name": "RollMind-v1-gemma1.1-7b",
            "path": "./out/rollmind-v2",
            "base": "google/gemma-1.1-7b-it"
        }
    ]
    
    for m in models_to_upload:
        # Resolve absolute path relative to project root
        abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", m["path"]))
        
        if os.path.exists(abs_path):
            # Create README.md inside the model folder before upload
            readme_path = os.path.join(abs_path, "README.md")
            print(f"Generating README for {m['name']} from template...")
            
            custom_readme = create_model_card(m["name"], m["base"], args.username)
            
            with open(readme_path, "w") as f:
                f.write(custom_readme)
            
            # Upload
            repo_id = f"{args.username}/{m['name']}"
            upload_model(abs_path, repo_id, token=args.token)
        else:
            print(f"⚠️ Path not found: {abs_path}. Skipping {m['name']}.")
