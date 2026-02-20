import os
import argparse
from google.cloud import storage

def download_gcs_folder(bucket_name, source_folder, destination_local_folder, credentials_path=None):
    """Downloads a folder from GCS to local directory using credentials or ADC."""
    
    # Initialize the client
    if credentials_path:
        print(f"Using service account key from {credentials_path}...")
        storage_client = storage.Client.from_service_account_json(credentials_path)
    else:
        print("Using Application Default Credentials (ADC)...")
        # Ensure you've run 'gcloud auth application-default login' 
        # or that the VM has a Service Account with Storage Object Viewer role.
        storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)
    
    # Ensure source_folder ends with / if provided, but prefix works without it too
    prefix = source_folder if source_folder.endswith('/') or not source_folder else source_folder + '/'
    blobs = bucket.list_blobs(prefix=prefix)

    if not os.path.exists(destination_local_folder):
        os.makedirs(destination_local_folder)

    print(f"Downloading from gs://{bucket_name}/{prefix} to {destination_local_folder}...")

    count = 0
    for blob in blobs:
        if blob.name.endswith('/'): # Skip directory markers
            continue
            
        # Preserving folder structure relative to the prefix
        rel_path = os.path.relpath(blob.name, prefix)
        local_file_path = os.path.join(destination_local_folder, rel_path)
        
        local_dir = os.path.dirname(local_file_path)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        print(f"  Downloading {blob.name}...")
        blob.download_to_filename(local_file_path)
        count += 1

    if count == 0:
        print(f"Warning: No files found with prefix gs://{bucket_name}/{prefix}")
    else:
        print(f"Finished! Downloaded {count} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download a GCS folder locally (Private or Public).")
    parser.add_argument("--bucket", type=str, required=True, help="GCS bucket name")
    parser.add_argument("--prefix", type=str, required=True, help="Folder prefix in bucket")
    parser.add_argument("--out", type=str, default="./data", help="Local destination folder")
    parser.add_argument("--creds", type=str, default=None, help="Optional: Path to service_account.json key")

    args = parser.parse_args()
    download_gcs_folder(args.bucket, args.prefix, args.out, args.creds)
