# Additional variables for staging environment

variable "domain_name" {
  description = "Domain name for the staging environment"
  type        = string
  default     = ""
}

variable "cors_origins" {
  description = "Allowed CORS origins"
  type        = list(string)
  default     = []
}

variable "data_anonymization" {
  description = "Enable data anonymization for external testing"
  type        = bool
  default     = true
}

variable "enable_google_oauth" {
  description = "Enable Google OAuth authentication"
  type        = bool
  default     = false
}

variable "enable_jwt_auth" {
  description = "Enable JWT authentication"
  type        = bool
  default     = true
}

variable "enable_iap" {
  description = "Enable Identity-Aware Proxy (IAP)"
  type        = bool
  default     = false
}

variable "max_concurrent_requests" {
  description = "Maximum concurrent requests for load testing"
  type        = number
  default     = 100
}

variable "request_timeout" {
  description = "Request timeout for Cloud Run services"
  type        = string
  default     = "60s"
}

variable "enable_detailed_logging" {
  description = "Enable detailed logging for debugging"
  type        = bool
  default     = false
}

variable "log_level" {
  description = "Logging level (DEBUG, INFO, WARNING, ERROR)"
  type        = string
  default     = "INFO"
  
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR."
  }
}