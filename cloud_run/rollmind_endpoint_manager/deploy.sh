#!/bin/bash
# cloud_run/rollmind_endpoint_manager/deploy.sh
set -e

# Configuration
PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="rollmind-endpoint-manager"
REGION="us-east4"
REPO_NAME="ostamand"
IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME"

SERVICE_ACCOUNT="rollmind-api@ostamand-264a1.iam.gserviceaccount.com"

echo "🔍 Checking for Artifact Registry repository: $REPO_NAME..."
gcloud artifacts repositories describe $REPO_NAME --location=$REGION > /dev/null 2>&1 || \
gcloud artifacts repositories create $REPO_NAME --repository-format=docker --location=$REGION

echo "📦 Building RollMind Endpoint Manager image..."
# Build from root to include endpoint/ package
cd ../..
docker build -t $IMAGE_NAME -f cloud_run/rollmind_endpoint_manager/Dockerfile .

echo "🚀 Pushing image..."
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet
docker push $IMAGE_NAME

echo "🌐 Deploying to Cloud Run (Private)..."
# We DO NOT use --allow-unauthenticated to keep it private
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --no-allow-unauthenticated \
    --service-account=$SERVICE_ACCOUNT \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION"

echo "✨ Deployment complete!"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format='value(status.url)')
echo "URL: $SERVICE_URL"
echo "Example toggle off: $SERVICE_URL/toggle?action=off"
