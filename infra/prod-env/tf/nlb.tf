# Network Load Balancer with health checks to app instances
resource "yandex_lb_network_load_balancer" "app_nlb" {
  name = "app-nlb"

  listener {
    name = "http"
    port = var.app_port
    target_port = var.app_port
    protocol = "tcp"
    external_address_spec {}
  }

  attached_target_group {
    target_group_id = yandex_lb_target_group.app_tg.id
    healthcheck {
      name = "tcp-check"
      tcp_options {
        port = var.app_port
      }
      interval  = 5
      timeout   = 2
      unhealthy_threshold = 2
      healthy_threshold   = 2
    }
  }
}

resource "yandex_lb_target_group" "app_tg" {
  name = "app-tg"

  dynamic "target" {
    for_each = [
      {
        subnet_id = yandex_vpc_subnet.app_a.id
        address   = yandex_compute_instance.app_a.network_interface[0].ip_address
      },
      {
        subnet_id = yandex_vpc_subnet.app_b.id
        address   = yandex_compute_instance.app_b.network_interface[0].ip_address
      }
    ]
    content {
      subnet_id = target.value.subnet_id
      address   = target.value.address
    }
  }

  dynamic "target" {
    for_each = var.enable_zone_d ? [1] : []
    content {
      subnet_id = yandex_vpc_subnet.app_d.id
      address   = yandex_compute_instance.app_d[0].network_interface[0].ip_address
    }
  }
}
