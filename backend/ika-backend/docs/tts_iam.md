# Text-to-Speech IAM and permissions

The `/generate-audio` endpoint uses **Google Cloud Text-to-Speech**. The Cloud Run service account must be allowed to call the TTS API.

**Service account (Cloud Run):**  
`ika-cloudrun-sa@ikause.iam.gserviceaccount.com`

## Do not hardcode role names

Role names and permission strings can change. Do **not** assume `roles/texttospeech.user` or custom roles like `texttospeech.synthesize` exist in your project. Verify using the methods below.

## How to verify required permissions

1. **Enable the API**  
   In Google Cloud Console: **APIs & Services** → enable **Cloud Text-to-Speech API** for the project.

2. **List testable permissions for TTS**  
   In a terminal (with `gcloud` and project set):
   ```bash
   gcloud iam list-testable-permissions //cloudresourcemanager.googleapis.com/projects/ikause \
     --filter="texttospeech" \
     --format="table(name)"
   ```
   Or search in the [IAM permissions reference](https://cloud.google.com/iam/docs/permissions-reference) for “Text-to-Speech” to see the correct permission names.

3. **Grant access to the service account**  
   - In Console: **IAM & Admin** → find `ika-cloudrun-sa@ikause.iam.gserviceaccount.com` → Edit → Add another role.  
   - Choose a role that includes Text-to-Speech (e.g. a role that lists the relevant TTS permission), or create a custom role with only the needed permission if your org requires it.  
   - For quick testing, project **Editor** is sufficient; restrict to a TTS-specific role later.

4. **If the app returns 500 with an IAM/permission message**  
   - Check Cloud Run logs for the exact error (e.g. `PermissionDenied`).  
   - Ensure the service account has a role that includes the permission required by the Text-to-Speech API (see Google’s current documentation for the exact permission name).  
   - After changing IAM, no redeploy is needed; the next request uses the new permissions.

## Clear error when permission is missing

If the TTS client raises a permission error, the backend returns **HTTP 500** with a JSON body that points to this doc, e.g.:

```json
{
  "error": "Audio generation failed (likely IAM/permission). See docs/tts_iam.md.",
  "request_id": "..."
}
```

Use that and the Cloud Run logs to confirm and fix IAM.
