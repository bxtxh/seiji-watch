# IAM and Secret Manager configuration

# Service Account for GitHub Actions
resource "google_service_account" "github_actions" {
  account_id   = "${var.app_name}-github-actions-${var.environment}"
  display_name = "GitHub Actions Service Account for ${var.app_name} ${var.environment}"
  description  = "Service account used by GitHub Actions for CI/CD"
}

# GitHub Actions IAM roles
resource "google_project_iam_member" "github_actions_cloud_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_actions_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_actions_iam_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# Secret Manager secrets
resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "${var.app_name}-openai-api-key-${var.environment}"
  
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

# Placeholder version for OpenAI API key (to be updated manually)
resource "google_secret_manager_secret_version" "openai_api_key" {
  secret      = google_secret_manager_secret.openai_api_key.id
  secret_data = "PLACEHOLDER_UPDATE_THIS_VALUE"

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "${var.app_name}-jwt-secret-${var.environment}"
  
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

resource "random_password" "jwt_secret" {
  length  = 32
  special = true
}

resource "google_secret_manager_secret_version" "jwt_secret" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = random_password.jwt_secret.result
}

# IAM for accessing secrets
resource "google_secret_manager_secret_iam_member" "cloud_run_openai_accessor" {
  secret_id = google_secret_manager_secret.openai_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_secret_manager_secret_iam_member" "cloud_run_jwt_accessor" {
  secret_id = google_secret_manager_secret.jwt_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}

# IAM for accessing Airtable secrets
resource "google_secret_manager_secret_iam_member" "cloud_run_airtable_api_accessor" {
  secret_id = google_secret_manager_secret.airtable_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_secret_manager_secret_iam_member" "cloud_run_airtable_base_accessor" {
  secret_id = google_secret_manager_secret.airtable_base_id.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}

# IAM for accessing Weaviate secrets
resource "google_secret_manager_secret_iam_member" "cloud_run_weaviate_api_accessor" {
  secret_id = google_secret_manager_secret.weaviate_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_secret_manager_secret_iam_member" "cloud_run_weaviate_url_accessor" {
  secret_id = google_secret_manager_secret.weaviate_cluster_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Service account key for GitHub Actions
resource "google_service_account_key" "github_actions" {
  service_account_id = google_service_account.github_actions.name
  public_key_type    = "TYPE_X509_PEM_FILE"
}

# Cloud Scheduler for periodic jobs
resource "google_cloud_scheduler_job" "daily_ingestion" {
  count = var.environment == "prod" ? 1 : 0
  
  name             = "${var.app_name}-daily-ingestion-${var.environment}"
  description      = "Daily Diet data ingestion job"
  schedule         = "0 2 * * *"  # 2 AM JST daily
  time_zone        = "Asia/Tokyo"
  attempt_deadline = "3600s"

  pubsub_target {
    topic_name = google_pubsub_topic.ingest_jobs.id
    data       = base64encode(jsonencode({
      job_type = "daily_ingestion"
      source   = "scheduler"
    }))
  }

  retry_config {
    retry_count = 3
  }

  depends_on = [google_project_service.required_apis]
}