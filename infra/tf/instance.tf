data "yandex_compute_image" "my_image" {
  family = "ubuntu-2204-lts"
}

resource "yandex_compute_disk" "boot-disk-1" {
  name     = "boot-disk-1"
  type     = "network-hdd"
  zone     = local.zone
  size     = "10"
  image_id = data.yandex_compute_image.my_image.id
}

resource "yandex_compute_instance" "minimal-vm" {
  name = "minimal-vm"
  zone = local.zone
  hostname = "minimal-vm"   

  platform_id = "standard-v2" # Use a standard platform for the VM

  resources {
    cores         = 2
    memory        = 1
    core_fraction = 5
  }

  boot_disk {
    disk_id = yandex_compute_disk.boot-disk-1.id
  }

  network_interface {
    subnet_id = yandex_vpc_subnet.subnet-1.id
    nat       = true
  }

  metadata = {
    ssh-keys = "ubuntu:${file("~/.ssh/id_ed25519.pub")}"
  }

  scheduling_policy {
    preemptible = true
  }
}

resource "yandex_vpc_network" "network-1" {
  name = "network1"
}

resource "yandex_vpc_subnet" "subnet-1" {
  name           = "subnet1"
  zone           = local.zone
  network_id     = yandex_vpc_network.network-1.id
  v4_cidr_blocks = ["192.168.10.0/24"]
}

output "internal_ip_address_vm_1" {
  value = yandex_compute_instance.minimal-vm.network_interface.0.ip_address
}

output "external_ip_address_vm_1" {
  value = yandex_compute_instance.minimal-vm.network_interface.0.nat_ip_address
}
