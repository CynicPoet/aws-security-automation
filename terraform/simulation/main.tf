terraform {
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.5" }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = { Project = "SecurityAutomation", ManagedBy = "Terraform", Purpose = "Demo-Simulation" }
  }
}

resource "random_id" "suffix" {
  byte_length = 2
}

# ── DATA ──────────────────────────────────────────────────────────────────────
data "aws_vpc" "default" {
  default = true
}

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY A — AUTO-REMEDIATION (MEDIUM severity, Environment=Test)
# ─────────────────────────────────────────────────────────────────────────────

# A1: Public S3 bucket
resource "aws_s3_bucket" "test_public" {
  bucket        = "secauto-test-public-${random_id.suffix.hex}"
  force_destroy = true
  tags = {
    Name        = "secauto-test-public-${random_id.suffix.hex}"
    Environment = "Test"
    Purpose     = "SecurityAutomationDemo-A1"
  }
}

resource "aws_s3_bucket_ownership_controls" "test_public" {
  bucket = aws_s3_bucket.test_public.id
  rule { object_ownership = "BucketOwnerPreferred" }
}

resource "aws_s3_bucket_acl" "test_public" {
  bucket     = aws_s3_bucket.test_public.id
  acl        = "public-read"
  depends_on = [aws_s3_bucket_ownership_controls.test_public]
}

# A2: Security group — SSH open to world
resource "aws_security_group" "test_open_ssh" {
  name        = "secauto-test-open-ssh"
  description = "Demo: SSH open to 0.0.0.0/0 — Category A auto-remediation"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "INTENTIONAL_MISCONFIGURATION_FOR_DEMO"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "secauto-test-open-ssh"
    Environment = "Test"
    Purpose     = "SecurityAutomationDemo-A2"
  }
}

# A3: Security group — ALL traffic open to world
resource "aws_security_group" "test_open_all" {
  name        = "secauto-test-open-all"
  description = "Demo: All traffic open to 0.0.0.0/0 — Category A auto-remediation"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "INTENTIONAL_MISCONFIGURATION_FOR_DEMO"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "secauto-test-open-all"
    Environment = "Test"
    Purpose     = "SecurityAutomationDemo-A3"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY B — ADMIN APPROVAL REQUIRED (HIGH severity)
# ─────────────────────────────────────────────────────────────────────────────

# B1: IAM user with admin access key — tagged Role=CI-Pipeline so AI escalates
resource "aws_iam_user" "test_risky" {
  name = "secauto-test-risky-user"
  tags = {
    Environment = "Test"
    Role        = "CI-Pipeline"
    Purpose     = "SecurityAutomationDemo-B1"
  }
}

resource "aws_iam_access_key" "test_risky" {
  user = aws_iam_user.test_risky.name
}

resource "aws_iam_user_policy_attachment" "test_risky_admin" {
  user       = aws_iam_user.test_risky.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

# B2: Security group — RDP open, tagged Environment=Production so AI escalates
resource "aws_security_group" "test_open_rdp" {
  name        = "secauto-test-open-rdp"
  description = "Demo: RDP open to 0.0.0.0/0, Production tag — Category B approval"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "INTENTIONAL_MISCONFIGURATION_FOR_DEMO"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "secauto-test-open-rdp"
    Environment = "Production"
    Service     = "RemoteAccess"
    Purpose     = "SecurityAutomationDemo-B2"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# FALSE POSITIVE DEMO — bucket is intentionally public (static website)
# AI should detect PublicAccess=Intentional tag and suppress without acting
# ─────────────────────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "test_fp_website" {
  bucket        = "secauto-test-fp-website-${random_id.suffix.hex}"
  force_destroy = true
  tags = {
    Name         = "secauto-test-fp-website-${random_id.suffix.hex}"
    Environment  = "Test"
    PublicAccess = "Intentional"
    Purpose      = "StaticWebsite"
    DemoScenario = "SecurityAutomationDemo-FP"
  }
}

resource "aws_s3_bucket_ownership_controls" "test_fp_website" {
  bucket = aws_s3_bucket.test_fp_website.id
  rule { object_ownership = "BucketOwnerPreferred" }
}

resource "aws_s3_bucket_acl" "test_fp_website" {
  bucket     = aws_s3_bucket.test_fp_website.id
  acl        = "public-read"
  depends_on = [aws_s3_bucket_ownership_controls.test_fp_website]
}

resource "aws_s3_bucket_website_configuration" "test_fp_website" {
  bucket = aws_s3_bucket.test_fp_website.id
  index_document { suffix = "index.html" }
}
