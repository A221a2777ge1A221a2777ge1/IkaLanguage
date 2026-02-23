# GCP Setup Script

This script sets up a GCP project for Cloud Run deployment by creating a service account, granting necessary roles, and enabling required APIs.

## Prerequisites

- Google Cloud SDK (gcloud) installed
- Authenticated with GCP (run `gcloud auth login`)
- Appropriate permissions to create service accounts and manage IAM roles

## Usage in Cloud Shell

1. **Open Google Cloud Shell** from the [Cloud Console](https://console.cloud.google.com/)

2. **Navigate to the project directory** (if you need to upload the script first):
   ```bash
   cd ~
   # If you need to upload the script, use the Cloud Shell editor or upload via the UI
   ```

3. **Make the script executable**:
   ```bash
   chmod +x backend/scripts/setup_gcp.sh
   ```

4. **Set environment variables and run the script**:
   ```bash
   export PROJECT_ID=your-project-id
   export REGION=your-region
   ./backend/scripts/setup_gcp.sh
   ```

   Or run in a single line:
   ```bash
   PROJECT_ID=your-project-id REGION=your-region ./backend/scripts/setup_gcp.sh
   ```

## What the Script Does

1. **Creates a service account** named `ika-cloudrun-sa` (if it doesn't exist)
2. **Grants the following roles** to the service account:
   - `roles/datastore.user` - Access to Cloud Datastore
   - `roles/storage.objectAdmin` - Full control over Cloud Storage objects
   - `roles/iam.serviceAccountTokenCreator` - Ability to create tokens for service accounts
   - `roles/secretmanager.secretAccessor` - (Optional, commented out) Access to Secret Manager secrets

3. **Enables the following APIs**:
   - `run.googleapis.com` - Cloud Run API
   - `cloudbuild.googleapis.com` - Cloud Build API
   - `artifactregistry.googleapis.com` - Artifact Registry API
   - `iam.googleapis.com` - Identity and Access Management API

4. **Outputs the service account email** at the end

## Idempotency

The script is idempotent and safe to run multiple times. It will:
- Skip service account creation if it already exists
- Add IAM policy bindings (which are idempotent operations)
- Enable APIs (which are idempotent operations)

## Enabling Secret Manager Access

If you need Secret Manager access, uncomment the relevant section in the script (around line 60-65) and run the script again.

## Example Output

```
Setting up GCP project: my-project-id in region: us-central1
Checking for service account: ika-cloudrun-sa
Creating service account: ika-cloudrun-sa
Service account created successfully
Granting roles to service account...
...
==========================================
Setup completed successfully!
Service Account Email: ika-cloudrun-sa@my-project-id.iam.gserviceaccount.com
==========================================
```
