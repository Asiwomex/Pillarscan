# Deliberately misconfigured resources for the scanner to find.
#
# Everything here is either free or costs a few cents a month, holds no
# data, and is attached to nothing. Remove it all with `terraform destroy`.
# State is kept locally and git-ignored because it contains the account ID.

terraform {
  required_version = ">= 1.9"

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
      project = "pillarscan-bait"
    }
  }
}

data "aws_vpc" "default" {
  default = true
}

# Bucket names are global, so a random suffix avoids collisions without
# putting the account ID in the name.
resource "random_id" "suffix" {
  byte_length = 4
}

# Fails s3_public_access_block and s3_versioning. The bucket stays empty and
# has no public policy or ACL, so nothing is actually exposed.
resource "aws_s3_bucket" "bait" {
  bucket = "pillarscan-bait-${random_id.suffix.hex}"
}

resource "aws_s3_bucket_public_access_block" "bait" {
  bucket = aws_s3_bucket.bait.id

  block_public_acls       = false
  ignore_public_acls      = false
  block_public_policy     = false
  restrict_public_buckets = false
}

# Fails ec2_security_group_open_admin_ports. A security group does nothing
# until it is attached to a network interface. Never attach this one.
resource "aws_security_group" "bait" {
  name        = "pillarscan-bait-open-admin"
  description = "Pillarscan bait. Do not attach to anything."
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "RDP from anywhere"
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Fails ebs_unattached_volume and ebs_gp2_volume. About $0.10 a month.
resource "aws_ebs_volume" "bait" {
  availability_zone = "us-east-1a"
  size              = 1
  type              = "gp2"
}

# An IAM user with no permissions, no password and no access keys. Adding a
# console password by hand (and no MFA) makes it fail iam_user_mfa.
resource "aws_iam_user" "bait" {
  name          = "pillarscan-bait-user"
  force_destroy = true
}
