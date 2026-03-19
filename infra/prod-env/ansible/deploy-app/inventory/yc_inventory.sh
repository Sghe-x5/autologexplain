#!/usr/bin/env sh

# Получаем список всех инстансов
INSTANCES=$(yc compute instances list --folder-id b1g3u90stuffbcgnkgne --format json)

# Получаем публичный IP Bastion Host
BASTION_IP=$(echo "$INSTANCES" | jq -r '.[] | select(.name | test("bastion")) | .network_interfaces[0].primary_v4_address.one_to_one_nat.address')

# Генерируем инвентарь для Ansible
echo "$INSTANCES" | jq \
    --arg bastion_ip "$BASTION_IP" \
    '{
        _meta: {
            hostvars: (
                map(
                    if (.name | test("bastion")) then
                        {
                            (.name): {
                                ansible_host: .network_interfaces[0].primary_v4_address.one_to_one_nat.address,
                                ansible_user: "ubuntu"
                            }
                        }
                    else
                        {
                            (.name): {
                                ansible_host: .network_interfaces[0].primary_v4_address.address,
                                ansible_ssh_common_args: ("-o ProxyCommand=\"ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -W %h:%p ubuntu@" + $bastion_ip + "\" -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"),
                                ansible_user: "ubuntu"
                            }
                        }
                    end
                ) | add
            )
        },
        all: {
            children: (
                [
                    if (map(select(.name | test("bastion"))) | length > 0) then "bastion" else empty end,
                    (map(select(.name | test("bastion") | not)) | .[].name | split("-")[0])
                ] | unique
            )
        }
    } + 
    {
        bastion: [map(select(.name | test("bastion"))) | .[].name]
    } + 
    (
        map(select(.name | test("bastion") | not)) | 
        group_by(.name | split("-")[0]) | 
        map(
            {
                (.[0].name | split("-")[0]): [.[].name]
            }
        ) | add
    )'