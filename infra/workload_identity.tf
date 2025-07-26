# Workload Identity Federation configuration for GitHub Actions
# This enables keyless authentication from GitHub Actions to GCP

locals {
  project_number = data.google_project.project.number
  pool_id        = "github-actions-pool"
  provider_id    = "github-actions-provider"
}

# Get current project data
data "google_project" "project" {}

# Create Workload Identity Pool
resource "google_iam_workload_identity_pool" "github_actions" {
  workload_identity_pool_id = local.pool_id
  display_name              = "GitHub Actions Pool"
  description               = "Workload Identity Pool for GitHub Actions CI/CD"
  disabled                  = false
}

# Create Workload Identity Provider
resource "google_iam_workload_identity_pool_provider" "github_actions" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_actions.workload_identity_pool_id
  workload_identity_pool_provider_id = local.provider_id
  display_name                       = "GitHub Actions Provider"
  description                        = "OIDC provider for GitHub Actions"
  
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
  }
  
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
  
  # Only allow from our repository
  attribute_condition = "assertion.repository_owner == 'bxtxh'"
}

# Create service account for GitHub Actions
resource "google_service_account" "github_actions" {
  account_id   = "github-actions-sa"
  display_name = "GitHub Actions Service Account"
  description  = "Service account for GitHub Actions CI/CD (WIF enabled)"
}

# Grant the service account necessary permissions
resource "google_project_iam_member" "github_actions_roles" {
  for_each = toset([
    "roles/run.admin",
    "roles/storage.admin",
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/iam.serviceAccountUser"
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# Allow GitHub Actions to impersonate the service account
resource "google_service_account_iam_member" "github_actions_workload_identity" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${local.project_number}/locations/global/workloadIdentityPools/${local.pool_id}/attribute.repository/bxtxh/seiji-watch"
}

# Output values for GitHub Actions configuration
output "workload_identity_provider" {
  value = "projects/${local.project_number}/locations/global/workloadIdentityPools/${local.pool_id}/providers/${local.provider_id}"
  description = "Workload Identity Provider for GitHub Actions"
}

output "service_account_email" {
  value = google_service_account.github_actions.email
  description = "Service account email for GitHub Actions"
}