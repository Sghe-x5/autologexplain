# VPC network and subnets with NAT Gateway for egress
resource "yandex_vpc_network" "prod" {
  name = var.network_name
}

# Managed NAT Gateway to provide internet access to private subnets
resource "yandex_vpc_gateway" "nat" {
  name                 = "nat-gateway"
  shared_egress_gateway {}
}

resource "yandex_vpc_route_table" "private_rt" {
  name       = "private-rt"
  network_id = yandex_vpc_network.prod.id

  static_route {
    destination_prefix = "0.0.0.0/0"
    gateway_id         = yandex_vpc_gateway.nat.id
  }
}

# Private subnets for application VMs (no public IPs)
resource "yandex_vpc_subnet" "app_a" {
  name           = "app-a"
  zone           = "${var.region}-a"
  network_id     = yandex_vpc_network.prod.id
  v4_cidr_blocks = [var.v4_cidr_a]
  route_table_id = yandex_vpc_route_table.private_rt.id
}

resource "yandex_vpc_subnet" "app_b" {
  name           = "app-b"
  zone           = "${var.region}-b"
  network_id     = yandex_vpc_network.prod.id
  v4_cidr_blocks = [var.v4_cidr_b]
  route_table_id = yandex_vpc_route_table.private_rt.id
}

resource "yandex_vpc_subnet" "app_d" {
  name           = "app-d"
  zone           = "${var.region}-d"
  network_id     = yandex_vpc_network.prod.id
  v4_cidr_blocks = [var.v4_cidr_d]
  route_table_id = yandex_vpc_route_table.private_rt.id
}

# Public subnet for Bastion host
resource "yandex_vpc_subnet" "bastion" {
  name           = "bastion-public"
  zone           = "${var.region}-a"
  network_id     = yandex_vpc_network.prod.id
  v4_cidr_blocks = [var.bastion_cidr]
}
