# Ansible: продовой деплой приложения на узлы app-*

Требования:
- ansible >= 2.15, коллекция community.docker
- yc CLI + jq (для динамического инвентаря)
- доступ к bastion по SSH ключу, настроенному в Terraform

Подготовка:
- экспортируйте YC_PROFILE/YCAUTH, чтобы `yc` видел ваш каталог
- при необходимости: ansible-galaxy collection install community.docker

Запуск деплоя:
- cd infra/prod-env/ansible
- ansible-playbook -i inventory/inventory.sh deploy-app.yml

Переменные:
- задаются в deploy-app.yml (образы, Valkey/ClickHouse, ключи)
- возьмите FQDN Valkey из terraform outputs (redis_endpoints) и пароль (redis_password)

Архитектура:
- 2+ приватных VM app-*, доступ через bastion (ProxyCommand)
- NLB балансирует TCP на порт app_port
- Контейнеры: frontend, backend, analytics
- Backend использует Valkey (MDB) и ClickHouse
