# The read-only role the daily public scan runs through, in the platform's
# own account, and the external ID that role asks for.
#
# Users' accounts get the same role from onboarding/pillarscan-role.yaml.
# This one used to be made the same way, by hand, together with the SSM
# parameter. Being outside Terraform, both outlived `terraform destroy`, and
# once the role was deleted the daily scan kept failing against it. Made
# here, they come and go with the rest of the platform.
#
# The trade-off: the external ID is now in Terraform state. The state
# bucket is private and encrypted, and anyone who can read it can already
# change this account, so it guards against nothing extra. The external ID
# is not a password; it stops the confused-deputy problem across accounts.

resource "random_password" "external_id" {
  length  = 48
  special = false
}

resource "aws_ssm_parameter" "external_id" {
  name        = var.external_id_parameter
  description = "External ID the Pillarscan scanner sends when it assumes the audit role."
  type        = "SecureString"
  value       = random_password.external_id.result
}

data "aws_iam_policy_document" "audit_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    # Only the scanner Lambda's role, not the whole account.
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.scanner.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values   = [random_password.external_id.result]
    }
  }
}

resource "aws_iam_role" "audit" {
  name                 = var.audit_role_name
  description          = "Read-only access for Pillarscan posture scans."
  max_session_duration = 3600
  assume_role_policy   = data.aws_iam_policy_document.audit_trust.json
}

# The same two AWS managed, read-only policies as the onboarding template.
resource "aws_iam_role_policy_attachment" "audit" {
  for_each = toset([
    "arn:aws:iam::aws:policy/SecurityAudit",
    "arn:aws:iam::aws:policy/job-function/ViewOnlyAccess",
  ])

  role       = aws_iam_role.audit.name
  policy_arn = each.value
}
