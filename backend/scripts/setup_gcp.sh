#!/bin/bash

# GCP Setup Script for Cloud Run
# This script sets up a service account and enables required APIs for Cloud Run deployment
# Usage: PROJECT_ID=your-project-id REGION=your-region ./setup_gcp.sh

set -e  # Exit on error

# Check if required environment variables are set
if [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID environment variable is not set"
    echo "Usage: PROJECT_ID=your-project-id REGION=your-region ./setup_gcp.sh"
    exit 1
fi

if [ -z "$REGION" ]; then
    echo "Error: REGION environment variable is not set"
    echo "Usage: PROJECT_ID=your-project-id REGION=your-region ./setup_gcp.sh"
    exit 1
fi

echo "Setting up GCP project: $PROJECT_ID in region: $REGION"

# Set the project
gcloud config set project "$PROJECT_ID"

# Service account name
SERVICE_ACCOUNT_NAME="ika-cloudrun-sa"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Create service account if it doesn't exist (idempotent)
echo "Checking for service account: $SERVICE_ACCOUNT_NAME"
if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo "Creating service account: $SERVICE_ACCOUNT_NAME"
    gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
        --display-name="Cloud Run Service Account" \
        --project="$PROJECT_ID"
    echo "Service account created successfully"
else
    echo "Service account already exists, skipping creation"
fi

# Grant roles to the service account (idempotent - safe to run multiple times)
echo "Granting roles to service account..."

# Grant roles/datastore.user
echo "Granting roles/datastore.user..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/datastore.user" \
    --quiet

# Grant roles/storage.objectAdmin
echo "Granting roles/storage.objectAdmin..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/storage.objectAdmin" \
    --quiet

# Grant roles/iam.serviceAccountTokenCreator
echo "Granting roles/iam.serviceAccountTokenCreator..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --quiet

# Grant roles/secretmanager.secretAccessor (optional - commented out)
# Uncomment the following lines if you need Secret Manager access:
# echo "Granting roles/secretmanager.secretAccessor..."
# gcloud projects add-iam-policy-binding "$PROJECT_ID" \
#     --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
#     --role="roles/secretmanager.secretAccessor" \
#     --quiet

# Enable required APIs (idempotent - safe to run multiple times)
echo "Enabling required APIs..."

echo "Enabling run.googleapis.com..."
gcloud services enable run.googleapis.com --project="$PROJECT_ID"

echo "Enabling cloudbuild.googleapis.com..."
gcloud services enable cloudbuild.googleapis.com --project="$PROJECT_ID"

echo "Enabling artifactregistry.googleapis.com..."
gcloud services enable artifactregistry.googleapis.com --project="$PROJECT_ID"

echo "Enabling iam.googleapis.com..."
gcloud services enable iam.googleapis.com --project="$PROJECT_ID"

# Output the service account email
echo ""
echo "=========================================="
echo "Setup completed successfully!"
echo "Service Account Email: $SERVICE_ACCOUNT_EMAIL"
echo "=========================================="
