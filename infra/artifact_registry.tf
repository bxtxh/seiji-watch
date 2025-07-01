# Artifact Registry for container images

resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = "${var.app_name}-${var.environment}"
  description   = "Container registry for ${var.app_name} ${var.environment} environment"
  format        = "DOCKER"

  labels = {
    environment = var.environment
    app         = var.app_name
  }

  cleanup_policies {
    id     = "keep-minimum-versions"
    action = "KEEP"
    
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-old-versions"
    action = "DELETE"
    
    condition {
      tag_state    = "TAGGED"
      tag_prefixes = ["v"]
      older_than   = "2592000s" # 30 days
    }
  }

  depends_on = [google_project_service.required_apis]
}

# IAM for Cloud Run to pull images
resource "google_artifact_registry_repository_iam_member" "cloud_run_reader" {
  location   = google_artifact_registry_repository.main.location
  repository = google_artifact_registry_repository.main.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.cloud_run.email}"
}

# IAM for GitHub Actions to push images
resource "google_artifact_registry_repository_iam_member" "github_actions_writer" {
  location   = google_artifact_registry_repository.main.location
  repository = google_artifact_registry_repository.main.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.github_actions.email}"
}