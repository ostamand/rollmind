# 🚀 RollMind Endpoint Manager

A lightweight FastAPI service deployed to Cloud Run that allows you to remotely manage your Vertex AI endpoints. Its primary purpose is **cost optimization**: enabling you to toggle expensive GPU-backed endpoints ON and OFF on demand without needing local terminal access.

## 📌 Features
- **Remote Toggle**: Turn endpoints on/off via simple HTTP GET requests.
- **Background Processing**: Vertex AI deployments take 10-15 minutes; the API returns an immediate `202 Accepted` and handles the operation in the background.
- **Private & Secure**: Deployed with IAM authentication required (`--no-allow-unauthenticated`).
- **Dry/Zero-Maintenance**: Imports logic directly from the core `endpoint/` package to ensure consistency.

## 🛠️ Prerequisites
- Google Cloud SDK (`gcloud`) configured.
- A service account with **Vertex AI Administrator** (`roles/aiplatform.admin`) permissions. 
  - *Note: "Vertex AI User" is insufficient as it does not allow deploying/undeploying models.*
- Artifact Registry enabled in your GCP project.


## 🚀 Deployment

Run the included deployment script from the root of the repository:

```bash
cd cloud_run/rollmind_endpoint_manager
./deploy.sh
```

The script will:
1. Build a Docker image from the project root (to include the `endpoint/` package).
2. Push the image to Artifact Registry.
3. Deploy the service to Cloud Run with the service account `rollmind-api@ostamand-264a1.iam.gserviceaccount.com`.

## 📡 API Usage

The service is private. You must provide a Google ID token in the `Authorization` header.

### Get Service URL
```bash
export SERVICE_URL=$(gcloud run services describe rollmind-endpoint-manager --platform managed --region us-east4 --format='value(status.url)')
```

### 🔋 Toggle OFF (Stop Billing)
Undeploys all models from the endpoint. The endpoint resource remains, but the GPU nodes are released.
```bash
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "$SERVICE_URL/toggle?action=off"
```

### 🔌 Toggle ON (Start Serving)
Deploys the specified model to the endpoint. This takes ~15 minutes.
```bash
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "$SERVICE_URL/toggle?action=on"
```

### ⚙️ Parameters
- `action`: (Required) `on` or `off`.
- `name`: (Optional) The display name of the endpoint. Defaults to `rollmind-gemma-7b_endpoint`.
- `model_name`: (Optional) The display name of the model to deploy. Defaults to `rollmind-gemma-7b`.

## 🪵 Monitoring
Since the toggle runs as a FastAPI `BackgroundTask`, you should monitor the **Cloud Run Logs** in the GCP Console to see the progress of the deployment or any errors encountered during the Vertex AI API calls.
