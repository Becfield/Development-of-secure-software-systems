import psycopg
import json
import getpass
import time
import os
import sys
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
 
            
def check_database(config):
        
    try:
        with psycopg.connect(
            host=config["host"],
            port=config["port"],
            dbname=config["database"],
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
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
    
    while True:
        check_database(config)
        log(f"Следующая проверка через {interval} секунд")
        time.sleep(interval)
 
         
if __name__ == "__main__":
    main()