#!/bin/bash
# cloud_run/deploy_vertex_proxy.sh

# Configuration (Defaults)
PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="rollmind-api"
REGION="us-east4"
REPO_NAME="ostamand"
# Artifact Registry format: REGION-docker.pkg.dev/PROJECT_ID/REPO_NAME/IMAGE_NAME
IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME"

# Check for required Vertex Endpoint ID
if [ -z "$VERTEX_ENDPOINT_ID" ]; then
    echo "⚠️  Warning: VERTEX_ENDPOINT_ID environment variable is not set."
    echo "You can provide it now or set it later in the Cloud Run console."
    read -p "Enter Vertex Endpoint ID (optional): " VERTEX_ENDPOINT_ID
fi

# Ensure the Artifact Registry repository exists
echo "🔍 Checking for Artifact Registry repository: $REPO_NAME..."
gcloud artifacts repositories describe $REPO_NAME --location=$REGION > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "🏗️  Creating Artifact Registry repository: $REPO_NAME..."
    gcloud artifacts repositories create $REPO_NAME \
        --repository-format=docker \
        --location=$REGION \
        --description="RollMind API Container Repository"
fi

echo "📦 Building lightweight RollMind API image for Vertex mode..."
# Build from root
docker build -t $IMAGE_NAME -f app/api/Dockerfile.vertex .

echo "🚀 Pushing image to Artifact Registry..."
# Configure docker for this region if not already done
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet
docker push $IMAGE_NAME

echo "🌐 Deploying to Cloud Run (Standard CPU)..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars="INFERENCE_MODE=vertex,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,VERTEX_ENDPOINT_ID=$VERTEX_ENDPOINT_ID"

echo "✨ Deployment complete!"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format='value(status.url)')
echo "URL: $SERVICE_URL"
echo "Health check: $SERVICE_URL/health"
