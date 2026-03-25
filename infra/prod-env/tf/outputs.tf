output "nlb_public_ip" {
  description = "NLB public IPv4"
  value       = flatten(yandex_lb_network_load_balancer.app_nlb.listener[*].external_address_spec[*].address)[0]
}

output "bastion_public_ip" {
  description = "Bastion public IP"
  value       = yandex_compute_instance.bastion.network_interface[0].nat_ip_address
}

output "app_private_ips" {
  description = "App VMs private IPs"
  value = compact([
    yandex_compute_instance.app_a.network_interface[0].ip_address,
    yandex_compute_instance.app_b.network_interface[0].ip_address,
    try(yandex_compute_instance.app_d[0].network_interface[0].ip_address, null)
  ])
}

# output "db_endpoints" {
#  description = "PostgreSQL FQDNs"
#  value       = yandex_mdb_postgresql_cluster.db.host[*].fqdn
#}

output "redis_endpoints" {
  description = "Redis FQDNs"
  value       = yandex_mdb_redis_cluster.redis.host[*].fqdn
}

#output "db_user_password" {
#  description = "DB user password (store in Secret Manager/Lockbox!)"
#  value       = random_password.db_user.result
#  sensitive   = true
#}

output "redis_password" {
  description = "Redis password (store in Secret Manager/Lockbox!)"
  value       = random_password.redis_password.result
  sensitive   = true
}
