# One table for everything. The key design is described in scanner/store.py.
resource "aws_dynamodb_table" "scans" {
  name = "pillarscan-scans"

  # Provisioned at 5 read and 5 write units, which sits inside DynamoDB's
  # always-free allowance of 25 each. A daily scan writes about 60 small
  # items; unused capacity from the minutes before covers that burst.
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5

  hash_key  = "PK"
  range_key = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # Items delete themselves 90 days after they are written.
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  # The scanner flags tables without this (dynamodb_pitr), so the platform
  # should not fail its own check. Billed per GB; this table is kilobytes.
  point_in_time_recovery {
    enabled = true
  }

  deletion_protection_enabled = true
}
