import os
import argparse
import subprocess
from dotenv import load_dotenv

load_dotenv()

def upload_data(bucket_name, bucket_folder):
    local_dir = "data"
    
    if not os.path.exists(local_dir):
        print(f"Error: Local directory '{local_dir}' not found.")
        return

    # Construct target URI
    target_uri = f"gs://{bucket_name}/{bucket_folder.strip('/')}"
    if not target_uri.endswith('/'):
        target_uri += '/'

    print(f"🚀 Starting optimized parallel upload of 'data/' to {target_uri}...")
    
    # Flags explained:
    # -m: Run in parallel (multiple threads/processes)
    # GSUtil:parallel_composite_upload_threshold=150M: Chunks large files for parallel streams
    try:
        subprocess.run([
            "gsutil", 
            "-m", 
            "-o", "GSUtil:parallel_composite_upload_threshold=150M", 
            "rsync", "-r", local_dir, target_uri
        ], check=True)
        print("✅ Data upload complete.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during upload: {e}")
        raise e

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload 'data/' directory to GCS")
    parser.add_argument("--bucket", type=str, required=True, help="GCS Bucket name (without gs://)")
    parser.add_argument("--folder", type=str, default="data", help="Target folder in the bucket (default: 'data')")
    
    args = parser.parse_args()
    upload_data(args.bucket, args.folder)
