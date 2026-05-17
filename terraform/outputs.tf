output "vpc_id" {
  description = "ID of the created VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "security_group_id" {
  description = "ID of the application security group"
  value       = aws_security_group.app.id
}

output "ec2_public_ip" {
  description = "Public IP of the standalone EC2 instance (single-instance mode)"
  value       = aws_instance.app.public_ip
}

output "ec2_public_dns" {
  description = "Public DNS of the standalone EC2 instance"
  value       = aws_instance.app.public_dns
}

output "ecr_repository_url" {
  description = "Full URL of the ECR repository (use as Docker image prefix)"
  value       = aws_ecr_repository.app.repository_url
}

output "ecr_repository_name" {
  description = "Name of the ECR repository"
  value       = aws_ecr_repository.app.name
}

output "asg_name" {
  description = "Name of the Auto Scaling Group"
  value       = aws_autoscaling_group.app.name
}

output "iam_instance_profile_name" {
  description = "IAM instance profile attached to EC2 instances"
  value       = aws_iam_instance_profile.ec2_profile.name
}

output "grafana_url" {
  description = "Grafana URL (single EC2 mode)"
  value       = "http://${aws_instance.app.public_ip}:3000"
}

output "prometheus_url" {
  description = "Prometheus URL (single EC2 mode)"
  value       = "http://${aws_instance.app.public_ip}:9090"
}

output "app_url" {
  description = "FastAPI application URL"
  value       = "http://${aws_instance.app.public_ip}:8000"
}
