variable "project_name" {
  description = "Short name used as a prefix for AWS resources."
  type        = string
  default     = "warehouse-intelligence"
}

variable "aws_region" {
  description = "AWS region for the deployment."
  type        = string
  default     = "eu-west-2"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "image_tag" {
  description = "Docker image tag already pushed to the ECR repository."
  type        = string
  default     = "latest"
}

variable "api_desired_count" {
  description = "Keep this at 0 until the first Docker image has been pushed to ECR."
  type        = number
  default     = 0
}

variable "db_instance_class" {
  description = "RDS instance class. This creates billable infrastructure if applied."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "schedule_expression" {
  description = "EventBridge Scheduler expression for the synthetic pipeline task."
  type        = string
  default     = "rate(1 day)"
}

variable "schedule_enabled" {
  description = "Leave false until an image exists in ECR and you actually want scheduled runs."
  type        = bool
  default     = false
}
