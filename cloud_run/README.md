# Cloud Run Deployment (Vertex Proxy Mode)

This approach deploys the RollMind API to **Cloud Run (CPU)**. It acts as a lightweight proxy that forwards all inquiries to your **Vertex AI Endpoint**.

## Why this is optimal:
1.  **Fast Cold Starts:** Because it doesn't load PyTorch or 15GB of weights, the container starts in **less than 1 second**.
2.  **True Serverless Cost:** Cloud Run scales to zero. You only pay for the few seconds it takes to process a request.
3.  **No GPU Needed on Cloud Run:** The expensive GPU heavy-lifting is done by your Vertex AI Endpoint.

---

## 🚀 Deployment Instructions

1.  **Ensure you have an active Vertex AI Endpoint.** (See `endpoint/README.md`)
2.  **Run the deployment script:**
    ```bash
    ./cloud_run/deploy_vertex_proxy.sh
    ```
3.  **Update your frontend:** Once deployed, the script will output a URL (e.g., `https://rollmind-api-xyz.a.run.app`). Use this as your API base URL in your production frontend.

---

## 🛠️ How it works
- **`Dockerfile.vertex`**: Uses a tiny `python:slim` image. It **skips** installing `torch`, `transformers`, and `peft`.
- **`model.py` (Lazy Imports)**: The backend code has been refactored to only import heavy ML libraries if `INFERENCE_MODE=local`. In Cloud Run, it stays in `vertex` mode and remains extremely light.
