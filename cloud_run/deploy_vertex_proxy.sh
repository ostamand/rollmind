#!/bin/bash

# Configuration
PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="rollmind-api"
REGION="us-central1"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "📦 Building lightweight RollMind API image for Vertex mode..."
docker build -t $IMAGE_NAME -f app/api/Dockerfile.vertex .

echo "🚀 Pushing image to Google Container Registry..."
docker push $IMAGE_NAME

echo "🌐 Deploying to Cloud Run (Standard CPU)..."
gcloud run deploy $SERVICE_NAME 
    --image $IMAGE_NAME 
    --platform managed 
    --region $REGION 
    --allow-unauthenticated 
    --set-env-vars="INFERENCE_MODE=vertex,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION" 
    --memory 1Gi 
    --cpu 1

echo "✨ Deployment complete!"
gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format='value(status.url)'
