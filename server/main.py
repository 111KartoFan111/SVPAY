from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
from datetime import datetime
import uvicorn

app = FastAPI(title="RFID Balance Management System")

# Database setup
def init_db():
    conn = sqlite3.connect('rfid_cards.db')
    c = conn.cursor()
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
    conn.commit()
    conn.close()

init_db()

# Pydantic models
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

# Helper functions
def get_db():
    conn = sqlite3.connect('rfid_cards.db')
    conn.row_factory = sqlite3.Row
    return conn

# API Endpoints

@app.get("/")
async def root():
    with open("../frontend/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/cards", response_model=CardResponse)
async def create_card(card: Card):
    """Create a new RFID card"""
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
async def get_all_cards(search: Optional[str] = None):
    """Get all cards or search by name/UID"""
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
async def get_card(card_id: int):
    """Get specific card by ID"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(status_code=404, detail="Card not found")
    
    return dict(result)

@app.get("/api/cards/uid/{rfid_uid}", response_model=CardResponse)
async def get_card_by_uid(rfid_uid: str):
    """Get card by RFID UID (for ESP8266)"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM cards WHERE rfid_uid = ?", (rfid_uid,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(status_code=404, detail="Card not found")
    
    return dict(result)

@app.put("/api/cards/{card_id}", response_model=CardResponse)
async def update_card(card_id: int, card_update: CardUpdate):
    """Update card name or balance"""
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
async def add_balance(card_id: int, balance_update: BalanceUpdate):
    """Add balance to card (quick commands +5, +10, +20)"""
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
    """Use one wash from card balance (called by ESP8266)"""
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
async def delete_card(card_id: int):
    """Delete a card"""
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
async def get_card_transactions(card_id: int, limit: int = 50):
    """Get transaction history for a card"""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM transactions WHERE card_id = ? ORDER BY timestamp DESC LIMIT ?",
        (card_id, limit)
    )
    results = c.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7000)
