import psycopg
import json
import time
import os
import sys
import hvac
from datetime import datetime

def load_config(filename="config.json"):
    with open(filename, "r", encoding="utf-8") as file:
        config = json.load(file)

    return config

def log(message, error=False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"[{timestamp}] {message}"

    if error:
        print(message, file=sys.stderr, flush=True) #Сразу выталкиваем сообщение из буфера в поток
    else:
        print(message, file=sys.stdout, flush=True)

    log_file = os.getenv("LOG_FILE")

    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as file:
                file.write(message + "\n")
        except OSError as exc:
            print(
                f"[{timestamp}] Ошибка записи в лог-файл: {exc}",
                file=sys.stderr,
                flush=True
            )


# ---------- Клиент Vault ----------

VAULT_ADDR = os.getenv("VAULT_ADDR")
VAULT_MOUNT_POINT = os.getenv("VAULT_MOUNT_POINT")
VAULT_SECRET_PATH = os.getenv("VAULT_SECRET_PATH")
VAULT_ROLE_ID = os.getenv("VAULT_ROLE_ID")
VAULT_SECRET_ID = os.getenv("VAULT_SECRET_ID")

def create_vault_client():
    client = hvac.Client(url=VAULT_ADDR)

    client.auth.approle.login(
        role_id=VAULT_ROLE_ID,
        secret_id=VAULT_SECRET_ID,
    )

    if not client.is_authenticated():
        raise RuntimeError("Не удалось авторизоваться в Vault по AppRole")

    return client

def read_db_credentials(client):
    response = client.secrets.kv.v2.read_secret_version(
        mount_point=VAULT_MOUNT_POINT,
        path=VAULT_SECRET_PATH,
    )

    data = response["data"]["data"]
    return data["login"], data["password"]


def check_database(config, vault_client):

    try:
        login, password = read_db_credentials(vault_client)
        log(f"Секрет получен из Vault")

        with psycopg.connect(
            host=config["host"],
            port=config["port"],
            dbname=config["database"],
            user=login,
            password=password,
            connect_timeout = 10
        ) as connection:

            log("Успешное подключение к PostgreSQL")

            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION();")
                version = cursor.fetchone()[0]

                if isinstance(version, str) and version.startswith("PostgreSQL 18"):
                    log(f"Версия PostgreSQL: {version}")
                else:
                    log(f"Нетипичный ответ на SELECT VERSION(): {version}")

    except Exception as exc:
        log(f"Не удалось подключиться к PostgreSQL: {exc}", error=True)


def main():
    config = load_config()

    interval = int(os.getenv("PING_INTERVAL"))

    log(f"Сервис pinger запущен. Интервал проверки: {interval} секунд")
    log(f"Vault: {VAULT_ADDR}, путь секрета: {VAULT_MOUNT_POINT}/{VAULT_SECRET_PATH}")

    vault_client = create_vault_client()
    log("Авторизация в Vault по AppRole выполнена")

    while True:
        if not vault_client.is_authenticated():
            log("Токен Vault истёк, повторная авторизация по AppRole", error=True)
            vault_client = create_vault_client()

        check_database(config, vault_client)
        log(f"Следующая проверка через {interval} секунд")
        time.sleep(interval)


if __name__ == "__main__":
    main()
