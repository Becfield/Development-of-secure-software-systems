-- Предметная область: Онлайн-магазин книг
-- Авторы книг
CREATE TABLE authors (
    id          SERIAL PRIMARY KEY,
    full_name   VARCHAR(200) NOT NULL,
    birth_year  INT,
    country     VARCHAR(100)
);

-- Книги
CREATE TABLE books (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(300) NOT NULL,
    author_id   INT NOT NULL REFERENCES authors(id) ON DELETE RESTRICT,
    genre       VARCHAR(100),
    price       NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    stock       INT NOT NULL DEFAULT 0 CHECK (stock >= 0),
    published   INT
);

-- Покупатели
CREATE TABLE customers (
    id          SERIAL PRIMARY KEY,
    full_name   VARCHAR(200) NOT NULL,
    email       VARCHAR(200) NOT NULL UNIQUE,
    phone       VARCHAR(30),
    city        VARCHAR(100)
);

-- Заказы
CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    order_date  TIMESTAMP NOT NULL DEFAULT NOW(),
    status      VARCHAR(50) NOT NULL DEFAULT 'new'
                CHECK (status IN ('new', 'paid', 'shipped', 'delivered', 'cancelled'))
);

-- Позиции заказа
CREATE TABLE order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    book_id     INT NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
    quantity    INT NOT NULL CHECK (quantity > 0),
    unit_price  NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0)
);
