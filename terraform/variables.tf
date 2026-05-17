variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Project name used as a prefix for all resources"
  type        = string
  default     = "sre-final"
}

variable "environment" {
  description = "Deployment environment (dev / staging / prod)"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "ec2_instance_type" {
  description = "EC2 instance type for the application server"
  type        = string
  default     = "t3.micro"
}

variable "key_pair_name" {
  description = "Name of the AWS key pair to attach to EC2 instances"
  type        = string
  # No default — must be supplied at deployment time
}

variable "asg_min_size" {
  description = "ASG minimum number of instances"
  type        = number
  default     = 1
}

variable "asg_max_size" {
  description = "ASG maximum number of instances"
  type        = number
  default     = 3
}

variable "asg_desired_capacity" {
  description = "ASG desired number of instances"
  type        = number
  default     = 1
}

variable "cpu_scale_up_threshold" {
  description = "CPU % at which to scale out"
  type        = number
  default     = 70
}

variable "cpu_scale_down_threshold" {
  description = "CPU % at which to scale in"
  type        = number
  default     = 30
}

variable "ecr_image_tag_mutability" {
  description = "ECR image tag mutability (MUTABLE / IMMUTABLE)"
  type        = string
  default     = "MUTABLE"
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to SSH into EC2 instances (restrict in production)"
  type        = string
  default     = "0.0.0.0/0"
}
