import argparse
import os
from google.cloud import aiplatform
from dotenv import load_dotenv

load_dotenv()

def predict_custom_trained_model_sample(
    project: str,
    endpoint_id: str,
    prompt: str,
    location: str = "us-east4",
):
    aiplatform.init(project=project, location=location)

    endpoint = aiplatform.Endpoint(
        endpoint_name=f"projects/{project}/locations/{location}/endpoints/{endpoint_id}"
    )

    # Apply Gemma's chat template
    formatted_prompt = f"<start_of_turn>user\n{prompt}<end_of_turn>\n<start_of_turn>model\n"

    # With pytorch-vllm-serve, standard endpoint.predict() works natively!
    # Pack your generation parameters directly into the instance dictionary.
    instances = [
        {
            "prompt": formatted_prompt,
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
        }
    ]

    print(f"Sending request to endpoint {endpoint_id}...")
    
    # Standard Vertex SDK call
    response = endpoint.predict(instances=instances)
    
    print("\n--- RESPONSE ---")
    # Extract the generated text from the response object
    print(response.predictions[0])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Vertex AI Endpoint")
    parser.add_argument("--endpoint_id", type=str, required=True, help="Alphanumeric Endpoint ID")
    parser.add_argument("--prompt", type=str, default="What are the core traits of a Fighter?", help="Prompt to send")
    parser.add_argument("--project", type=str, default=os.getenv("GOOGLE_CLOUD_PROJECT"), help="GCP Project ID")
    parser.add_argument("--location", type=str, default=os.getenv("GOOGLE_CLOUD_LOCATION", "us-east4"), help="GCP Region")

    args = parser.parse_args()
    predict_custom_trained_model_sample(args.project, args.endpoint_id, args.prompt, args.location)