# Output values for Diet Issue Tracker infrastructure

# External services outputs
output "airtable_api_key_secret_name" {
  description = "The name of the Airtable API key secret"
  value       = google_secret_manager_secret.airtable_api_key.secret_id
}

output "airtable_base_id_secret_name" {
  description = "The name of the Airtable base ID secret"
  value       = google_secret_manager_secret.airtable_base_id.secret_id
}

output "weaviate_api_key_secret_name" {
  description = "The name of the Weaviate API key secret"
  value       = google_secret_manager_secret.weaviate_api_key.secret_id
}

output "weaviate_cluster_url_secret_name" {
  description = "The name of the Weaviate cluster URL secret"
  value       = google_secret_manager_secret.weaviate_cluster_url.secret_id
}

# Storage outputs
output "storage_bucket_main" {
  description = "The name of the main storage bucket"
  value       = google_storage_bucket.main.name
}

output "storage_bucket_temp" {
  description = "The name of the temporary storage bucket"
  value       = google_storage_bucket.temp.name
}

output "storage_bucket_main_url" {
  description = "The URL of the main storage bucket"
  value       = google_storage_bucket.main.url
}

# Artifact Registry outputs
output "artifact_registry_repository" {
  description = "The name of the Artifact Registry repository"
  value       = google_artifact_registry_repository.main.name
}

output "artifact_registry_location" {
  description = "The location of the Artifact Registry repository"
  value       = google_artifact_registry_repository.main.location
}

output "docker_repository_url" {
  description = "The URL for pushing Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.main.repository_id}"
}

# Cloud Run outputs
output "api_gateway_url" {
  description = "The URL of the API Gateway Cloud Run service"
  value       = google_cloud_run_service.api_gateway.status[0].url
}

output "ingest_worker_url" {
  description = "The URL of the Ingest Worker Cloud Run service"
  value       = google_cloud_run_service.ingest_worker.status[0].url
}

# Service Account outputs
output "cloud_run_service_account_email" {
  description = "The email of the Cloud Run service account"
  value       = google_service_account.cloud_run.email
}

output "github_actions_service_account_email" {
  description = "The email of the GitHub Actions service account"
  value       = google_service_account.github_actions.email
}

output "github_actions_service_account_key" {
  description = "The private key for GitHub Actions service account (base64 encoded)"
  value       = google_service_account_key.github_actions.private_key
  sensitive   = true
}

# Secret Manager outputs
output "openai_api_key_secret_name" {
  description = "The name of the OpenAI API key secret"
  value       = google_secret_manager_secret.openai_api_key.secret_id
}

output "jwt_secret_name" {
  description = "The name of the JWT secret"
  value       = google_secret_manager_secret.jwt_secret.secret_id
}


# Pub/Sub outputs
output "pubsub_topic_ingest_jobs" {
  description = "The name of the ingest jobs Pub/Sub topic"
  value       = google_pubsub_topic.ingest_jobs.name
}

output "pubsub_subscription_ingest_jobs" {
  description = "The name of the ingest jobs Pub/Sub subscription"
  value       = google_pubsub_subscription.ingest_jobs.name
}

# Network outputs
output "vpc_network_name" {
  description = "The name of the VPC network"
  value       = google_compute_network.vpc.name
}

output "vpc_subnet_name" {
  description = "The name of the VPC subnet"
  value       = google_compute_subnetwork.subnet.name
}

output "vpc_connector_name" {
  description = "The name of the VPC access connector"
  value       = google_vpc_access_connector.connector.name
}

# Environment information
output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "The GCP region"
  value       = var.region
}

output "environment" {
  description = "The environment name"
  value       = var.environment
}