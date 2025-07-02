# Cloud Run services for MVP architecture

# Service Account for Cloud Run
resource "google_service_account" "cloud_run" {
  account_id   = "${var.app_name}-cloud-run-${var.environment}"
  display_name = "Cloud Run Service Account for ${var.app_name} ${var.environment}"
  description  = "Service account used by Cloud Run services"
}

# IAM roles for Cloud Run service account
resource "google_project_iam_member" "cloud_run_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_project_iam_member" "cloud_run_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_project_iam_member" "cloud_run_pubsub_editor" {
  project = var.project_id
  role    = "roles/pubsub.editor"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Cloud Run service for API Gateway
resource "google_cloud_run_service" "api_gateway" {
  name     = "${var.app_name}-api-gateway-${var.environment}"
  location = var.region

  template {
    metadata {
      labels = {
        environment = var.environment
        app         = var.app_name
        service     = "api-gateway"
      }
      annotations = {
        "autoscaling.knative.dev/minScale"      = var.cloud_run_min_instances
        "autoscaling.knative.dev/maxScale"      = var.cloud_run_max_instances
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.connector.id
        "run.googleapis.com/vpc-access-egress"    = "private-ranges-only"
      }
    }

    spec {
      service_account_name = google_service_account.cloud_run.email
      
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.main.repository_id}/api-gateway:latest"
        
        ports {
          container_port = 8000
        }

        resources {
          limits = {
            cpu    = var.cloud_run_cpu
            memory = var.cloud_run_memory
          }
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "GCS_BUCKET_NAME"
          value = google_storage_bucket.main.name
        }

        env {
          name  = "GCS_TEMP_BUCKET_NAME"  
          value = google_storage_bucket.temp.name
        }

        env {
          name = "OPENAI_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.openai_api_key.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "AIRTABLE_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.airtable_api_key.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "AIRTABLE_BASE_ID"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.airtable_base_id.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "WEAVIATE_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.weaviate_api_key.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "WEAVIATE_CLUSTER_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.weaviate_cluster_url.secret_id
              key  = "latest"
            }
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.required_apis,
    google_vpc_access_connector.connector
  ]
}

# Cloud Run service for Ingest Worker
resource "google_cloud_run_service" "ingest_worker" {
  name     = "${var.app_name}-ingest-worker-${var.environment}"
  location = var.region

  template {
    metadata {
      labels = {
        environment = var.environment
        app         = var.app_name
        service     = "ingest-worker"
      }
      annotations = {
        "autoscaling.knative.dev/minScale"      = "0"
        "autoscaling.knative.dev/maxScale"      = "5"
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.connector.id
        "run.googleapis.com/vpc-access-egress"    = "private-ranges-only"
      }
    }

    spec {
      service_account_name = google_service_account.cloud_run.email
      timeout_seconds      = 3600  # 1 hour for long-running processing
      
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.main.repository_id}/ingest-worker:latest"
        
        ports {
          container_port = 8080
        }

        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "GCS_BUCKET_NAME"
          value = google_storage_bucket.main.name
        }

        env {
          name  = "GCS_TEMP_BUCKET_NAME"
          value = google_storage_bucket.temp.name
        }

        env {
          name = "OPENAI_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.openai_api_key.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "AIRTABLE_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.airtable_api_key.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "AIRTABLE_BASE_ID"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.airtable_base_id.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "WEAVIATE_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.weaviate_api_key.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "WEAVIATE_CLUSTER_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.weaviate_cluster_url.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name  = "PUBSUB_TOPIC"
          value = google_pubsub_topic.ingest_jobs.name
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.required_apis,
    google_vpc_access_connector.connector
  ]
}

# VPC Connector for Cloud Run services
resource "google_vpc_access_connector" "connector" {
  name          = "${var.app_name}-vpc-connector-${var.environment}"
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc.name
  region        = var.region
  
  min_throughput = 200
  max_throughput = var.environment == "prod" ? 1000 : 300

  depends_on = [google_project_service.required_apis]
}

# IAM policy for API Gateway public access
data "google_iam_policy" "api_gateway_public" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "api_gateway_public" {
  location = google_cloud_run_service.api_gateway.location
  project  = google_cloud_run_service.api_gateway.project
  service  = google_cloud_run_service.api_gateway.name

  policy_data = data.google_iam_policy.api_gateway_public.policy_data
}

# Pub/Sub for job processing
resource "google_pubsub_topic" "ingest_jobs" {
  name = "${var.app_name}-ingest-jobs-${var.environment}"

  labels = {
    environment = var.environment
    app         = var.app_name
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_pubsub_subscription" "ingest_jobs" {
  name  = "${var.app_name}-ingest-jobs-sub-${var.environment}"
  topic = google_pubsub_topic.ingest_jobs.name

  ack_deadline_seconds = 600

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }

  depends_on = [google_pubsub_topic.dead_letter]
}

resource "google_pubsub_topic" "dead_letter" {
  name = "${var.app_name}-dead-letter-${var.environment}"

  labels = {
    environment = var.environment
    app         = var.app_name
  }

  depends_on = [google_project_service.required_apis]
}