
resource "yandex_compute_disk" "test-boot-disk-1" {
  name     = "test-boot-disk-1"
  type     = "network-hdd"
  zone     = local.zone
  size     = "20"
  image_id = data.yandex_compute_image.ubuntu_image.id
}

resource "yandex_compute_instance" "test-vm" {
  name     = "test-vm"
  zone     = local.zone
  hostname = "test-vm"

  platform_id = "standard-v3"

  resources {
    cores         = 2
    memory        = 2
    core_fraction = 50
  }

  boot_disk {
    disk_id = yandex_compute_disk.test-boot-disk-1.id
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.test_subnet-1.id
    nat       = true
  }

  metadata = {
    ssh-keys = "ubuntu:${file("~/.ssh/id_ed25519.pub")}"
  }

  scheduling_policy {
    preemptible = true
  }
}

resource "yandex_vpc_network" "test_network-1" {
  name = "test_network-1"
}

resource "yandex_vpc_subnet" "test_subnet-1" {
  name           = "test_subnet-1"
  zone           = local.zone
  network_id     = yandex_vpc_network.test_network-1.id
  v4_cidr_blocks = ["192.168.10.0/24"]
}

output "internal_ip_address_test_vm" {
  value = yandex_compute_instance.test-vm.network_interface.0.ip_address
}

output "external_ip_address_test_vm" {
  value = yandex_compute_instance.test-vm.network_interface.0.nat_ip_address
}

