import os
import argparse
from google.cloud import aiplatform
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

def parse_gcs_uri(uri):
    """Parses a gs://bucket/path URI into (bucket_name, prefix)."""
    if not uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {uri}. Must start with gs://")
    parts = uri[5:].split("/", 1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    return bucket_name, prefix

def upload_to_gcs(local_path, gcs_uri):
    import subprocess
    print(f"🚀 Starting optimized parallel upload to {gcs_uri}...")
    
    # Flags explained:
    # -m: Run in parallel (multiple threads/processes)
    # GSUtil:parallel_composite_upload_threshold=150M: Chunks large files for parallel streams
    try:
        subprocess.run([
            "gsutil", 
            "-m", 
            "-o", "GSUtil:parallel_composite_upload_threshold=150M", 
            "cp", "-r", local_path + "/*", gcs_uri
        ], check=True)
        print("✅ Upload complete.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during upload: {e}")
        raise e

def check_gcs_path_exists(gcs_uri):
    """Checks if any blobs exist under the given GCS URI."""
    bucket_name, prefix = parse_gcs_uri(gcs_uri)
    client = storage.Client()
    try:
        bucket = client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=prefix, max_results=1))
        return len(blobs) > 0
    except Exception as e:
        print(f"⚠️ Warning: Could not verify GCS path existence: {e}")
        return False

def deploy_model(project, location, model_display_name, gcs_uri):
    aiplatform.init(project=project, location=location)

    bucket_name, prefix = parse_gcs_uri(gcs_uri)
    serving_container_image_uri = "us-docker.pkg.dev/vertex-ai/vertex-vision-model-garden-dockers/pytorch-vllm-serve:latest"

    print(f"Registering model: {model_display_name}...")

    model = aiplatform.Model.upload(
        display_name=model_display_name,
        artifact_uri=f"gs://{bucket_name}/{prefix}", 
        serving_container_image_uri=serving_container_image_uri,
        serving_container_command=["python", "-m", "vllm.entrypoints.api_server"],
        # Notice the = formatting and the complete removal of --model
        serving_container_args=[
            "--host=0.0.0.0",
            "--port=8080",
            "--max-model-len=512", 
            "--tensor-parallel-size=1"
        ],
        serving_container_predict_route="/generate",
        serving_container_health_route="/ping",
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
    parser = argparse.ArgumentParser(description="Upload and Deploy model to Vertex AI")
    parser.add_argument("--project", type=str, default=os.getenv("GOOGLE_CLOUD_PROJECT"), help="GCP Project ID")
    parser.add_argument("--location", type=str, default=os.getenv("GOOGLE_CLOUD_LOCATION", "us-east4"), help="GCP Region")
    parser.add_argument("--gcs_path", type=str, required=True, help="Full GCS path (gs://bucket/path)")
    parser.add_argument("--local_model_dir", type=str, default="./merged_model", help="Local directory with merged weights")
    parser.add_argument("--name", type=str, default="rollmind-gemma-7b", help="Display name for the model")
    parser.add_argument("--skip-upload", action="store_true", help="Skip GCS upload if the model already exists")
    
    args = parser.parse_args()
    
    # Ensure gcs_path is a full URI and ends with /
    if not args.gcs_path.startswith("gs://"):
        args.gcs_path = f"gs://{args.gcs_path}"
    if not args.gcs_path.endswith("/"):
        args.gcs_path += "/"
    
    print(f"Configuration:")
    print(f"  Project:  {args.project}")
    print(f"  Location: {args.location}")
    print(f"  GCS Path: {args.gcs_path}")
    print(f"  Name:     {args.name}")
    
    should_upload = not args.skip_upload
    if args.skip_upload:
        print(f"⏭ Skipping GCS upload check as --skip-upload was provided.")
    elif check_gcs_path_exists(args.gcs_path):
        print(f"ℹ️ Model already exists at {args.gcs_path}. Skipping upload.")
        should_upload = False
    
    if should_upload:
        upload_to_gcs(args.local_model_dir, args.gcs_path)
    
    deploy_model(args.project, args.location, args.name, args.gcs_path)
