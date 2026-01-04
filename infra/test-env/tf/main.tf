resource "yandex_iam_service_account" "sa-test-env" {
  name        = "terraform-test-env"
  description = "Service account for Terraform (Test env)"
}

resource "yandex_resourcemanager_folder_iam_member" "terraform-provider-editor" {
  folder_id = var.folder_id
  role      = "admin"
  member    = "serviceAccount:${yandex_iam_service_account.sa-test-env.id}"
}

resource "yandex_iam_service_account_key" "sa_key" {
  service_account_id = yandex_iam_service_account.sa-test-env.id
  description        = "API key for Terraform (Test env)"
}

data "yandex_compute_image" "ubuntu_image" {
  family = "ubuntu-2204-lts"
}