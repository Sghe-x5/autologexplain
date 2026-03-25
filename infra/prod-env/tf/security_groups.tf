# Security Groups

# App SG: allow only NLB traffic on 80/443 and SSH from bastion, deny everything else inbound
resource "yandex_vpc_security_group" "app" {
  name        = "sg-app"
  description = "App VMs SG"
  network_id  = yandex_vpc_network.prod.id
  labels      = var.labels

  # Inbound app traffic (NLB forwards client IP; VMs are private so traffic arrives only via NLB)
  ingress {
    description    = "HTTP 80"
    protocol       = "TCP"
    port           = var.app_port
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description    = "HTTPS 443"
    protocol       = "TCP"
    port           = var.app_port_tls
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  # Health checks from NLB
  ingress {
    description       = "NLB healthchecks on app port"
    protocol          = "TCP"
    port              = var.app_port
    predefined_target = "loadbalancer_healthchecks"
  }

  # SSH from bastion SG
  ingress {
    description       = "SSH from bastion"
    protocol          = "TCP"
    port              = 22
    security_group_id = yandex_vpc_security_group.bastion.id
  }

  ingress {
    description       = "Prometheus metrics"
    protocol          = "TCP"
    port              = 9100
    security_group_id = yandex_vpc_security_group.bastion.id
  }

  ingress {
    description       = "cAdvisor metrics"
    protocol          = "TCP"
    port              = 1337
    security_group_id = yandex_vpc_security_group.bastion.id
  }

  # Egress allow all (NAT GW will route internet)
  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# Bastion SG: allow SSH from the internet to bastion and SSH to app VMs
resource "yandex_vpc_security_group" "bastion" {
  name        = "sg-bastion"
  description = "Bastion SG"
  network_id  = yandex_vpc_network.prod.id

  # SSH from trusted networks (here 0.0.0.0/0, better restrict)
  ingress {
    description    = "SSH from internet"
    protocol       = "TCP"
    port           = 22
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  # Prometheus
  ingress {
    description = "Prometheus UI"
    protocol    = "TCP"
    port        = 9090
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  # Grafana
  ingress {
    description = "Grafana UI"
    protocol    = "TCP"
    port        = 3000
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  # Loki
  ingress {
    description = "Loki push (Promtail)"
    protocol    = "TCP"
    port        = 3100
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description    = "HTTPS 443"
    protocol       = "TCP"
    port           = 443
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  # Egress allow all
  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# DB SG: allow traffic from App SG on 5432/6432
resource "yandex_vpc_security_group" "db" {
  name        = "sg-db"
  description = "DB SG"
  network_id  = yandex_vpc_network.prod.id

  ingress {
    description       = "app -> db 5432"
    protocol          = "TCP"
    port              = 5432
    security_group_id = yandex_vpc_security_group.app.id
  }
  ingress {
    description       = "app -> db 6432 (Odyssey pooler)"
    protocol          = "TCP"
    port              = 6432
    security_group_id = yandex_vpc_security_group.app.id
  }

  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# Valkey SG: allow traffic from App SG on 6379
resource "yandex_vpc_security_group" "valkey" {
  name        = "sg-valkey"
  description = "Valkey SG"
  network_id  = yandex_vpc_network.prod.id

  ingress {
    description       = "app -> valkey"
    protocol          = "TCP"
    port              = 6379
    security_group_id = yandex_vpc_security_group.app.id
  }

  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}
