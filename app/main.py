import os
import asyncio
import secrets
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import FileResponse # Добавлено для фронтенда
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, select

# --- Настройка БД ---
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
class Base(DeclarativeBase):
    pass

# --- Модели SQLAlchemy ---
class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(String)

# --- Схемы Pydantic ---
class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
class ItemCreate(ItemBase):
    pass
class ItemRead(ItemBase):
    id: int
    class Config:
        from_attributes = True

# --- Настройка Авторизации ---

security = HTTPBasic()

# Ваши учетные данные
HARDCODED_USERNAME = "svpayone"
HARDCODED_PASSWORD = "zx8r45n0"

async def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Зависимость для проверки Basic Auth.
    Использует secrets.compare_digest для защиты от атак по времени.
    """
    correct_username = secrets.compare_digest(credentials.username, HARDCODED_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, HARDCODED_PASSWORD)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- Приложение FastAPI ---
app = FastAPI(title="FastAPI + PostgreSQL + Docker")

@app.on_event("startup")
async def on_startup():

    print("Приложение запускается... Попытка подключения к БД.")
    retries = 5
    delay = 3
    for i in range(retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("Подключение к БД успешно, таблицы созданы (или уже существовали).")
            break
        except Exception as e:
            print(f"Не удалось подключиться к БД (попытка {i+1}/{retries}): {e}")
            if i < retries - 1:
                print(f"Повторная попытка через {delay} сек...")
                await asyncio.sleep(delay)
            else:
                print("Не удалось подключиться к БД после нескольких попыток.")

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# --- Эндпоинты API ---
# Мы добавим префикс /api/v1/ ко всем эндпоинтам данных
API_PREFIX = "/api/v1"

@app.get(f"{API_PREFIX}/hello", summary="Приветственное сообщение")
async def read_root():
    """
    Простой эндпоинт, чтобы проверить, что API работает.
    """
    return {"message": "Привет! Это API на FastAPI с PostgreSQL и Docker!"}

@app.post(f"{API_PREFIX}/items/", response_model=ItemRead, summary="Создать новый предмет (защищено)")
async def create_item(
    item: ItemCreate, 
    db: AsyncSession = Depends(get_db), 
    username: str = Depends(get_current_user) # <-- Добавлена авторизация
):
    """
    Создает новый предмет в базе данных.
    Доступно только авторизованным пользователям.
    """
    db_item = Item(name=item.name, description=item.description)
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item

@app.get(f"{API_PREFIX}/items/", response_model=List[ItemRead], summary="Получить список предметов (защищено)")
async def read_items(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db), 
    username: str = Depends(get_current_user) # <-- Добавлена авторизация
):
    """
    Возвращает список предметов с пагинацией.
    Доступно только авторизованным пользователям.
    """
    result = await db.execute(select(Item).offset(skip).limit(limit))
    items = result.scalars().all()
    return items

@app.get(f"{API_PREFIX}/items/{{item_id}}", response_model=ItemRead, summary="Получить предмет по ID (защищено)")
async def read_item(
    item_id: int, 
    db: AsyncSession = Depends(get_db), 
    username: str = Depends(get_current_user) # <-- Добавлена авторизация
):
    """
    Возвращает один предмет по его ID.
    Доступно только авторизованным пользователям.
    """
    result = await db.execute(select(Item).where(Item.id == item_id))
    db_item = result.scalar_one_or_none()
    
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

# --- Эндпоинт для Фронтенда ---

@app.get("/", response_class=FileResponse, include_in_schema=False)
async def read_index():
    """
    Отдает главный файл фронтенда index.html.
    """
    return "index.html"