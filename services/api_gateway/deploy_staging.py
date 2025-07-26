#!/usr/bin/env python3
"""
Direct deployment of staging API Gateway
"""
import os
import subprocess
import sys

def run_command(cmd):
    """Run shell command and handle errors"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(f"Success: {result.stdout}")
    return True

def main():
    """Deploy API Gateway staging environment"""
    
    # Get project info
    project_id = "gen-lang-client-0458605339"
    region = "asia-northeast1"
    image_name = f"{region}-docker.pkg.dev/{project_id}/seiji-watch-staging/api-gateway:manual"
    
    print("Building and deploying API Gateway for staging...")
    
    # Step 1: Build image locally
    if not run_command("docker buildx build --platform linux/amd64 -t api-gateway:manual -f Dockerfile.simple ."):
        return False
    
    # Step 2: Tag for registry
    if not run_command(f"docker tag api-gateway:manual {image_name}"):
        return False
    
    # Step 3: Try push with retries
    max_retries = 3
    for attempt in range(max_retries):
        print(f"Push attempt {attempt + 1}/{max_retries}")
        if run_command(f"docker push {image_name}"):
            break
        if attempt == max_retries - 1:
            print("Push failed after all retries")
            return False
    
    # Step 4: Deploy to Cloud Run
    deploy_cmd = f"""
    gcloud run deploy seiji-watch-api-gateway-staging \\
      --image={image_name} \\
      --region={region} \\
      --platform=managed \\
      --port=8000 \\
      --memory=1Gi \\
      --cpu=1 \\
      --update-env-vars=AIRTABLE_API_KEY=dummy,AIRTABLE_BASE_ID=dummy \\
      --service-account=seiji-cr-staging@{project_id}.iam.gserviceaccount.com \\
      --allow-unauthenticated
    """
    
    if not run_command(deploy_cmd):
        return False
    
    print("✅ API Gateway deployed successfully!")
    print(f"🔗 Service URL: https://seiji-watch-api-gateway-staging-496359339214.{region}.run.app")
    
    return True

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)