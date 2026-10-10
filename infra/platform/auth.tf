# Sign-in, by invitation only. Nobody can register themselves: an
# administrator creates each user, and Cognito emails them a temporary
# password that they must change the first time they sign in.

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_cognito_user_pool" "this" {
  name = "pillarscan"

  # People sign in with their email address.
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  # Each user may add an authenticator app as a second factor.
  mfa_configuration = "OPTIONAL"

  software_token_mfa_configuration {
    enabled = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  deletion_protection = "ACTIVE"
}

# Cognito hosts the sign-in pages at this address, so the site never sees
# a password. The prefix has to be unique across AWS, hence the suffix.
resource "aws_cognito_user_pool_domain" "this" {
  domain       = "pillarscan-${random_id.suffix.hex}"
  user_pool_id = aws_cognito_user_pool.this.id
}

# The site is a public client: it runs in the browser and cannot keep a
# secret. It uses the authorization code flow with PKCE, the standard for
# that case, and never the older flows that put tokens in the URL.
resource "aws_cognito_user_pool_client" "site" {
  name         = "pillarscan-site"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email"]
  supported_identity_providers         = ["COGNITO"]

  callback_urls = [for url in var.site_urls : "${url}/account"]
  logout_urls   = [for url in var.site_urls : "${url}/account"]

  # A stolen token stops working within the hour.
  access_token_validity  = 60
  id_token_validity      = 60
  refresh_token_validity = 1

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  prevent_user_existence_errors = "ENABLED"
}

# The role template has to be readable by anyone, because CloudFormation
# fetches it on behalf of whoever is connecting their account. The bucket
# holds that one file and nothing else.
#
# Pillarscan's own scanner reports this bucket as lacking a public access
# block. That finding is accurate, and it is deliberate here.
resource "aws_s3_bucket" "onboarding" {
  bucket = "pillarscan-onboarding-${random_id.suffix.hex}"
}

resource "aws_s3_bucket_public_access_block" "onboarding" {
  bucket = aws_s3_bucket.onboarding.id

  # ACLs stay blocked. Only a bucket policy can make something public, and
  # the one below covers a single object.
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

resource "aws_s3_object" "role_template" {
  bucket       = aws_s3_bucket.onboarding.id
  key          = "pillarscan-role.yaml"
  source       = "${path.module}/../../onboarding/pillarscan-role.yaml"
  etag         = filemd5("${path.module}/../../onboarding/pillarscan-role.yaml")
  content_type = "application/x-yaml"
}

data "aws_iam_policy_document" "onboarding_public_read" {
  statement {
    sid       = "AnyoneMayReadTheRoleTemplate"
    actions   = ["s3:GetObject"]
    resources = [aws_s3_object.role_template.arn]

    principals {
      type        = "*"
      identifiers = ["*"]
    }
  }
}

resource "aws_s3_bucket_policy" "onboarding" {
  bucket = aws_s3_bucket.onboarding.id
  policy = data.aws_iam_policy_document.onboarding_public_read.json

  # The policy is refused while the public access block still forbids it.
  depends_on = [aws_s3_bucket_public_access_block.onboarding]
}
