# Terraform variables for external user testing staging environment
# This configuration provides enhanced resources for comprehensive testing

project_id = "diet-issue-tracker"  # Replace with actual project ID
region = "asia-northeast1"
zone = "asia-northeast1-a"
environment = "staging-external-test"
app_name = "seiji-watch"

# Enhanced database configuration for testing
db_tier = "db-custom-2-7680"  # 2 vCPU, 7.5GB RAM for performance testing
db_disk_size = 100  # 100GB for full dataset
db_backup_enabled = true

# Enhanced Cloud Run configuration for load testing
cloud_run_cpu = "2"  # 2 vCPU for performance
cloud_run_memory = "2Gi"  # 2GB memory for load handling
cloud_run_min_instances = 1  # Always available for testing
cloud_run_max_instances = 50  # Higher limit for load testing (1000 concurrent users)

# Storage configuration
storage_location = "ASIA-NORTHEAST1"
storage_class = "STANDARD"

# Additional testing-specific configurations
# These will be used in Terraform templates

# Domain configuration (will need DNS setup)
domain_name = "staging-test.diet-issue-tracker.jp"

# Security configuration for external access
cors_origins = [
  "https://staging-test.diet-issue-tracker.jp",
  "http://localhost:3000",  # For local development testing
  "http://localhost:8080"   # For debug testing
]

# Performance testing configuration
max_concurrent_requests = 1000
request_timeout = "300s"
memory_limit = "2Gi"

# Monitoring and logging
enable_detailed_logging = true
log_level = "INFO"
metrics_collection = true

# Authentication for external testers
enable_google_oauth = true
enable_jwt_auth = true

# Test data configuration
include_full_diet_217_data = true
enable_sample_data = true
data_anonymization = false  # Real data needed for accuracy testing

# Legal compliance testing
enable_gdpr_mode = true
enable_audit_logging = true
data_retention_days = 90

# Accessibility testing
enable_accessibility_features = true
enable_screen_reader_support = true
enable_keyboard_navigation = true

# Performance monitoring
enable_lighthouse_ci = true
enable_web_vitals_monitoring = true
performance_budget_mobile = "200ms"
performance_budget_desktop = "100ms"