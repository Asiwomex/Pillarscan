variable "region" {
  description = "Region the platform runs in."
  type        = string
  default     = "us-east-1"
}

variable "audit_role_name" {
  description = "Name of the read-only role the scanner assumes. The platform's own is made in audit_role.tf; users' come from onboarding/pillarscan-role.yaml with a suffix."
  type        = string
  default     = "PillarscanAuditRole"
}

variable "external_id_parameter" {
  description = "Name of the SSM SecureString parameter holding the audit role's external ID (made in audit_role.tf)."
  type        = string
  default     = "/pillarscan/external-id"
}

variable "allowed_origins" {
  description = "Sites whose pages may call the API from a browser."
  type        = list(string)
  default = [
    "https://pillarscan.lytaworks.com",
    "https://pillarscan.vercel.app",
    "http://localhost:3000",
  ]
}

variable "site_urls" {
  description = "Addresses of the site. Cognito only sends people back to these after sign-in."
  type        = list(string)
  default = [
    "https://pillarscan.lytaworks.com",
    "https://pillarscan.vercel.app",
    "http://localhost:3000",
  ]
}

variable "scan_schedule" {
  description = "When the scheduled scan runs, as an EventBridge Scheduler expression (UTC)."
  type        = string
  default     = "cron(0 6 * * ? *)"
}

variable "alarm_email" {
  description = "Address to email when an alarm fires. Leave empty for alarms with no notification."
  type        = string
  default     = ""
}

variable "protect" {
  description = "Deletion protection on the table and user pool, and refuse to delete buckets that still hold files. scripts/destroy.ps1 turns it off just before tearing everything down."
  type        = bool
  default     = true
}
