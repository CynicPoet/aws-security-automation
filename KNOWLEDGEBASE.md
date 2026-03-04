# Security Automation — Knowledge Base

## Stage 0 — Repository & Local Setup — COMPLETED ✅
**Date:** 2026-03-05
**Resources:** Local only — no AWS resources created
**Terraform files:**
- `terraform/providers.tf` — AWS + random providers, default tags
- `terraform/variables.tf` — All root variables with validation
- `terraform/main.tf` — Root module wiring all child modules
- `terraform/outputs.tf` — Key output values
- `terraform/backend.tf` — Local backend (tfstate)
- `terraform/terraform.tfvars.example` — Template for secrets

**Infra state:** No AWS resources deployed yet
**Decisions:**
- Local backend for now; S3 backend can be added later
- All variables have validation blocks
- `admin_email` is a required variable (no default — must be set in tfvars)
- `main.tf` wires all modules together; errors visible until each module is built (expected)

**Issues:** VS Code shows "Unexpected attribute" errors in main.tf — these resolve automatically as each module's variables.tf is created. Not a real error.

**Next:** Stage 1 — IAM Roles & Budget Alert
