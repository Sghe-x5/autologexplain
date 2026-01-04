# Managed PostgreSQL in 3 zones (a,b,d) with cheapest preset
resource "yandex_mdb_postgresql_cluster" "db" {
  name        = "app-postgres"
  environment = "PRODUCTION"
  network_id  = yandex_vpc_network.prod.id
  labels      = var.labels

  config {
    version = var.db_version
    resources {
      resource_preset_id = var.db_resource_preset
      disk_type_id       = "network-ssd"
      disk_size          = var.db_disk_size
    }
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

  security_group_ids = [yandex_vpc_security_group.db.id]
}

resource "random_password" "db_user" {
  length  = 20
  special = false
}

resource "yandex_mdb_postgresql_user" "app" {
  cluster_id = yandex_mdb_postgresql_cluster.db.id
  name       = "app"
  password   = random_password.db_user.result
}

resource "yandex_mdb_postgresql_database" "app" {
  cluster_id = yandex_mdb_postgresql_cluster.db.id
  name       = "app"
  owner      = yandex_mdb_postgresql_user.app.name
}
