# 📡 API Documentation & Examples

## Base URL
```
http://YOUR_SERVER_IP:7000
```

---

## 🃏 Cards Management

### 1. Get All Cards
**Endpoint:** `GET /api/cards`

**Example:**
```bash
curl http://localhost:7000/api/cards
```

**Response:**
```json
[
  {
    "id": 1,
    "rfid_uid": "A1B2C3D4",
    "name": "Иван Иванов",
    "balance": 15,
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-20T14:45:00"
  }
]
```

---

### 2. Search Cards
**Endpoint:** `GET /api/cards?search={query}`

**Example:**
```bash
curl "http://localhost:7000/api/cards?search=Иван"
```

---

### 3. Get Card by ID
**Endpoint:** `GET /api/cards/{card_id}`

**Example:**
```bash
curl http://localhost:7000/api/cards/1
```

---

### 4. Get Card by UID
**Endpoint:** `GET /api/cards/uid/{rfid_uid}`

**Example:**
```bash
curl http://localhost:7000/api/cards/uid/A1B2C3D4
```

This endpoint is primarily used by ESP8266 to check card existence.

---

### 5. Create New Card
**Endpoint:** `POST /api/cards`

**Request Body:**
```json
{
  "rfid_uid": "E5F6G7H8",
  "name": "Мария Петрова",
  "balance": 10
}
```

**Example:**
```bash
curl -X POST http://localhost:7000/api/cards \
  -H "Content-Type: application/json" \
  -d '{
    "rfid_uid": "E5F6G7H8",
    "name": "Мария Петрова",
    "balance": 10
  }'
```

**Response:**
```json
{
  "id": 2,
  "rfid_uid": "E5F6G7H8",
  "name": "Мария Петрова",
  "balance": 10,
  "created_at": "2025-01-21T11:00:00",
  "updated_at": "2025-01-21T11:00:00"
}
```

---

### 6. Update Card
**Endpoint:** `PUT /api/cards/{card_id}`

**Request Body:**
```json
{
  "name": "Иван Петров",
  "balance": 20
}
```

**Example:**
```bash
curl -X PUT http://localhost:7000/api/cards/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Иван Петров",
    "balance": 20
  }'
```

You can update only `name`, only `balance`, or both.

---

### 7. Add Balance (Quick Commands)
**Endpoint:** `POST /api/cards/{card_id}/add-balance`

**Request Body:**
```json
{
  "amount": 10
}
```

**Example:**
```bash
# Add 10 washes
curl -X POST http://localhost:7000/api/cards/1/add-balance \
  -H "Content-Type: application/json" \
  -d '{"amount": 10}'

# Add 5 washes
curl -X POST http://localhost:7000/api/cards/1/add-balance \
  -H "Content-Type: application/json" \
  -d '{"amount": 5}'
```

**Response:**
```json
{
  "id": 1,
  "rfid_uid": "A1B2C3D4",
  "name": "Иван Иванов",
  "balance": 25,
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-21T12:00:00"
}
```

---

### 8. Use Card (ESP8266 Endpoint)
**Endpoint:** `POST /api/cards/uid/{rfid_uid}/use`

**Example:**
```bash
curl -X POST http://localhost:7000/api/cards/uid/A1B2C3D4/use
```

**Success Response (balance > 0):**
```json
{
  "success": true,
  "message": "Wash activated",
  "remaining_balance": 14
}
```

**Error Response (insufficient balance):**
```json
{
  "detail": "Insufficient balance"
}
```
Status Code: 400

**Error Response (card not found):**
```json
{
  "detail": "Card not found"
}
```
Status Code: 404

---

### 9. Delete Card
**Endpoint:** `DELETE /api/cards/{card_id}`

**Example:**
```bash
curl -X DELETE http://localhost:7000/api/cards/1
```

**Response:**
```json
{
  "success": true,
  "message": "Card deleted"
}
```

---

## 📊 Transaction History

### Get Card Transactions
**Endpoint:** `GET /api/transactions/{card_id}?limit={limit}`

**Parameters:**
- `limit` (optional): Number of transactions to return (default: 50)

**Example:**
```bash
curl http://localhost:7000/api/transactions/1?limit=10
```

**Response:**
```json
[
  {
    "id": 15,
    "card_id": 1,
    "amount": -1,
    "transaction_type": "use",
    "timestamp": "2025-01-21T14:30:00"
  },
  {
    "id": 14,
    "card_id": 1,
    "amount": 10,
    "transaction_type": "add_balance",
    "timestamp": "2025-01-21T12:00:00"
  },
  {
    "id": 13,
    "card_id": 1,
    "amount": 15,
    "transaction_type": "initial",
    "timestamp": "2025-01-15T10:30:00"
  }
]
```

**Transaction Types:**
- `initial` - Initial balance when card was created
- `add_balance` - Balance was added via quick commands
- `manual_update` - Manual balance update via edit form
- `use` - Balance was used (wash activated)

---

## 🧪 Testing Scripts

### Python Testing Script

Create file `test_api.py`:

```python
import requests
import json

BASE_URL = "http://localhost:7000"

def test_create_card():
    """Test creating a new card"""
    print("Testing: Create Card")
    data = {
        "rfid_uid": "TEST1234",
        "name": "Test User",
        "balance": 5
    }
    response = requests.post(f"{BASE_URL}/api/cards", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.json()['id']

def test_get_cards():
    """Test getting all cards"""
    print("\nTesting: Get All Cards")
    response = requests.get(f"{BASE_URL}/api/cards")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_add_balance(card_id):
    """Test adding balance"""
    print(f"\nTesting: Add Balance to Card {card_id}")
    data = {"amount": 10}
    response = requests.post(f"{BASE_URL}/api/cards/{card_id}/add-balance", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_use_card(uid):
    """Test using a card"""
    print(f"\nTesting: Use Card {uid}")
    response = requests.post(f"{BASE_URL}/api/cards/uid/{uid}/use")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_get_transactions(card_id):
    """Test getting transactions"""
    print(f"\nTesting: Get Transactions for Card {card_id}")
    response = requests.get(f"{BASE_URL}/api/transactions/{card_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    print("=== API Testing ===\n")
    
    # Create test card
    card_id = test_create_card()
    
    # Get all cards
    test_get_cards()
    
    # Add balance
    test_add_balance(card_id)
    
    # Use card
    test_use_card("TEST1234")
    
    # Get transactions
    test_get_transactions(card_id)
    
    print("\n=== Testing Complete ===")
```

Run with:
```bash
python test_api.py
```

---

### Bash Testing Script

Create file `test_api.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:7000"

echo "=== API Testing ==="
echo ""

# Test 1: Create Card
echo "1. Creating test card..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/cards" \
  -H "Content-Type: application/json" \
  -d '{
    "rfid_uid": "BASH_TEST",
    "name": "Bash Test User",
    "balance": 5
  }')
echo "Response: $RESPONSE"
CARD_ID=$(echo $RESPONSE | grep -o '"id":[0-9]*' | grep -o '[0-9]*')
echo "Created Card ID: $CARD_ID"
echo ""

# Test 2: Get All Cards
echo "2. Getting all cards..."
curl -s "$BASE_URL/api/cards" | json_pp
echo ""

# Test 3: Add Balance
echo "3. Adding balance..."
curl -s -X POST "$BASE_URL/api/cards/$CARD_ID/add-balance" \
  -H "Content-Type: application/json" \
  -d '{"amount": 10}' | json_pp
echo ""

# Test 4: Use Card
echo "4. Using card..."
curl -s -X POST "$BASE_URL/api/cards/uid/BASH_TEST/use" | json_pp
echo ""

# Test 5: Get Transactions
echo "5. Getting transactions..."
curl -s "$BASE_URL/api/transactions/$CARD_ID" | json_pp
echo ""

echo "=== Testing Complete ==="
```

Run with:
```bash
chmod +x test_api.sh
./test_api.sh
```

---

## 🔐 ESP8266 Integration Examples

### Example 1: Check Card Balance Before Use

```cpp
bool checkCardBalance(String uid) {
  HTTPClient http;
  String url = String(serverUrl) + "/api/cards/uid/" + uid;
  
  http.begin(wifiClient, url);
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    String payload = http.getString();
    DynamicJsonDocument doc(512);
    deserializeJson(doc, payload);
    
    int balance = doc["balance"];
    Serial.print("Current balance: ");
    Serial.println(balance);
    
    http.end();
    return balance > 0;
  }
  
  http.end();
  return false;
}
```

### Example 2: Get Card Name for Display

```cpp
String getCardName(String uid) {
  HTTPClient http;
  String url = String(serverUrl) + "/api/cards/uid/" + uid;
  
  http.begin(wifiClient, url);
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    String payload = http.getString();
    DynamicJsonDocument doc(512);
    deserializeJson(doc, payload);
    
    String name = doc["name"].as<String>();
    http.end();
    return name;
  }
  
  http.end();
  return "Unknown";
}
```

---

## 📱 Mobile App Integration

### React Native Example

```javascript
const BASE_URL = 'http://192.168.1.100:7000';

// Get all cards
const getCards = async () => {
  try {
    const response = await fetch(`${BASE_URL}/api/cards`);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching cards:', error);
    return [];
  }
};

// Add balance
const addBalance = async (cardId, amount) => {
  try {
    const response = await fetch(`${BASE_URL}/api/cards/${cardId}/add-balance`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ amount }),
    });
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error adding balance:', error);
    return null;
  }
};
```

---

## 🐛 Error Codes

| Status Code | Description | Meaning |
|------------|-------------|---------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid data or insufficient balance |
| 404 | Not Found | Card not found |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

---

## 💡 Best Practices

1. **Always check response status codes**
2. **Handle errors gracefully**
3. **Use HTTPS in production** (not implemented in base version)
4. **Implement rate limiting for production**
5. **Log all transactions for audit trail**
6. **Regular database backups**

---

**Happy Coding! 🚀**
