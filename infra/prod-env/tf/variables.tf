variable "region" {
  description = "YC region (e.g., ru-central1)"
  type        = string
  default     = "ru-central1"
}

variable "network_name" {
  description = "VPC network name"
  type        = string
  default     = "prod-net"
}

variable "v4_cidr_a" {
  description = "CIDR for zone a private subnet"
  type        = string
  default     = "10.10.1.0/24"
}

variable "v4_cidr_b" {
  description = "CIDR for zone b private subnet"
  type        = string
  default     = "10.10.2.0/24"
}

variable "v4_cidr_d" {
  description = "CIDR for zone d private subnet"
  type        = string
  default     = "10.10.3.0/24"
}

variable "bastion_cidr" {
  description = "CIDR for bastion public subnet"
  type        = string
  default     = "10.10.10.0/24"
}

variable "enable_zone_d" {
  description = "Whether to create resources in zone d (3rd app VM)"
  type        = bool
  default     = false
}

variable "ssh_public_key" {
  description = "SSH public key content to inject into VMs (e.g., 'ssh-ed25519 AAAA... user@host')"
  type        = string
}

variable "app_port" {
  description = "Application HTTP port"
  type        = number
  default     = 80
}

variable "app_port_tls" {
  description = "Application HTTPS port"
  type        = number
  default     = 443
}

variable "labels" {
  description = "Common labels to apply"
  type        = map(string)
  default     = {
    label = "app-prod"
    role  = "app-prod"
  }
}

variable "docker_frontend_image" {
  description = "Docker image for frontend service"
  type        = string
  default     = "nginx:alpine"
}

variable "docker_backend_image" {
  description = "Docker image for backend service"
  type        = string
  default     = "nginx:alpine"
}

variable "docker_analytics_image" {
  description = "Docker image for analytics service"
  type        = string
  default     = "nginx:alpine"
}

variable "db_version" {
  description = "PostgreSQL major version"
  type        = number
  default     = 15
}

variable "db_resource_preset" {
  description = "MDB PostgreSQL preset (cheapest suitable)"
  type        = string
  default     = "s2.micro"
}

variable "db_disk_size" {
  description = "MDB PostgreSQL disk size (GiB)"
  type        = number
  default     = 16
}

variable "redis_version" {
  description = "Managed Redis version (e.g., 6.0 or 7.0)"
  type        = string
  default     = "8.1-valkey"
}

variable "valkey_resource_preset" {
  description = "Valkey (Redis) preset (burstable)"
  type        = string
  default     = "b3-c1-m4"
}

variable "valkey_disk_size" {
  description = "Valkey disk size (GiB)"
  type        = number
  default     = 10
}

variable "folder_id" {
  description = "Yandex Cloud Folder ID"
  type        = string
}
