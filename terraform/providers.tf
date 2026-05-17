terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state in S3 + DynamoDB locking.
  # Create the bucket and table ONCE before first `terraform init`:
  #   aws s3 mb s3://<bucket> --region <region>
  #   aws dynamodb create-table --table-name <table> \
  #       --attribute-definitions AttributeName=LockID,AttributeType=S \
  #       --key-schema AttributeName=LockID,KeyType=HASH \
  #       --billing-mode PAY_PER_REQUEST
  backend "s3" {
    bucket         = "sre-final-tfstate-649617407622"
    key            = "sre-final/terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "sre-final-tfstate-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
