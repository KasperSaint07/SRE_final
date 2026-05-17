# ── S3 bucket for Terraform state (bootstrap resource) ───────────────────────
# Create this bucket BEFORE running terraform init for the first time:
#   aws s3 mb s3://sre-final-tfstate-bucket --region eu-central-1
#   aws s3api put-bucket-versioning \
#       --bucket sre-final-tfstate-bucket \
#       --versioning-configuration Status=Enabled
#   aws s3api put-bucket-encryption \
#       --bucket sre-final-tfstate-bucket \
#       --server-side-encryption-configuration \
#       '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
#
# DynamoDB table for state locking:
#   aws dynamodb create-table \
#       --table-name sre-final-tfstate-lock \
#       --attribute-definitions AttributeName=LockID,AttributeType=S \
#       --key-schema AttributeName=LockID,KeyType=HASH \
#       --billing-mode PAY_PER_REQUEST \
#       --region eu-central-1

# All resources are defined in the focused files:
#   vpc.tf            – VPC, subnets, IGW, route tables
#   security-groups.tf – Security group rules
#   ecr.tf            – ECR repo + IAM role/profile for EC2
#   ec2.tf            – Standalone EC2 + EIP
#   asg.tf            – Launch Template + ASG + CloudWatch alarms
