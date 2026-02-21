#!/bin/bash
# cloud_run/update_endpoint.sh

# Configuration
SERVICE_NAME="rollmind-api"
REGION="us-east4"

# Get Endpoint ID from argument or prompt
NEW_ID=$1

if [ -z "$NEW_ID" ]; then
    echo "Current Region: $REGION"
    echo "Current Service: $SERVICE_NAME"
    read -p "Enter the new Vertex Endpoint ID: " NEW_ID
fi

if [ -z "$NEW_ID" ]; then
    echo "❌ Error: Vertex Endpoint ID is required."
    exit 1
fi

echo "🔄 Updating Cloud Run service environment variables..."
# This will trigger a new revision of the service with the updated ID.
# It is persistent and will be used by all new instances.
gcloud run services update $SERVICE_NAME 
    --platform managed 
    --region $REGION 
    --update-env-vars="VERTEX_ENDPOINT_ID=$NEW_ID"

echo "✨ Successfully updated $SERVICE_NAME to use Vertex Endpoint: $NEW_ID"
echo "Note: It may take a few seconds for the new revision to start serving traffic."
