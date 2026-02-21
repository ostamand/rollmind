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

## 🔄 Updating your Endpoint ID

You can update the Vertex AI Endpoint ID of your deployed service **without** rebuilding the container:

```bash
# Provide the new ID as an argument
./cloud_run/update_endpoint.sh your-new-endpoint-id
```

This will persistently update the environment variable in Cloud Run and trigger a new revision.

---

## 📡 API Endpoints

Once deployed, the following endpoints are available:

### `GET /health`
Returns the operational status of the API.
- **Response**: `{"status": "online", "mode": "vertex", "is_loading": false}`

### `GET /config`
Returns the current configuration of the Vertex AI manager.
- **Response**: `{"mode": "vertex", "endpoint_id": "...", "status": "ready", ...}`

### `POST /config`
Update the configuration at runtime (e.g., to point to a new Vertex Endpoint).
- **Body**: `{"endpoint_id": "new-id-here"}`
- **Response**: Confirmation message with updated config.

### `POST /consult`
The main inference endpoint. It returns a **Server-Sent Events (SSE)** stream of tokens.
- **Body**: `{"prompt": "What is a Wizard?"}`
- **Response**: Stream of tokens: `data: Token1`, `data: Token2`, etc.

---

## 🔐 Security

To protect your administrative endpoints, the `/config` routes require a secret key if the `CONFIG_SECRET_KEY` environment variable is set.

- **Header**: `X-Config-Secret: your-secret-key`

**Example (cURL):**
```bash
curl -X GET https://rollmind-api-xyz.a.run.app/config \
     -H "X-Config-Secret: my-super-secret"
```

---

## 🛠️ How it works
- **`Dockerfile.vertex`**: Uses a tiny `python:slim` image. It **skips** installing `torch`, `transformers`, and `peft`.
- **`model.py` (Lazy Imports)**: The backend code has been refactored to only import heavy ML libraries if `INFERENCE_MODE=local`. In Cloud Run, it stays in `vertex` mode and remains extremely light.
