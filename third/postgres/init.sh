#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Создаём пользователя
    CREATE ROLE ${DB_USER}
        LOGIN
        PASSWORD '${DB_PASSWORD}';
    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${DB_USER};
    GRANT USAGE ON SCHEMA public TO ${DB_USER};
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -f /docker-entrypoint-initdb.d/init.sql

# Выдаём права на таблицы ПОСЛЕ их создания
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ${DB_USER};
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ${DB_USER};
EOSQL

# Загружаем тестовые данные
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -f /docker-entrypoint-initdb.d/seed.sql

echo "==> Инициализация БД завершена."
