import sqlite3
import sys
import getpass
from passlib.context import CryptContext

# --- Контекст хэширования ---
# Этот контекст должен быть идентичен тому, что в main.py
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    print("Ошибка: Библиотека 'passlib' или 'bcrypt' не установлена.")
    print("Пожалуйста, установите зависимости: pip install -r requirements.txt")
    sys.exit(1)

# --- Настройки ---
DATABASE_FILE = 'rfid_cards.db'

def get_password_hash(password):
    """Хэширует пароль"""
    return pwd_context.hash(password)

def create_user():
    """
    Интерактивно создает нового пользователя в базе данных.
    """
    print("--- Создание нового пользователя SVPAY ---")
    
    # 1. Запросить имя пользователя
    username = input("Введите имя пользователя: ").strip()
    if not username:
        print("\nОшибка: Имя пользователя не может быть пустым.")
        return

    # 2. Запросить пароль (скрытый ввод)
    try:
        password = getpass.getpass("Введите пароль (будет скрыт): ")
        if not password:
            print("\nОшибка: Пароль не может быть пустым.")
            return
            
        password_confirm = getpass.getpass("Повторите пароль: ")
        if password != password_confirm:
            print("\nОшибка: Пароли не совпадают.")
            return
            
    except (EOFError, KeyboardInterrupt):
        print("\nОтмена операции.")
        return

    # 3. Валидация пароля (такая же, как в main.py)
    if len(password.encode('utf-8')) > 72:
        print(f"\nОшибка: Пароль слишком длинный. Максимум 72 байта (UTF-8).")
        print(f"Ваш пароль имеет длину {len(password.encode('utf-8'))} байт.")
        return

    # 4. Хэшировать пароль
    try:
        hashed_password = get_password_hash(password)
    except Exception as e:
        print(f"\nОшибка при хэшировании пароля: {e}")
        return

    # 5. Подключиться к БД и вставить пользователя
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        
        # Убедимся, что таблица существует (на всякий случай)
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL
            )
        ''')
        
        # Вставляем пользователя
        c.execute(
            "INSERT INTO users (username, hashed_password) VALUES (?, ?)",
            (username, hashed_password)
        )
        conn.commit()
        print(f"\nУспех! Пользователь '{username}' успешно создан.")
        
    except sqlite3.IntegrityError:
        print(f"\nОшибка: Пользователь с именем '{username}' уже существует.")
    except sqlite3.Error as e:
        print(f"\nОшибка базы данных SQLite: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    create_user()
