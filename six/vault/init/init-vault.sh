#!/bin/sh
# Инициализация Vault для лабораторной работы 6:
#   4. Включение метода авторизации AppRole
#   5. Создание секрета (логин и пароль) для доступа к БД
#   6. Создание политики для чтения этого секрета
#   7. Создание AppRole для сервиса pinger
#   8. Получение role-id для AppRole
set -e

echo "[vault-init] Ожидание готовности Vault..."
until vault status >/dev/null 2>&1; do
  sleep 1
done

echo "[vault-init] Включение метода авторизации AppRole"
if vault auth enable approle >/dev/null 2>&1; then
  echo "[vault-init] AppRole включён"
else
  echo "[vault-init] AppRole уже включён"
fi

echo "[vault-init] Создание секрета ${DB_CREDS_PATH:-db} (логин и пароль для доступа к БД)"
vault kv put secret/db login="${DB_USER}" password="${DB_PASSWORD}"

echo "[vault-init] Создание политики pinger-policy (только чтение секрета db)"
vault policy write pinger-policy - <<'EOF'
# Доступ только на чтение конкретного секрета с кредами БД
path "secret/data/db" {
  capabilities = ["read"]
}
EOF

echo "[vault-init] Создание AppRole 'pinger' для сервиса pinger"
vault write auth/approle/role/pinger \
    token_policies="pinger-policy" \
    token_ttl=1h \
    token_max_ttl=4h

echo "[vault-init] Получение role-id и генерация secret-id"
vault read -field=role_id auth/approle/role/pinger/role-id > /vault-creds/role_id
vault write -f -field=secret_id auth/approle/role/pinger/secret-id > /vault-creds/secret_id
chmod 644 /vault-creds/role_id /vault-creds/secret_id

echo "[vault-init] Готово. role-id: $(cat /vault-creds/role_id)"
echo "[vault-init] role-id и secret-id записаны в volume vault_creds"
