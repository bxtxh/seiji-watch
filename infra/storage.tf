# Cloud Storage for raw files and processed data

# Main storage bucket for raw files
resource "google_storage_bucket" "main" {
  name          = "${var.app_name}-${var.environment}-${local.name_suffix}"
  location      = var.storage_location
  storage_class = var.storage_class
  
  # Prevent accidental deletion
  force_destroy = var.environment == "prod" ? false : true

  uniform_bucket_level_access = true

  versioning {
    enabled = var.environment == "prod" ? true : false
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass" 
      storage_class = "ARCHIVE"
    }
  }

  # CORS for frontend uploads (if needed)
  cors {
    origin          = var.environment == "prod" ? ["https://seiji-watch.com"] : ["http://localhost:3000", "https://*.run.app"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  labels = {
    environment = var.environment
    app         = var.app_name
  }

  depends_on = [google_project_service.required_apis]
}

# Bucket for temporary processing files
resource "google_storage_bucket" "temp" {
  name          = "${var.app_name}-temp-${var.environment}-${local.name_suffix}"
  location      = var.storage_location
  storage_class = "STANDARD"
  
  force_destroy = true

  uniform_bucket_level_access = true

  # Auto-delete files after 7 days
  lifecycle_rule {
    condition {
      age = 7
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    environment = var.environment
    app         = var.app_name
    purpose     = "temporary"
  }

  depends_on = [google_project_service.required_apis]
}

# IAM for Cloud Run services to access storage
resource "google_storage_bucket_iam_member" "cloud_run_object_admin" {
  bucket = google_storage_bucket.main.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_storage_bucket_iam_member" "cloud_run_temp_admin" {
  bucket = google_storage_bucket.temp.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run.email}"
}

# IAM for GitHub Actions to access storage (for deployments)
resource "google_storage_bucket_iam_member" "github_actions_viewer" {
  bucket = google_storage_bucket.main.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.github_actions.email}"
}