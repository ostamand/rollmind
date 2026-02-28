import os
import argparse
from google.cloud import aiplatform
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

def parse_gcs_uri(uri):
    if not uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {uri}. Must start with gs://")
    parts = uri[5:].split("/", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""

def deploy_model(project, location, model_display_name, gcs_uri):
    aiplatform.init(project=project, location=location)
    bucket_name, prefix = parse_gcs_uri(gcs_uri)

    # Use Google's official, patched vLLM container
    serving_container_image_uri = "us-docker.pkg.dev/vertex-ai/vertex-vision-model-garden-dockers/pytorch-vllm-serve:latest"

    print(f"Registering model: {model_display_name}...")

    model = aiplatform.Model.upload(
        display_name=model_display_name,
        artifact_uri=f"gs://{bucket_name}/{prefix}", 
        serving_container_image_uri=serving_container_image_uri,
        
        # 🚨 THE FIX: Do not use serving_container_command. Let Google's launcher run.
        
        # Put the Python command at the start of the args. 
        # The launcher will automatically download the GCS bucket and append "--model=/tmp/..." to the end of this list.
        serving_container_args=[
            "python3", "-m", "vllm.entrypoints.openai.api_server",
            "--host=0.0.0.0",
            "--port=8080",
            "--max-model-len=512", 
            "--tensor-parallel-size=1"
        ],
        
        # Standard OpenAI routes 
        serving_container_predict_route="/v1/chat/completions",
        serving_container_health_route="/health",
        serving_container_ports=[8080],
    )
    
    print(f"Deploying to endpoint (this takes 10-15 minutes)...")
    endpoint = model.deploy(
        machine_type="g2-standard-12",
        accelerator_type="NVIDIA_L4",
        accelerator_count=1,
        min_replica_count=1,
        max_replica_count=1,
        deploy_request_timeout=1800, 
    )

    print("\n🚀 SUCCESS!")
    print(f"Endpoint ID: {endpoint.name}")
    print(f"Resource Name: {endpoint.resource_name}")
    return endpoint

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload and Deploy model")
    parser.add_argument("--project", type=str, default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--location", type=str, default="us-east4")
    parser.add_argument("--gcs_path", type=str, required=True)
    parser.add_argument("--name", type=str, default="rollmind-gemma-7b")
    
    args = parser.parse_args()
    
    if not args.gcs_path.endswith("/"):
        args.gcs_path += "/"
    
    deploy_model(args.project, args.location, args.name, args.gcs_path)