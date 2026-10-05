variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name, used as a resource name prefix"
  type        = string
  default     = "pulse-platform"
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "kubernetes_version" {
  description = "Kubernetes version for the EKS control plane"
  type        = string
  default     = "1.31"
}

variable "db_password" {
  description = "RDS master password. No default on purpose -- pass via TF_VAR_db_password or a gitignored *.tfvars file, never commit a real one."
  type        = string
  sensitive   = true
}
