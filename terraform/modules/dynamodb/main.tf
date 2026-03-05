# ── FINDINGS TABLE ─────────────────────────────────────────────────────────────
# Stores every security finding processed by the system

resource "aws_dynamodb_table" "findings" {
  name         = "security-automation-findings"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "finding_id"

  attribute {
    name = "finding_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "status-created-index"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl_epoch"
    enabled        = true
  }

  tags = { Name = "security-automation-findings" }
}

# ── SETTINGS TABLE ─────────────────────────────────────────────────────────────
# Key-value store for dashboard configuration (e.g. email toggle)

resource "aws_dynamodb_table" "settings" {
  name         = "security-automation-settings"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "setting_key"

  attribute {
    name = "setting_key"
    type = "S"
  }

  tags = { Name = "security-automation-settings" }
}

# ── SEED DEFAULT SETTINGS ──────────────────────────────────────────────────────

resource "aws_dynamodb_table_item" "email_notifications" {
  table_name = aws_dynamodb_table.settings.name
  hash_key   = aws_dynamodb_table.settings.hash_key

  item = jsonencode({
    setting_key = { S = "email_notifications" }
    value       = { S = "false" }
    updated_at  = { S = "initial" }
  })

  lifecycle {
    ignore_changes = [item]
  }
}
