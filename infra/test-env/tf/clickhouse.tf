resource "random_password" "clickhouse_password" {
  length           = 16
  special          = true
  override_special = "_%@"
}

resource "yandex_compute_disk" "clickhouse-boot-disk-1" {
  name     = "clickhouse-boot-disk-1"
  type     = "network-hdd"
  zone     = local.zone
  size     = "100"
  image_id = data.yandex_compute_image.ubuntu_image.id
}

resource "yandex_compute_instance" "clickhouse-vm" {
  name     = "clickhouse-vm"
  zone     = local.zone
  hostname = "clickhouse-vm"

  platform_id = "standard-v3"

  resources {
    cores         = 2
    memory        = 2
    core_fraction = 50
  }

  boot_disk {
    disk_id = yandex_compute_disk.clickhouse-boot-disk-1.id
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.clickhouse_subnet-1.id
    nat       = true
  }

  metadata = {
    ssh-keys = "ubuntu:${file("~/.ssh/id_ed25519.pub")}"
  }

  provisioner "remote-exec" {
    inline = [
      "sudo apt-get update",
      "sudo apt-get install -y apt-transport-https ca-certificates curl gnupg",
      "curl -fsSL 'https://packages.clickhouse.com/rpm/lts/repodata/repomd.xml.key' | sudo gpg --dearmor -o /usr/share/keyrings/clickhouse-keyring.gpg",
      "echo 'deb [signed-by=/usr/share/keyrings/clickhouse-keyring.gpg arch=amd64] https://packages.clickhouse.com/deb stable main' | sudo tee /etc/apt/sources.list.d/clickhouse.list",
      "sudo apt-get update",
      # Установка в неинтерактивном режиме
      "export DEBIAN_FRONTEND=noninteractive",
      "sudo -E apt-get install -y clickhouse-server clickhouse-client",
      # Создание конфигурации с паролем
      "sudo mkdir -p /etc/clickhouse-server/users.d/",
      "echo '<clickhouse><users><default><password>${random_password.clickhouse_password.result}</password></default></users></clickhouse>' | sudo tee /etc/clickhouse-server/users.d/default-password.xml",
      # Настройка прослушивания на всех интерфейсах (опционально)
      "echo '<clickhouse><listen_host>0.0.0.0</listen_host></clickhouse>' | sudo tee /etc/clickhouse-server/config.d/listen.xml",
      "sudo chown clickhouse:clickhouse /etc/clickhouse-server/users.d/default-password.xml",
      "sudo chown clickhouse:clickhouse /etc/clickhouse-server/config.d/listen.xml",
      "sudo systemctl start clickhouse-server",
      "sudo systemctl enable clickhouse-server"
    ]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      private_key = file("~/.ssh/id_ed25519")
      host        = yandex_compute_instance.clickhouse-vm.network_interface.0.nat_ip_address
    }
  }

  scheduling_policy {
    preemptible = true
  }
}

resource "yandex_vpc_network" "clickhouse_network-1" {
  name = "clickhouse_network-1"
}

resource "yandex_vpc_subnet" "clickhouse_subnet-1" {
  name           = "clickhouse_subnet-1"
  zone           = local.zone
  network_id     = yandex_vpc_network.clickhouse_network-1.id
  v4_cidr_blocks = ["192.168.10.0/24"]
}

output "internal_ip_address_clickhouse_vm" {
  value = yandex_compute_instance.clickhouse-vm.network_interface.0.ip_address
}

output "external_ip_address_clickhouse_vm" {
  value = yandex_compute_instance.clickhouse-vm.network_interface.0.nat_ip_address
}

output "clickhouse_password" {
  value     = random_password.clickhouse_password.result
  sensitive = true
}
