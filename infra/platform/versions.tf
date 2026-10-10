terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.6"
    }
  }

  # The bucket name is supplied at init time from backend.hcl, which is
  # git-ignored:  terraform init -backend-config=backend.hcl
  backend "s3" {
    key     = "platform/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
    # Locks state with a file in the bucket itself, so no DynamoDB lock
    # table is needed.
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project = "pillarscan"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id

  # Built from the caller's identity so no account ID is committed.
  audit_role_arn            = "arn:aws:iam::${local.account_id}:role/${var.audit_role_name}"
  external_id_parameter_arn = "arn:aws:ssm:${var.region}:${local.account_id}:parameter${var.external_id_parameter}"

  lambda_runtime      = "python3.13"
  lambda_architecture = "arm64" # Graviton: cheaper per millisecond than x86.
  log_retention_days  = 14
}
