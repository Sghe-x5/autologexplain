output "service_account_key_json" {
  value = jsonencode({
    id                 = yandex_iam_service_account_key.sa_key.id
    service_account_id = yandex_iam_service_account_key.sa_key.service_account_id
    created_at         = yandex_iam_service_account_key.sa_key.created_at
    key_algorithm      = yandex_iam_service_account_key.sa_key.key_algorithm
    public_key         = yandex_iam_service_account_key.sa_key.public_key
    private_key        = yandex_iam_service_account_key.sa_key.private_key
  })
  sensitive = true
}