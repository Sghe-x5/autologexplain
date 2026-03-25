# Managed Redis cluster in 3 zones from burstable cheapest preset

resource "random_password" "redis_password" {
  length  = 20
  special = false
}

resource "yandex_mdb_redis_cluster" "redis" {
  name        = "app-redis"
  environment = "PRODUCTION"
  network_id  = yandex_vpc_network.prod.id
  labels      = var.labels

  config {
    version  = var.redis_version
    password = random_password.redis_password.result
  }

  resources {
    resource_preset_id = var.valkey_resource_preset
    disk_size          = var.valkey_disk_size
    disk_type_id       = "network-ssd"
  }

  host {
    zone      = "${var.region}-a"
    subnet_id = yandex_vpc_subnet.app_a.id
  }
  host {
    zone      = "${var.region}-b"
    subnet_id = yandex_vpc_subnet.app_b.id
  }
  host {
    zone      = "${var.region}-d"
    subnet_id = yandex_vpc_subnet.app_d.id
  }

  security_group_ids = [yandex_vpc_security_group.valkey.id]
}
