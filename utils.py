import os
import sqlite3

# Удаляем старый файл базы данных (если существует)
try:
    os.remove("db.sqlite3")
except OSError as e:
    print(f"Ошибка при удалении файла: {e}")
else:
    print("Файл успешно удалён.")

# Создаем новую базу данных и создаем нужные таблицы
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Первая таблица: users
cursor.executescript('''
    DROP TABLE IF EXISTS users;
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number TEXT,
        name TEXT
    );

    INSERT INTO users (number, name) VALUES
        ('+79112223344', 'Иван Петров'),
        ('+79223334455', 'Анна Смирнова'),
        ('+79334445566', 'Сергей Васильев'),
        ('+79445556677', 'Елена Кузнецова'),
        ('+79556667788', 'Андрей Иванов');
''')

# Вторая таблица: equipment
cursor.executescript('''
    DROP TABLE IF EXISTS equipment;
    CREATE TABLE equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        state_number TEXT,
        brand TEXT,
        model TEXT,
        year INTEGER
    );
''')

# Вставка данных в таблицу equipment
cursor.executemany('''
    INSERT INTO equipment (state_number, brand, model, year) VALUES (?, ?, ?, ?)
''', [
    ('В488НР', 'Toyota', 'Camry', 2018),
    ('B456BB', 'Ford', 'Focus', 2015),
    ('C789CC', 'Volkswagen', 'Passat', 2020),
    ('D012DD', 'Nissan', 'Qashqai', 2019),
    ('E345EE', 'Lada', 'Vesta', 2022)
])

# Третья таблица: telegram_messages
cursor.executescript('''
    DROP TABLE IF EXISTS telegram_messages;
    CREATE TABLE telegram_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_phone TEXT,
        state_number TEXT,
        date_time TEXT,
        description TEXT,
        photo_file_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
''')

# Сохраняем изменения и закрываем соединение
conn.commit()
conn.close()

print("Новая база данных создана и заполнена необходимыми таблицами.")
