import requests
import json
import argparse

def test_local_vllm(prompt, port=8080):
    url = f"http://localhost:{port}/generate"
    
    # Vertex AI Custom Container (vLLM) expects this structure:
    # { "prompt": "...", "max_tokens": ..., "temperature": ..., "top_p": ... }
    # Or sometimes { "instances": [...] } but Google's vLLM-serve wrapper
    # usually maps the request to its /generate endpoint.
    
    formatted_prompt = f"<start_of_turn>user
{prompt}<end_of_turn>
<start_of_turn>model
"
    
    payload = {
        "prompt": formatted_prompt,
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.9,
    }

    print(f"📡 Sending request to {url}...")
    try:
        # Check Health first
        health_url = f"http://localhost:{port}/ping"
        health_resp = requests.get(health_url)
        print(f"❤️ Health Check (/ping): {health_resp.status_code}")
        
        # Send Prediction
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            print("
✅ SUCCESS!")
            print("-" * 50)
            print("RESPONSE:")
            # vLLM-serve usually returns a JSON object with predictions
            result = response.json()
            # If it returns a list of predictions like Vertex
            if "predictions" in result:
                print(result["predictions"][0])
            else:
                # If it's a direct vLLM response
                print(json.dumps(result, indent=2))
            print("-" * 50)
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("Is the Docker container running?")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test local vLLM serving container")
    parser.add_argument("--prompt", type=str, default="Explain the core class feature of a Druid.", help="Prompt to send")
    parser.add_argument("--port", type=int, default=8080, help="Local port (default: 8080)")
    
    args = parser.parse_args()
    test_local_vllm(args.prompt, args.port)
