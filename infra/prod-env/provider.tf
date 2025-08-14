terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
    random = {
      source = "hashicorp/random"
    }
  }
  required_version = ">= 0.13"
}

# Default region/zone (can be overridden via variable "region").
locals {
  zone = "${var.region}-a"
}

provider "yandex" {
  folder_id = var.folder_id
  zone      = local.zone
}
