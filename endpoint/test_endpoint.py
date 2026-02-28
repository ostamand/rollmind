import os
import argparse
import json
from google.cloud import aiplatform
from dotenv import load_dotenv

load_dotenv()

def predict_custom_trained_model_sample(
    project: str,
    endpoint_id: str,
    prompt: str,
    location: str = "us-east4",
):
    # 1. Initialize Vertex AI
    aiplatform.init(project=project, location=location)
    endpoint = aiplatform.Endpoint(endpoint_name=endpoint_id)

    print(f"Sending OpenAI-formatted request to Vertex endpoint {endpoint_id}...")
    
    # 2. Format the payload EXACTLY as the OpenAI API expects it
    # We no longer need manual <start_of_turn> tags; vLLM handles the chat template.
    openai_payload = {
        "model": "gemma", # vLLM usually ignores this if only one model is loaded
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 400,
        "temperature": 0.7,
        "top_p": 0.9,
    }
    
    try:
        # 3. Use raw_predict to bypass Vertex's proprietary formatting
        response = endpoint.raw_predict(
            body=json.dumps(openai_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        
        # 4. Parse the standard OpenAI JSON response
        response_data = json.loads(response.text)
        
        # Catch strict model name errors (in case vLLM demands the exact /tmp/ path)
        if "error" in response_data:
            print(f"❌ API Error: {response_data['error']}")
            return

        print("\n--- RESPONSE ---")
        if "choices" in response_data and len(response_data["choices"]) > 0:
            print(response_data["choices"][0]["message"]["content"].strip())
        else:
            print("Unrecognized format. Raw Response:", json.dumps(response_data, indent=2))
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        if hasattr(e, 'response'):
             print(f"Raw output: {e.response.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Vertex AI Endpoint")
    parser.add_argument("--endpoint_id", type=str, required=True, help="Alphanumeric Endpoint ID")
    parser.add_argument("--prompt", type=str, default="What are the core traits of a Fighter?", help="Prompt to send")
    parser.add_argument("--project", type=str, default=os.getenv("GOOGLE_CLOUD_PROJECT"), help="GCP Project ID")
    parser.add_argument("--location", type=str, default=os.getenv("GOOGLE_CLOUD_LOCATION", "us-east4"), help="GCP Region")

    args = parser.parse_args()
    predict_custom_trained_model_sample(args.project, args.endpoint_id, args.prompt, args.location)