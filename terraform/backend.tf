# Local backend for development — switch to S3 backend for production
terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}
