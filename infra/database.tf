# Cloud SQL PostgreSQL instance with pgvector support

# Generate random password for database
resource "random_password" "db_password" {
  length  = 16
  special = true
}

# Store password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.app_name}-db-password-${var.environment}"
  
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# Cloud SQL instance
resource "google_sql_database_instance" "main" {
  name             = "${var.app_name}-db-${var.environment}-${local.name_suffix}"
  database_version = "POSTGRES_15"
  region           = var.region
  deletion_protection = var.environment == "prod" ? true : false

  settings {
    tier                        = var.db_tier
    availability_type          = var.environment == "prod" ? "REGIONAL" : "ZONAL"
    disk_size                  = var.db_disk_size
    disk_type                  = "PD_SSD"
    disk_autoresize           = true
    disk_autoresize_limit     = 100

    database_flags {
      name  = "shared_preload_libraries"
      value = "vector"
    }

    backup_configuration {
      enabled                        = var.db_backup_enabled
      start_time                     = "03:00"
      point_in_time_recovery_enabled = var.environment == "prod" ? true : false
      backup_retention_settings {
        retained_backups = var.environment == "prod" ? 30 : 7
      }
    }

    ip_configuration {
      ipv4_enabled    = true
      private_network = google_compute_network.vpc.id
      require_ssl     = true
      
      dynamic "authorized_networks" {
        for_each = var.environment == "dev" ? [1] : []
        content {
          name  = "allow-all-dev"
          value = "0.0.0.0/0"
        }
      }
    }

    maintenance_window {
      day          = 7
      hour         = 4
      update_track = "stable"
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
  }

  depends_on = [
    google_project_service.required_apis,
    google_compute_network.vpc,
    google_compute_global_address.private_ip_address
  ]
}

# Database
resource "google_sql_database" "app_db" {
  name     = "${var.app_name}_${var.environment}"
  instance = google_sql_database_instance.main.name
}

# Database user
resource "google_sql_user" "app_user" {
  name     = "${var.app_name}_user"
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result
}

# VPC for private IP
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

  secondary_ip_range {
    range_name    = "services-range"
    ip_cidr_range = "10.1.0.0/24"
  }

  secondary_ip_range {
    range_name    = "pod-ranges"
    ip_cidr_range = "10.2.0.0/24"
  }
}

# Reserve IP range for private services
resource "google_compute_global_address" "private_ip_address" {
  name          = "${var.app_name}-private-ip-${var.environment}"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

# Create private connection
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# Firewall rules
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.app_name}-allow-internal-${var.environment}"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = ["10.0.0.0/8"]
}