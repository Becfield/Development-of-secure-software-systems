import psycopg
import json
import getpass

def load_config(filename="config.json"):
    with open(filename, "r", encoding="utf-8") as file:
        config = json.load(file)
    
    allowed_keys={"host", "port", "database"} # Используем для того, чтобы пользователь не смог вносить изменения в дополнительные параметры подключения

    # Логика пустого множества --> False
    if set(config.keys() - allowed_keys): 
        raise ValueError("Конфигурационный файл содержит недопустимые параметры")

    return config

def main():
    config = load_config()
    
    username = input("Введите логин пользователя PostgreSQL: ")
    password = getpass.getpass("Введите пароль пользователя PostgreSQL: ")

    connection = psycopg.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["database"],
        user=username,
        password=password
    )
    
    with connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION();")
            version = cursor.fetchone()[0]
            print("\nВерсия PostgreSQL:")
            print(version)
            
if __name__ == "__main__":
    main()