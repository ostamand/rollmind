import argparse
import os
from google.cloud import aiplatform
from dotenv import load_dotenv

load_dotenv()

def cleanup_endpoint(project, location, endpoint_id):
    aiplatform.init(project=project, location=location)

    print(f"Fetching endpoint {endpoint_id}...")
    endpoint = aiplatform.Endpoint(
        endpoint_name=f"projects/{project}/locations/{location}/endpoints/{endpoint_id}"
    )

    print(f"Undeploying all models from endpoint... this stops GPU billing.")
    endpoint.undeploy_all()

    print(f"Deleting endpoint...")
    endpoint.delete()
    print("Cleanup complete. GPU node has been decommissioned.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup Vertex AI Endpoint")
    parser.add_argument("--endpoint_id", type=str, required=True, help="Alphanumeric Endpoint ID")
    parser.add_argument("--project", type=str, default=os.getenv("GOOGLE_CLOUD_PROJECT"), help="GCP Project ID")
    parser.add_argument("--location", type=str, default=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"), help="GCP Region")

    args = parser.parse_args()
    cleanup_endpoint(args.project, args.location, args.endpoint_id)
