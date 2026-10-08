import os
import sys
import json
import getpass
from datetime import datetime

import psycopg
from psycopg.rows import dict_row

#Белый список таблиц и колонок
ALLOWED_TABLES: dict[str, list[str]] = {
    "authors": ["id", "full_name", "birth_year", "country"],
    "books": ["id", "title", "author_id", "genre", "price", "stock", "published"],
    "customers": ["id", "full_name", "email", "phone", "city"],
    "orders": ["id", "customer_id", "order_date", "status"],
    "order_items": ["id", "order_id", "book_id", "quantity", "unit_price"],
}

NON_UPDATEABLE_COL = {"id"}

#Блок подклучения
def connect(config: dict, user: str, password: str) -> psycopg.Connection:
    """Устанавливает соединение с PostgreSQL."""
    conn = psycopg.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["database"],
        user=user,
        password=password,
        connect_timeout=10,
        row_factory=dict_row,
    )
    return conn

# Блок логгирования
def _fmt(message: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{ts}] {message}"


def log(message: str, error: bool = False) -> None:
    line = _fmt(message)
    stream = sys.stderr if error else sys.stdout
    print(line, file=stream, flush=True)
    
    log_file = os.getenv("LOG_FILE")
    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError as exc:
            print(_fmt(f"Ошибка записи в лог-файл: {exc}"), file=sys.stderr, flush=True)     
            

#Блок вспомогательных функций
#Чтение строки от пользователя            
def _input(prompt: str) -> str:
    try:
        value = input(prompt)
        return value.strip()
    except EOFError:
        print("\nСеанс завершён.")
        sys.exit(0)
    

def choose_table() -> str:
    names = list(ALLOWED_TABLES.keys())
    print("\nДоступные таблицы:")
    for i, name in enumerate(names, 1):
        print(f"  {i}. {name}")
    while True:
        raw = _input("Введите номер или название таблицы: ")
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(names):
                return names[idx]
        elif raw in ALLOWED_TABLES:
            return raw
        print("Неверный выбор, попробуйте снова.")
        
        
def choose_column(table: str, exclude: set[str] | None = None) -> str:
    cols = [c for c in ALLOWED_TABLES[table] if c not in (exclude or set())]
    print(f"\nКолонки таблицы «{table}»:")
    for i, col in enumerate(cols, 1):
        print(f"  {i}. {col}")
    while True:
        raw = _input("Введите номер или название колонки: ")
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(cols):
                return cols[idx]
        elif raw in cols:
            return raw
        print("Неверный выбор, попробуйте снова.")    
        

def print_rows(rows: list[dict]) -> None:
    if not rows:
        print("  (нет данных)")
        return
    keys = list(rows[0].keys())
    # Вычисляем ширину каждой колонки
    widths = {k: max(len(str(k)), max(len(str(r[k])) for r in rows)) for k in keys}
    sep = "+-" + "-+-".join("-" * widths[k] for k in keys) + "-+"
    header = "| " + " | ".join(str(k).ljust(widths[k]) for k in keys) + " |"
    print(sep)
    print(header)
    print(sep)
    for row in rows:
        line = "| " + " | ".join(str(row[k]).ljust(widths[k]) for k in keys) + " |"
        print(line)
    print(sep)
    print(f"  Всего строк: {len(rows)}")
    
    
#Блок фильтрации 6.1.1
def select_all(conn: psycopg.Connection) -> None:
    table = choose_table()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {table} ORDER BY id")
            rows = cur.fetchall()
        log(f"Получено {len(rows)} строк")
        print_rows(rows)
    except Exception as exc:
        conn.rollback()
        log(f"Ошибка при чтении таблицы «{table}»: {exc}", error=True)
        print("Не удалось выполнить запрос. Подробности — в логах.")
 
 
#6.1.2
def select_filter_one(conn: psycopg.Connection) -> None:
    table = choose_table()
    col = choose_column(table)
    value = _input(f"Введите значение для «{col}»: ")     
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {table} WHERE {col} = %s ORDER BY id",
                (value,),
            )
            rows = cur.fetchall()
        log(f"Получено {len(rows)} строк")  
        print_rows(rows)
    except Exception as exc:
        conn.rollback()
        log(f"Ошибка при фильтрации: {exc}", error=True)
        print("Не удалось выполнить запрос. Подробности — в логах.")
        

#6.1.3
def select_filter_multi(conn: psycopg.Connection) -> None:
    table = choose_table()
    filters: list[tuple[str,str]] = []
    
    while True:
        col = choose_column(table)
        value = _input(f"Введите значение для «{col}»: ")
        filters.append((col, value))
        more = _input("Добавить ещё один фильтр? (y/n): ").lower()
        if more != "y":
            break
        
    where_parts = " AND ".join(f"{col} = %s" for col, _ in filters)
    params = tuple(v for _, v in filters)
    sql = f"SELECT * FROM {table} WHERE {where_parts} ORDER BY id"
    
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        log(f"Получено {len(rows)} строк")
        print_rows(rows)
    except Exception as exc:
        conn.rollback()
        log(f"Ошибка при фильтрации: {exc}", error=True)
        print("Не удалось выполнить запрос. Подробности — в логах.")
               
               

#Блок обновления
#6.2.1
def update_one_by_id(conn: psycopg.Connection) -> None:
    table = choose_table()
    id_val = _input("Введите id записи для обновления: ")

    updates: list[tuple[str, str]] = []
    while True:
        col = choose_column(table, exclude=NON_UPDATEABLE_COL)
        value = _input(f"Новое значение для «{col}»: ")
        updates.append((col, value))
        more = _input("Обновить ещё одно поле? (y/n): ").lower()
        if more != "y":
            break

    set_clause = ", ".join(f"{col} = %s" for col, _ in updates)
    params = tuple(v for _, v in updates) + (id_val,)
    sql = f"UPDATE {table} SET {set_clause} WHERE id = %s"

    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            affected = cur.rowcount
        conn.commit()
        print(f"  Обновлено строк: {affected}")
    except Exception as exc:
        conn.rollback()
        log(f"Ошибка при обновлении: {exc}", error=True)
        print("Не удалось выполнить обновление. Подробности — в логах.")
      
#6.2.2        
def update_many_by_values(conn: psycopg.Connection) -> None:
    table = choose_table()

    upd_col = choose_column(table, exclude=NON_UPDATEABLE_COL)
    upd_val = _input(f"Новое значение для «{upd_col}»: ")

    filter_col = choose_column(table)
    raw_vals = _input("Введите значения через запятую (для фильтра IN): ")
    filter_vals = [v.strip() for v in raw_vals.split(",") if v.strip()]

    if not filter_vals:
        print("Список значений пуст. Операция отменена.")
        return

    placeholders = ", ".join(["%s"] * len(filter_vals))
    params = (upd_val, *filter_vals)
    sql = f"UPDATE {table} SET {upd_col} = %s WHERE {filter_col} IN ({placeholders})"

    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            affected = cur.rowcount
        conn.commit()
        print(f"  Обновлено строк: {affected}")
    except Exception as exc:
        conn.rollback()
        log(f"Ошибка при массовом обновлении: {exc}", error=True)
        print("Не удалось выполнить обновление. Подробности — в логах.")
        

#Блок добавления
def _ask_row_values(table: str, include_id: bool = False) -> tuple[list[str], list[str]]:
    """Интерактивно спрашивает значения для строки; возвращает (cols, vals)."""
    cols = ALLOWED_TABLES[table] if include_id else [c for c in ALLOWED_TABLES[table] if c not in NON_UPDATEABLE_COL]
    vals = []
    for col in cols:
        val = _input(f"  {col}: ")
        vals.append(val)
    return cols, vals

#6.3.1
def insert_one(conn: psycopg.Connection) -> None:
    """INSERT INTO table (...) VALUES (...)"""
    table = choose_table()
    print(f"\nВведите значения для новой строки в «{table}»")
    cols, vals = _ask_row_values(table)      
    col_list = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(vals))
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) RETURNING id"

    try:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(vals))
            new_id = cur.fetchone()["id"]
        conn.commit()
        print(f"  Вставлена строка с id={new_id}")
    except Exception as exc:
        conn.rollback()
        log(f"Ошибка при вставке: {exc}", error=True)
        print("Не удалось выполнить вставку. Подробности — в логах.")
        

#6.3.2
def insert_related(conn: psycopg.Connection) -> None:
    """INSERT в две связанные таблицы: сначала родительская,потом дочерняя"""
    print("\n=== Вставка заказа с позициями (orders → order_items) ===")
    print("\nДанные заказа (orders):")
    cols_o, vals_o = _ask_row_values("orders")

    sql_order = (
        "INSERT INTO orders ({}) VALUES ({}) RETURNING id".format(
            ", ".join(cols_o),
            ", ".join(["%s"] * len(vals_o)),
        )
    )

    try:
        with conn.cursor() as cur:
            cur.execute(sql_order, tuple(vals_o))
            order_id = cur.fetchone()["id"]
        log(f"INSERT INTO orders — order_id={order_id}")

        # Вставляем одну или несколько позиций
        while True:
            print(f"\nДанные позиции заказа (order_items) для order_id={order_id}:")
            item_cols = [c for c in ALLOWED_TABLES["order_items"] if c not in ("id", "order_id")]
            item_vals = []
            for col in item_cols:
                val = _input(f"  {col}: ")
                item_vals.append(val)

            all_cols = ["order_id"] + item_cols
            all_vals = [str(order_id)] + item_vals
            col_list = ", ".join(all_cols)
            placeholders = ", ".join(["%s"] * len(all_vals))
            sql_item = f"INSERT INTO order_items ({col_list}) VALUES ({placeholders}) RETURNING id"

            with conn.cursor() as cur:
                cur.execute(sql_item, tuple(all_vals))
                item_id = cur.fetchone()["id"]
            print(f"  Позиция добавлена (id={item_id})")

            more = _input("Добавить ещё одну позицию? (y/n): ").lower()
            if more != "y":
                break

        conn.commit()
        print(f"  Заказ order_id={order_id} успешно сохранён.")
    except Exception as exc:
        conn.rollback()
        log(f"Ошибка при вставке заказа: {exc}", error=True)
        print("Не удалось выполнить вставку. Подробности — в логах.")
        
        
def insert_many(conn: psycopg.Connection) -> None:
    """Вставка нескольких строк в одну таблицу."""
    table = choose_table()
    cols = [c for c in ALLOWED_TABLES[table] if c not in NON_UPDATEABLE_COL]
    all_rows: list[tuple] = []

    while True:
        print(f"\nВведите данные строки №{len(all_rows) + 1}:")
        vals = []
        for col in cols:
            val = _input(f"  {col}: ")
            vals.append(val)
        all_rows.append(tuple(vals))
        more = _input("Добавить ещё строку? (y/n): ").lower()
        if more != "y":
            break

    col_list = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

    try:
        with conn.cursor() as cur:
            cur.executemany(sql, all_rows)
        conn.commit()
        print(f"  Вставлено строк: {len(all_rows)}")
    except Exception as exc:
        conn.rollback()
        log(f"Ошибка при массовой вставке: {exc}", error=True)
        print("Не удалось выполнить вставку. Подробности — в логах.")


def insert_many_related(conn: psycopg.Connection) -> None:
    """Вставка нескольких строк в несколько связанных таблиц."""
    print("\n=== Вставка нескольких авторов и их книг (authors → books) ===")
    author_cols = [c for c in ALLOWED_TABLES["authors"] if c != "id"]

    n_authors = _input("Сколько авторов вставить? ")
    try:
        
        n_authors = int(n_authors)
    except ValueError:
        print("Неверное число.")
        return

    pairs: list[tuple[tuple, list[tuple]]] = []  # (author_vals, [book_vals, ...])

    for i in range(n_authors):
        print(f"\nАвтор №{i + 1}:")
        a_vals = tuple(_input(f"  {c}: ") for c in author_cols)

        book_cols = [c for c in ALLOWED_TABLES["books"] if c not in ("id", "author_id")]
        books_data: list[tuple] = []
        n_books = _input(f"Сколько книг добавить для автора №{i + 1}? ")
        try:
            n_books = int(n_books)
        except ValueError:
            print("Неверное число.")
            return
        for j in range(n_books):
            print(f"  Книга №{j + 1}:")
            b_vals = tuple(_input(f"    {c}: ") for c in book_cols)
            books_data.append(b_vals)

        pairs.append((a_vals, books_data))

    # Выполняем в одной транзакции
    try:
        author_sql = "INSERT INTO authors ({}) VALUES ({}) RETURNING id".format(
            ", ".join(author_cols),
            ", ".join(["%s"] * len(author_cols)),
        )
        book_cols_full = ["author_id"] + [c for c in ALLOWED_TABLES["books"] if c not in ("id", "author_id")]
        book_sql = "INSERT INTO books ({}) VALUES ({})".format(
            ", ".join(book_cols_full),
            ", ".join(["%s"] * len(book_cols_full)),
        )

        total_authors = 0
        total_books = 0

        with conn.cursor() as cur:
            for a_vals, books in pairs:
                cur.execute(author_sql, a_vals)
                author_id = cur.fetchone()["id"]
                total_authors += 1

                for b_vals in books:
                    cur.execute(book_sql, (str(author_id), *b_vals))
                    total_books += 1

        conn.commit()
        print(f"  Вставлено авторов: {total_authors}, книг: {total_books}")
    except Exception as exc:
        conn.rollback()
        log(f"Ошибка при массовой связанной вставке: {exc}", error=True)
        print("Не удалось выполнить вставку. Подробности — в логах.")



MENU = {
    "1": ("Просмотр: все записи (без фильтра)",             select_all),
    "2": ("Просмотр: фильтр по одной колонке",              select_filter_one),
    "3": ("Просмотр: фильтр по нескольким колонкам",        select_filter_multi),
    "4": ("Обновление: одна запись по id",                  update_one_by_id),
    "5": ("Обновление: несколько записей (IN)",             update_many_by_values),
    "6": ("Вставка: одна строка в одну таблицу",            insert_one),
    "7": ("Вставка: заказ + позиции (две связ. таблицы)",   insert_related),
    "8": ("Вставка: несколько строк в одну таблицу",        insert_many),
    "9": ("Вставка: несколько строк в связ. таблицы",       insert_many_related),
    "0": ("Выход",                                          None),
}


def print_menu() -> None:
    print("\n" + "=" * 50)
    print("  Онлайн-магазин книг — главное меню")
    print("=" * 50)
    for key, (desc, _) in MENU.items():
        print(f"  {key}. {desc}")
    print("=" * 50)


def load_config(filename: str = "config.json") -> dict:
    with open(filename, "r", encoding="utf-8") as fh:
        return json.load(fh)


def get_credentials() -> tuple[str, str]:
    """Получает логин и пароль от пользователя или из переменных окружения."""
    user = os.getenv("DB_USER") or _input("Логин БД: ")
    password = os.getenv("DB_PASSWORD")
    if password is None:
        password = getpass.getpass("Пароль БД: ")
    return user, password


def main() -> None:
    config = load_config()
    user, password = get_credentials()

    try:
        conn = connect(config, user, password)
        log(f"Успешное подключение к PostgreSQL ({config['host']}:{config['port']}/{config['database']})")
    except Exception as exc:
        log(f"Не удалось подключиться к базе данных: {exc}", error=True)
        print("Ошибка подключения к базе данных. Проверьте логин, пароль и доступность сервера.")
        sys.exit(1)

    try:
        while True:
            print_menu()
            choice = _input("Выберите действие: ")
            if choice not in MENU:
                print("Неверный выбор.")
                continue
            desc, action = MENU[choice]
            if action is None:
                log("Пользователь завершил сеанс.")
                print("До свидания!")
                break
            print(f"\n--- {desc} ---")
            action(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()