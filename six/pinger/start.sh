#!/bin/sh
# Мост "volume -> переменные окружения".
# vault-init при старте складывает AppRole-креды в volume vault_creds.
# Этот скрипт экспортирует их в окружение, чтобы app.py, как и раньше,
# брал ВСЕ параметры строго из переменных окружения (require_env).

if [ ! -f /vault-creds/role_id ] || [ ! -f /vault-creds/secret_id ]; then
    echo "ОШИБКА: /vault-creds/role_id или /vault-creds/secret_id не найдены." >&2
    echo "Vault-init не отработал или volume не смонтирован." >&2
    exit 1
fi

export VAULT_ROLE_ID="$(cat /vault-creds/role_id)"
export VAULT_SECRET_ID="$(cat /vault-creds/secret_id)"

# exec заменяет shell процессом python - сигналы (Ctrl+C и т.п.)
# доходят до приложения напрямую
exec python app.py
