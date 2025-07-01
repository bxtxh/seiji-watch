# Input variables for Diet Issue Tracker infrastructure

variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region for resources"
  type        = string
  default     = "asia-northeast1"
}

variable "zone" {
  description = "The GCP zone for resources"
  type        = string
  default     = "asia-northeast1-a"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "seiji-watch"
}

# Database variables
variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"
}

variable "db_disk_size" {
  description = "Cloud SQL disk size in GB"
  type        = number
  default     = 20
}

variable "db_backup_enabled" {
  description = "Enable Cloud SQL backups"
  type        = bool
  default     = true
}

# Cloud Run variables
variable "cloud_run_cpu" {
  description = "CPU allocation for Cloud Run services"
  type        = string
  default     = "1"
}

variable "cloud_run_memory" {
  description = "Memory allocation for Cloud Run services"
  type        = string
  default     = "512Mi"
}

variable "cloud_run_min_instances" {
  description = "Minimum instances for Cloud Run services"
  type        = number
  default     = 0
}

variable "cloud_run_max_instances" {
  description = "Maximum instances for Cloud Run services"
  type        = number
  default     = 10
}

# Storage variables
variable "storage_location" {
  description = "Location for Cloud Storage bucket"
  type        = string
  default     = "ASIA-NORTHEAST1"
}

variable "storage_class" {
  description = "Storage class for Cloud Storage bucket"
  type        = string
  default     = "STANDARD"
}