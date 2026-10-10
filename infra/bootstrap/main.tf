# The S3 bucket that holds Terraform state for infra/platform.
#
# This is the one piece that cannot keep its own state in that bucket, so
# it is applied once with local state (git-ignored) and then left alone.

terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      project = "pillarscan"
    }
  }
}

# Bucket names are global. A random suffix avoids collisions without
# putting the account ID in the name.
resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "state" {
  bucket = "pillarscan-tfstate-${random_id.suffix.hex}"
}

# State can contain sensitive values, so the bucket is private, encrypted
# and versioned. Versioning also allows a bad state write to be rolled back.
resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Old state versions are only useful for a short while.
resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    id     = "expire-old-state-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

output "state_bucket" {
  description = "Put this in infra/platform/backend.hcl as the bucket."
  value       = aws_s3_bucket.state.bucket
}
