import argparse
import os
import sys
from google.cloud import aiplatform
from dotenv import load_dotenv

load_dotenv()

def toggle_endpoint(project, location, name, action, model_name=None):
    aiplatform.init(project=project, location=location)

    # 1. Find Endpoint
    endpoints = aiplatform.Endpoint.list(
        filter=f'display_name="{name}"',
        order_by="create_time desc"
    )
    
    endpoint = None
    if endpoints:
        endpoint = endpoints[0]
        print(f"Found endpoint: {endpoint.display_name} ({endpoint.resource_name})")
    
    if action == "off":
        if not endpoint:
            print(f"No endpoint found with name '{name}'. Nothing to turn off.")
            return

        print(f"Turning OFF: Undeploying all models from {name} to stop GPU billing...")
        endpoint.undeploy_all()
        print(f"SUCCESS: All models undeployed. GPU billing has stopped.")

    elif action == "on":
        # Find Model to deploy
        target_model_name = model_name if model_name else name
        models = aiplatform.Model.list(
            filter=f'display_name="{target_model_name}"',
            order_by="create_time desc"
        )
        
        if not models:
            print(f"ERROR: No registered model found with name '{target_model_name}'. Use deploy.py first.")
            sys.exit(1)
        
        model = models[0]
        print(f"Found latest model version: {model.display_name} ({model.resource_name})")

        if not endpoint:
            print(f"Creating new endpoint '{name}'...")
            endpoint = aiplatform.Endpoint.create(display_name=name)

        # Check if already deployed
        deployed_models = endpoint.list_models()
        if any(dm.model == model.resource_name for dm in deployed_models):
            print(f"Model is already deployed to endpoint. No action needed.")
            return

        print(f"Turning ON: Deploying model to endpoint (10-15 minutes)...")
        endpoint.deploy(
            model=model,
            machine_type="g2-standard-12",
            accelerator_type="NVIDIA_L4",
            accelerator_count=1,
            min_replica_count=1,
            max_replica_count=1,
            deploy_request_timeout=1800, 
        )
        print("\n🚀 SUCCESS: Endpoint is back ONLINE!")
        print(f"Endpoint ID: {endpoint.name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Toggle Vertex AI Endpoint ON/OFF to manage costs")
    parser.add_argument("action", choices=["on", "off"], help="Action to perform: 'on' or 'off'")
    parser.add_argument("--name", type=str, default="rollmind-gemma-7b_endpoint", help="Display name of the endpoint")
    parser.add_argument("--model_name", default="rollmind-gemma-7b", type=str, help="Display name of the model")
    parser.add_argument("--project", type=str, default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--location", type=str, default="us-east4")

    args = parser.parse_args()
    
    if not args.project:
        print("ERROR: Project ID must be set via --project or GOOGLE_CLOUD_PROJECT env var")
        sys.exit(1)

    toggle_endpoint(args.project, args.location, args.name, args.action, model_name=args.model_name)
