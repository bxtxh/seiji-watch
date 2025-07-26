# Identity-Aware Proxy (IAP) configuration for external user testing
# Provides secure authentication without exposing services publicly

# Enable required APIs
resource "google_project_service" "iap_api" {
  service = "iap.googleapis.com"
  disable_on_destroy = false
}

# Create OAuth2 client for IAP
resource "google_iap_client" "external_testing" {
  display_name = "External Testing OAuth Client"
  brand        = google_iap_brand.project_brand.name
}

# Create IAP brand (one per project)
resource "google_iap_brand" "project_brand" {
  support_email     = "support@diet-tracker.jp"
  application_title = "Diet Issue Tracker - External Testing"
  project           = var.project_id
}

# IAP configuration for API Gateway
resource "google_iap_web_iam_member" "api_gateway_access" {
  project = var.project_id
  role    = "roles/iap.httpsResourceAccessor"
  
  # Grant access to external testers group
  member = "group:external-testers@diet-tracker.jp"
  
  condition {
    title       = "External Testing Period"
    description = "Access granted during external testing phase"
    expression  = "request.time < timestamp('2025-08-01T00:00:00Z')"
  }
}

# IAP configuration for Web Frontend
resource "google_iap_web_iam_member" "web_frontend_access" {
  project = var.project_id
  role    = "roles/iap.httpsResourceAccessor"
  
  # Grant access to external testers group
  member = "group:external-testers@diet-tracker.jp"
  
  condition {
    title       = "External Testing Period"
    description = "Access granted during external testing phase"
    expression  = "request.time < timestamp('2025-08-01T00:00:00Z')"
  }
}

# Backend service for API Gateway with IAP
resource "google_compute_backend_service" "api_gateway_backend" {
  name        = "${var.app_name}-api-gateway-backend-${var.environment}"
  protocol    = "HTTPS"
  timeout_sec = 30
  
  backend {
    group = google_compute_region_network_endpoint_group.api_gateway_neg.id
  }
  
  iap {
    oauth2_client_id     = google_iap_client.external_testing.client_id
    oauth2_client_secret = google_iap_client.external_testing.secret
  }
  
  depends_on = [google_project_service.iap_api]
}

# Backend service for Web Frontend with IAP
resource "google_compute_backend_service" "web_frontend_backend" {
  name        = "${var.app_name}-web-frontend-backend-${var.environment}"
  protocol    = "HTTPS"
  timeout_sec = 30
  
  backend {
    group = google_compute_region_network_endpoint_group.web_frontend_neg.id
  }
  
  iap {
    oauth2_client_id     = google_iap_client.external_testing.client_id
    oauth2_client_secret = google_iap_client.external_testing.secret
  }
  
  depends_on = [google_project_service.iap_api]
}

# Network Endpoint Groups for Cloud Run services
resource "google_compute_region_network_endpoint_group" "api_gateway_neg" {
  name                  = "${var.app_name}-api-gateway-neg-${var.environment}"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = google_cloud_run_service.api_gateway.name
  }
}

resource "google_compute_region_network_endpoint_group" "web_frontend_neg" {
  name                  = "${var.app_name}-web-frontend-neg-${var.environment}"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = google_cloud_run_service.web_frontend.name
  }
}

# Load balancer configuration with IAP
resource "google_compute_url_map" "https_lb" {
  name            = "${var.app_name}-https-lb-${var.environment}"
  default_service = google_compute_backend_service.web_frontend_backend.id
  
  host_rule {
    hosts        = [var.domain_name]
    path_matcher = "paths"
  }
  
  path_matcher {
    name            = "paths"
    default_service = google_compute_backend_service.web_frontend_backend.id
    
    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.api_gateway_backend.id
    }
  }
}

# HTTPS proxy
resource "google_compute_target_https_proxy" "https_proxy" {
  name             = "${var.app_name}-https-proxy-${var.environment}"
  url_map          = google_compute_url_map.https_lb.id
  ssl_certificates = [google_compute_managed_ssl_certificate.default.id]
}

# Managed SSL certificate
resource "google_compute_managed_ssl_certificate" "default" {
  name = "${var.app_name}-ssl-cert-${var.environment}"
  
  managed {
    domains = [var.domain_name]
  }
}

# Global forwarding rule
resource "google_compute_global_forwarding_rule" "https_rule" {
  name       = "${var.app_name}-https-rule-${var.environment}"
  target     = google_compute_target_https_proxy.https_proxy.id
  port_range = "443"
  ip_address = google_compute_global_address.default.address
}

# Reserved IP address
resource "google_compute_global_address" "default" {
  name = "${var.app_name}-ip-${var.environment}"
}

# Output the load balancer IP for DNS configuration
output "load_balancer_ip" {
  value = google_compute_global_address.default.address
  description = "IP address for DNS A record configuration"
}

# Output IAP client information
output "iap_client_id" {
  value = google_iap_client.external_testing.client_id
  description = "OAuth2 client ID for IAP configuration"
  sensitive = true
}

# Instructions for setting up external testers
output "iap_setup_instructions" {
  value = <<-EOT
    IAP Setup Instructions:
    
    1. Create Google Group: external-testers@diet-tracker.jp
    2. Add external testers to the group
    3. Configure DNS A record: ${var.domain_name} → ${google_compute_global_address.default.address}
    4. Wait for SSL certificate provisioning (up to 30 minutes)
    5. Access the application at: https://${var.domain_name}
    
    External testers will be prompted to sign in with their Google accounts.
    Only members of the external-testers group will have access.
  EOT
}