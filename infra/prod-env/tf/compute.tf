# Ubuntu 24.04 image
data "yandex_compute_image" "ubuntu" {
  family = "ubuntu-2404-lts"
}

# Bastion VM with public IP
resource "yandex_compute_instance" "bastion" {
  name        = "bastion"
  platform_id = "standard-v3"
  zone        = "${var.region}-a"
  labels      = { role = "bastion" }

  resources {
    cores  = 2
    memory = 2
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.id
      size     = 15
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.bastion.id
    nat                = true
    security_group_ids = [yandex_vpc_security_group.bastion.id]
  }

  metadata = {
    ssh-keys = "ubuntu:${var.ssh_public_key}"
  }
}

# Cloud-Init script to run docker compose with three services
locals {
  app_user_data = <<-EOT
  #cloud-config
  package_update: true
  packages:
    - docker.io
    - docker-compose-plugin
  runcmd:
    - [ sh, -c, "usermod -aG docker ubuntu" ]
    - [ sh, -c, "mkdir -p /opt/app" ]
    - [ sh, -c, "cat >/opt/app/compose.yaml <<'YAML'\nversion: '3.9'\nservices:\n  frontend:\n    image: ${var.docker_frontend_image}\n    ports:\n      - '${var.app_port}:80'\n    restart: unless-stopped\n  backend:\n    image: ${var.docker_backend_image}\n    restart: unless-stopped\n  analytics:\n    image: ${var.docker_analytics_image}\n    restart: unless-stopped\nYAML" ]
    - [ sh, -c, "docker compose -f /opt/app/compose.yaml up -d" ]
  EOT
}

# Application instances in zones a and b (and optional d)
resource "yandex_compute_instance" "app_a" {
  name        = "app-a"
  platform_id = "standard-v3"
  zone        = "${var.region}-a"
  labels      = var.labels

  resources {
    cores  = 2
    memory = 4
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.id
      size     = 20
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.app_a.id
    nat                = false
    security_group_ids = [yandex_vpc_security_group.app.id]
  }

  metadata = {
    ssh-keys  = "ubuntu:${var.ssh_public_key}"
    user-data = local.app_user_data
  }
}

resource "yandex_compute_instance" "app_b" {
  name        = "app-b"
  platform_id = "standard-v3"
  zone        = "${var.region}-b"
  labels      = var.labels

  resources {
    cores  = 2
    memory = 4
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.id
      size     = 20
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.app_b.id
    nat                = false
    security_group_ids = [yandex_vpc_security_group.app.id]
  }

  metadata = {
    ssh-keys  = "ubuntu:${var.ssh_public_key}"
    user-data = local.app_user_data
  }
}

resource "yandex_compute_instance" "app_d" {
  count       = var.enable_zone_d ? 1 : 0
  name        = "app-d"
  platform_id = "standard-v3"
  zone        = "${var.region}-d"
  labels      = var.labels

  resources {
    cores  = 2
    memory = 4
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.id
      size     = 20
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.app_d.id
    nat                = false
    security_group_ids = [yandex_vpc_security_group.app.id]
  }

  metadata = {
    ssh-keys  = "ubuntu:${var.ssh_public_key}"
    user-data = local.app_user_data
  }
}
