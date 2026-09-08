terraform {
  backend "http" {}

  required_version = "= 1.16.1"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "= 8.29.0"
    }
  }
}

provider "oci" {
  region = var.region
}
