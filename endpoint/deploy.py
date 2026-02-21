import os
import argparse
from google.cloud import aiplatform
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

def upload_to_gcs(local_path, bucket_name, gcs_path):
    import subprocess
    target_uri = f"gs://{bucket_name}/{gcs_path}"
    print(f"🚀 Starting optimized parallel upload to {target_uri}...")
    
    # Flags explained:
    # -m: Run in parallel (multiple threads/processes)
    # GSUtil:parallel_composite_upload_threshold=150M: Chunks large files for parallel streams
    try:
        subprocess.run([
            "gsutil", 
            "-m", 
            "-o", "GSUtil:parallel_composite_upload_threshold=150M", 
            "cp", "-r", local_path + "/*", target_uri
        ], check=True)
        print("✅ Upload complete.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during upload: {e}")
        raise e

def deploy_model(project, location, bucket_name, model_display_name, model_path):
    aiplatform.init(project=project, location=location)

    # Using the Google-optimized vLLM container
    serving_container_image_uri = "us-docker.pkg.dev/vertex-ai/vertex-vision-model-garden-dockers/pytorch-vllm-serve:latest"

    vllm_args = [
        "--host=0.0.0.0",
        "--port=8080",
        "--model=$(AIP_STORAGE_URI)", 
        "--max-model-len=1024", # Safe for Gemma 7B on 24GB L4
        "--tensor-parallel-size=1"
    ]

    print(f"Registering model: {model_display_name}...")
    model = aiplatform.Model.upload(
        display_name=model_display_name,
        artifact_uri=f"gs://{bucket_name}/{model_path}",
        serving_container_image_uri=serving_container_image_uri,
        serving_container_args=vllm_args,
        # Google's wrapper uses /generate and /ping
        serving_container_predict_route="/generate",
        serving_container_health_route="/ping",
        serving_container_ports=[8080],
    )

    print(f"Deploying to endpoint (this takes 10-15 minutes)...")
    endpoint = model.deploy(
        machine_type="g2-standard-4",
        accelerator_type="NVIDIA_L4",
        accelerator_count=1,
        min_replica_count=1,
        max_replica_count=1,
    )

    print("\n🚀 SUCCESS!")
    print(f"Endpoint ID: {endpoint.name}")
    print(f"Resource Name: {endpoint.resource_name}")
    return endpoint

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload and Deploy model to Vertex AI")
    parser.add_argument("--project", type=str, default=os.getenv("GOOGLE_CLOUD_PROJECT"), help="GCP Project ID")
    parser.add_argument("--location", type=str, default=os.getenv("GOOGLE_CLOUD_LOCATION", "us-east4"), help="GCP Region")
    parser.add_argument("--bucket", type=str, required=True, help="GCS Bucket name (without gs://)")
    parser.add_argument("--local_model_dir", type=str, default="./merged_model", help="Local directory with merged weights")
    parser.add_argument("--name", type=str, default="rollmind-gemma-7b", help="Display name for the model")
    
    args = parser.parse_args()
    gcs_path = f"models/{args.name}"
    
    upload_to_gcs(args.local_model_dir, args.bucket, gcs_path)
    deploy_model(args.project, args.location, args.bucket, args.name, gcs_path)