from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
from datetime import datetime, timedelta
import uvicorn
# Импорты для аутентификации
import jwt
from jwt import PyJWTError
from passlib.context import CryptContext

# --- Настройки безопасности ---
# В реальном приложении используйте `openssl rand -hex 32` для генерации ключа
SECRET_KEY = "a_very_secret_key_that_should_be_in_an_env_file"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Контекст для хэширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Схема OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")
# -----------------------------

app = FastAPI(title="RFID Balance Management System")

# --- Управление базой данных ---
def init_db():
    conn = sqlite3.connect('rfid_cards.db')
    c = conn.cursor()
    # Таблица карт
    c.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfid_uid TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            balance INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    # Таблица транзакций
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            amount INTEGER,
            transaction_type TEXT,
            timestamp TEXT,
            FOREIGN KEY (card_id) REFERENCES cards (id)
        )
    ''')
    # НОВАЯ ТАБЛИЦА: Пользователи
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect('rfid_cards.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- Модели Pydantic ---

# Карты
class Card(BaseModel):
    rfid_uid: str
    name: str
    balance: Optional[int] = 0

class CardUpdate(BaseModel):
    name: Optional[str] = None
    balance: Optional[int] = None

class BalanceUpdate(BaseModel):
    amount: int

class CardResponse(BaseModel):
    id: int
    rfid_uid: str
    name: str
    balance: int
    created_at: str
    updated_at: str

# Токен
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Пользователи
class User(BaseModel):
    username: str

class UserInDB(User):
    id: int
    hashed_password: str

    class Config:
        from_attributes = True # Замена orm_mode

class UserCreate(BaseModel):
    username: str
    password: str

# --- Функции безопасности ---

def verify_password(plain_password, hashed_password):
    """Проверяет обычный пароль против хэшированного"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Хэширует пароль"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создает JWT токен"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_from_db(conn: sqlite3.Connection, username: str):
    """Получает пользователя из БД по имени"""
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    if not row:
        return None
    # sqlite3.Row не распознаётся Pydantic как mapping/атрибутный объект — сконвертируем в dict
    user_dict = dict(row)
    return UserInDB.model_validate(user_dict)

def authenticate_user(conn: sqlite3.Connection, username: str, password: str):
    """Аутентифицирует пользователя"""
    user = get_user_from_db(conn, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Зависимость для получения текущего пользователя из токена"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except PyJWTError:
        raise credentials_exception
    
    conn = get_db()
    user = get_user_from_db(conn, username=token_data.username)
    conn.close()
    
    if user is None:
        raise credentials_exception
    return user

# --- Конечные точки (Endpoints) ---

# --- Аутентификация ---

@app.post("/api/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Генерирует токен для входа"""
    conn = get_db()
    user = authenticate_user(conn, form_data.username, form_data.password)
    conn.close()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/users/register", response_model=User)
async def register_user(user: UserCreate):
    """Регистрирует нового пользователя"""
    conn = get_db()
    db_user = get_user_from_db(conn, user.username)
    if db_user:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # НОВАЯ ПРОВЕРКА ДЛИНЫ ПАРОЛЯ (В БАЙТАХ)
    if len(user.password.encode('utf-8')) > 72:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Пароль слишком длинный. Максимум 72 байта (UTF-8)."
        )
    
    hashed_password = get_password_hash(user.password)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (username, hashed_password) VALUES (?, ?)",
            (user.username, hashed_password)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already registered")
    
    conn.close()
    return User(username=user.username)

@app.get("/api/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Возвращает данные текущего пользователя"""
    return current_user

# --- Статика и страницы ---

@app.get("/", response_class=HTMLResponse)
async def root():
    """Обслуживает главную страницу index.html"""
    try:
        with open("../frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="index.html not found")

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Обслуживает страницу входа login.html"""
    try:
        with open("../frontend/login.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # Если login.html не найден, перенаправляем на /
        # (на случай, если фронтенд обрабатывает это)
        return RedirectResponse(url="/")


# --- API Карт (ЗАЩИЩЕНО) ---

@app.post("/api/cards", response_model=CardResponse)
async def create_card(card: Card, current_user: User = Depends(get_current_user)):
    """(Защищено) Создает новую RFID карту"""
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    try:
        c.execute(
            "INSERT INTO cards (rfid_uid, name, balance, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (card.rfid_uid, card.name, card.balance, now, now)
        )
        conn.commit()
        card_id = c.lastrowid
        
        # Log transaction
        c.execute(
            "INSERT INTO transactions (card_id, amount, transaction_type, timestamp) VALUES (?, ?, ?, ?)",
            (card_id, card.balance, "initial", now)
        )
        conn.commit()
        
        c.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
        result = c.fetchone()
        conn.close()
        
        return dict(result)
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Card with this UID already exists")

@app.get("/api/cards", response_model=List[CardResponse])
async def get_all_cards(search: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """(Защищено) Получает все карты или ищет по имени/UID"""
    conn = get_db()
    c = conn.cursor()
    
    if search:
        c.execute(
            "SELECT * FROM cards WHERE name LIKE ? OR rfid_uid LIKE ? ORDER BY updated_at DESC",
            (f"%{search}%", f"%{search}%")
        )
    else:
        c.execute("SELECT * FROM cards ORDER BY updated_at DESC")
    
    results = c.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

@app.get("/api/cards/{card_id}", response_model=CardResponse)
async def get_card(card_id: int, current_user: User = Depends(get_current_user)):
    """(Защищено) Получает карту по ID"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(status_code=404, detail="Card not found")
    
    return dict(result)

@app.get("/api/cards/uid/{rfid_uid}", response_model=CardResponse)
async def get_card_by_uid(rfid_uid: str, current_user: User = Depends(get_current_user)):
    """(Защищено) Получает карту по RFID UID (для ESP8266)"""
    # ПРИМЕЧАНИЕ: Если ESP8266 должен вызывать это, ему тоже нужен токен.
    # Для простоты ESP может использовать /api/cards/uid/{rfid_uid}/use,
    # который может иметь другую (например, на основе API-ключа) аутентификацию.
    # Пока что оставляем защиту токеном.
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM cards WHERE rfid_uid = ?", (rfid_uid,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(status_code=404, detail="Card not found")
    
    return dict(result)

@app.put("/api/cards/{card_id}", response_model=CardResponse)
async def update_card(card_id: int, card_update: CardUpdate, current_user: User = Depends(get_current_user)):
    """(Защищено) Обновляет имя или баланс карты"""
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    c.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
    existing = c.fetchone()
    
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Card not found")
    
    if card_update.name is not None:
        c.execute("UPDATE cards SET name = ?, updated_at = ? WHERE id = ?", 
                 (card_update.name, now, card_id))
    
    if card_update.balance is not None:
        old_balance = existing['balance']
        c.execute("UPDATE cards SET balance = ?, updated_at = ? WHERE id = ?", 
                 (card_update.balance, now, card_id))
        
        # Log transaction
        diff = card_update.balance - old_balance
        c.execute(
            "INSERT INTO transactions (card_id, amount, transaction_type, timestamp) VALUES (?, ?, ?, ?)",
            (card_id, diff, "manual_update", now)
        )
    
    conn.commit()
    
    c.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
    result = c.fetchone()
    conn.close()
    
    return dict(result)

@app.post("/api/cards/{card_id}/add-balance", response_model=CardResponse)
async def add_balance(card_id: int, balance_update: BalanceUpdate, current_user: User = Depends(get_current_user)):
    """(Защищено) Добавляет баланс на карту"""
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    c.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
    existing = c.fetchone()
    
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Card not found")
    
    new_balance = existing['balance'] + balance_update.amount
    c.execute("UPDATE cards SET balance = ?, updated_at = ? WHERE id = ?", 
             (new_balance, now, card_id))
    
    # Log transaction
    c.execute(
        "INSERT INTO transactions (card_id, amount, transaction_type, timestamp) VALUES (?, ?, ?, ?)",
        (card_id, balance_update.amount, "add_balance", now)
    )
    conn.commit()
    
    c.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
    result = c.fetchone()
    conn.close()
    
    return dict(result)

@app.post("/api/cards/uid/{rfid_uid}/use")
async def use_card(rfid_uid: str):
    """(НЕ ЗАЩИЩЕНО) Использует одну стирку с карты (вызывается ESP8266)"""
    # ПРИМЕЧАНИЕ: Эта конечная точка оставлена ОТКРЫТОЙ для простоты
    # интеграции с ESP8266. В реальной системе здесь
    # должен быть API-ключ или другой метод аутентификации.
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    c.execute("SELECT * FROM cards WHERE rfid_uid = ?", (rfid_uid,))
    card = c.fetchone()
    
    if not card:
        conn.close()
        raise HTTPException(status_code=404, detail="Card not found")
    
    if card['balance'] <= 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    new_balance = card['balance'] - 1
    c.execute("UPDATE cards SET balance = ?, updated_at = ? WHERE id = ?", 
             (new_balance, now, card['id']))
    
    # Log transaction
    c.execute(
        "INSERT INTO transactions (card_id, amount, transaction_type, timestamp) VALUES (?, ?, ?, ?)",
        (card['id'], -1, "use", now)
    )
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "message": "Wash activated",
        "remaining_balance": new_balance
    }

@app.delete("/api/cards/{card_id}")
async def delete_card(card_id: int, current_user: User = Depends(get_current_user)):
    """(Защищено) Удаляет карту"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Card not found")
    
    c.execute("DELETE FROM transactions WHERE card_id = ?", (card_id,))
    c.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Card deleted"}

@app.get("/api/transactions/{card_id}")
async def get_card_transactions(card_id: int, limit: int = 50, current_user: User = Depends(get_current_user)):
    """(Защищено) Получает историю транзакций для карты"""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM transactions WHERE card_id = ? ORDER BY timestamp DESC LIMIT ?",
        (card_id, limit)
    )
    results = c.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

