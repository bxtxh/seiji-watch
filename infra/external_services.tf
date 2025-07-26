# External services configuration: Airtable + Weaviate Cloud
# Replaces Cloud SQL setup for cost optimization and simplicity

# Airtable PAT (Personal Access Token) secrets
resource "google_secret_manager_secret" "airtable_pat" {
  secret_id = "${var.app_name}-airtable-pat-${var.environment}"
  
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "airtable_pat" {
  secret      = google_secret_manager_secret.airtable_pat.id
  secret_data = "PLACEHOLDER_AIRTABLE_PAT"
  
  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "airtable_base_id" {
  secret_id = "${var.app_name}-airtable-base-id-${var.environment}"
  
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "airtable_base_id" {
  secret      = google_secret_manager_secret.airtable_base_id.id
  secret_data = "PLACEHOLDER_AIRTABLE_BASE_ID"
  
  lifecycle {
    ignore_changes = [secret_data]
  }
}

# Weaviate Cloud API secrets
resource "google_secret_manager_secret" "weaviate_api_key" {
  secret_id = "${var.app_name}-weaviate-api-key-${var.environment}"
  
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "weaviate_api_key" {
  secret      = google_secret_manager_secret.weaviate_api_key.id
  secret_data = "PLACEHOLDER_WEAVIATE_API_KEY"
  
  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "weaviate_cluster_url" {
  secret_id = "${var.app_name}-weaviate-cluster-url-${var.environment}"
  
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "weaviate_cluster_url" {
  secret      = google_secret_manager_secret.weaviate_cluster_url.id
  secret_data = "PLACEHOLDER_WEAVIATE_CLUSTER_URL"
  
  lifecycle {
    ignore_changes = [secret_data]
  }
}

# Simplified VPC for Cloud Run (no Cloud SQL private access needed)
resource "google_compute_network" "vpc" {
  name                    = "${var.app_name}-vpc-${var.environment}"
  auto_create_subnetworks = false
  mtu                     = 1460
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${var.app_name}-subnet-${var.environment}"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id

  # Simplified IP ranges for Cloud Run only
  secondary_ip_range {
    range_name    = "services-range"
    ip_cidr_range = "10.1.0.0/24"
  }
}

# Basic firewall rules for Cloud Run
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.app_name}-allow-internal-${var.environment}"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["8000", "8080", "3000"]  # Specific ports for our services
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = ["10.0.0.0/8"]
}

# Internet access for Cloud Run
resource "google_compute_firewall" "allow_http_https" {
  name    = "${var.app_name}-allow-http-https-${var.environment}"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["http-server", "https-server"]
}