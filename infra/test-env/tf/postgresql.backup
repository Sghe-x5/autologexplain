resource "random_password" "postgres_password" {
  length           = 16
  special          = true
  override_special = "_%@"
}

resource "yandex_compute_disk" "boot-disk-1" {
  name     = "boot-disk-1"
  type     = "network-hdd"
  zone     = local.zone
  size     = "10"
  image_id = data.yandex_compute_image.ubuntu_image.id
}

resource "yandex_compute_instance" "postgres-vm" {
  name     = "postgres-vm"
  zone     = local.zone
  hostname = "postgres-vm"

  platform_id = "standard-v3"

  resources {
    cores         = 2
    memory        = 2
    core_fraction = 50
  }

  boot_disk {
    disk_id = yandex_compute_disk.boot-disk-1.id
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.postgres_subnet-1.id
    nat       = true
  }

  metadata = {
    ssh-keys = "ubuntu:${file("~/.ssh/id_ed25519.pub")}"
  }

  provisioner "remote-exec" {
    inline = [
      "sudo apt-get update",
      "sudo apt-get install -y postgresql postgresql-contrib",
      "sudo systemctl start postgresql",
      "sudo systemctl enable postgresql",
      # Настройка PostgreSQL
      "sudo -u postgres psql -c \"ALTER USER postgres WITH PASSWORD '${random_password.postgres_password.result}';\"",
      "echo \"listen_addresses = '*'\" | sudo tee -a /etc/postgresql/*/main/postgresql.conf",
      "echo \"host all all 0.0.0.0/0 md5\" | sudo tee -a /etc/postgresql/*/main/pg_hba.conf",
      "sudo systemctl restart postgresql"
    ]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      private_key = file("~/.ssh/id_ed25519") # Укажите путь к вашему приватному ключу
      host        = yandex_compute_instance.postgres-vm.network_interface.0.nat_ip_address
    }
  }

  scheduling_policy {
    preemptible = true
  }
}

resource "yandex_vpc_network" "postgres_network-1" {
  name = "network1"
}

resource "yandex_vpc_subnet" "postgres_subnet-1" {
  name           = "subnet1"
  zone           = local.zone
  network_id     = yandex_vpc_network.postgres_network-1.id
  v4_cidr_blocks = ["192.168.10.0/24"]
}

output "internal_ip_address_vm_1" {
  value = yandex_compute_instance.postgres-vm.network_interface.0.ip_address
}

output "external_ip_address_vm_1" {
  value = yandex_compute_instance.postgres-vm.network_interface.0.nat_ip_address
}
