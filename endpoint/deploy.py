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
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    return bucket_name, prefix

def upload_to_gcs(local_path, gcs_uri):
    """Uploads a local directory to a GCS bucket."""
    bucket_name, prefix = parse_gcs_uri(gcs_uri)
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    print(f"Uploading {local_path} to {gcs_uri}...")
    for root, dirs, files in os.walk(local_path):
        for file in files:
            local_file = os.path.join(root, file)
            # Calculate relative path to maintain directory structure
            rel_path = os.path.relpath(local_file, local_path)
            # Ensure prefix ends with / if it exists
            if prefix and not prefix.endswith("/"):
                blob_path = f"{prefix}/{rel_path}"
            else:
                blob_path = f"{prefix}{rel_path}"

            blob_path = blob_path.replace("\\", "/") # For Windows compatibility
            blob = bucket.blob(blob_path)
            blob.upload_from_filename(local_file)
    print("Upload complete.")

def deploy_model(project, location, model_display_name, gcs_uri, local_path=None, skip_upload=False):
    aiplatform.init(project=project, location=location)

    if not skip_upload:
        if not local_path:
            raise ValueError("local_path must be provided if skip_upload is False")
        upload_to_gcs(local_path, gcs_uri)

    bucket_name, prefix = parse_gcs_uri(gcs_uri)
    # Ensure prefix does not end with / for artifact_uri
    artifact_uri = f"gs://{bucket_name}/{prefix.rstrip('/')}"

    serving_container_image_uri = "us-docker.pkg.dev/vertex-ai/vertex-vision-model-garden-dockers/pytorch-vllm-serve:latest"

    print(f"Registering model: {model_display_name}...")

    model = aiplatform.Model.upload(
        display_name=model_display_name,
        artifact_uri=artifact_uri, 
        serving_container_image_uri=serving_container_image_uri,
        serving_container_args=[
            "python3", "-m", "vllm.entrypoints.openai.api_server",
            "--host=0.0.0.0",
            "--port=8080",
            "--max-model-len=1024", 
            "--tensor-parallel-size=1"
        ],
        serving_container_predict_route="/v1/chat/completions",
        serving_container_health_route="/health",
        serving_container_ports=[8080],
    )

    # Check for existing endpoint
    endpoints = aiplatform.Endpoint.list(
        filter=f'display_name="{model_display_name}"',
        order_by="create_time desc"
    )

    if endpoints:
        endpoint = endpoints[0]
        print(f"Using existing endpoint: {endpoint.resource_name}")
    else:
        print(f"Creating new endpoint...")
        endpoint = aiplatform.Endpoint.create(display_name=model_display_name)

    print(f"Deploying model to endpoint {endpoint.display_name} (this takes 10-15 minutes)...")

    # Deploy new model
    endpoint.deploy(
        model=model,
        machine_type="g2-standard-12",
        accelerator_type="NVIDIA_L4",
        accelerator_count=1,
        min_replica_count=1,
        max_replica_count=1,
        deploy_request_timeout=1800, 
    )

    # Undeploy old models if this was an update
    if endpoints:
        deployed_models = endpoint.list_models()
        for dm in deployed_models:
            if dm.model != model.resource_name:
                print(f"Undeploying old model version: {dm.id}")
                endpoint.undeploy(deployed_model_id=dm.id)

    print("\n🚀 SUCCESS!")
    print(f"Endpoint ID: {endpoint.name}")
    print(f"Resource Name: {endpoint.resource_name}")
    return endpoint

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload and Deploy model to Vertex AI")
    parser.add_argument("--project", type=str, default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--location", type=str, default="us-east4")
    parser.add_argument("--local_path", type=str, help="Local path to the merged model directory")
    parser.add_argument("--gcs_path", type=str, required=True, help="GCS URI (gs://bucket/path/) to store model artifacts")
    parser.add_argument("--name", type=str, default="rollmind-gemma-7b", help="Display name for model and endpoint")
    parser.add_argument("--skip-upload", action="store_true", help="Skip uploading local files to GCS")

    args = parser.parse_args()

    if not args.project:
        raise ValueError("Project ID must be set via --project or GOOGLE_CLOUD_PROJECT env var")

    deploy_model(
        project=args.project, 
        location=args.location, 
        model_display_name=args.name, 
        gcs_uri=args.gcs_path,
        local_path=args.local_path,
        skip_upload=args.skip_upload
    )