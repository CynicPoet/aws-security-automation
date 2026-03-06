data "aws_caller_identity" "current" {}

# ─────────────────────────────────────────────
# SECURITY HUB — account activation only
# Standards (CIS, FSBP) are intentionally NOT subscribed:
# they require AWS Config (all_supported=true) which bills
# $0.003 per recorded config item across the entire account
# and is not needed for simulation-based operation.
# ─────────────────────────────────────────────

resource "aws_securityhub_account" "this" {}
