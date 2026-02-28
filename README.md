# 🚀 Multi-DEX Market Execution Engine

An **event-driven, asynchronous market execution engine** that simulates token swaps across two Solana-based DEXs — Raydium and Meteora.

The system models realistic execution flow (routing → transaction building → submission → confirmation) and provides real-time updates via WebSockets.

> It is a smart order routing and execution simulator.

---

## 🧠 Key Features

* Async order queue with concurrent workers
* Smart routing across multiple DEXs (mocked)
* Execution lifecycle state machine
* Redis-backed fast state layer
* SQLite persistence layer
* Real-time WebSocket updates
* Structured order logging
* REST API + minimal frontend UI

---

## 🏗 Architecture Overview

```
Client (UI / API)
        ↓
FastAPI REST Endpoint
        ↓
Persist Order (SQLite)
        ↓
Async ORDER_QUEUE
        ↓
Concurrent Workers (x10)
        ↓
Mock DEX Routing
        ↓
Redis State Update
        ↓
WebSocket Notification
        ↓
Final DB Update
```

---

## 🔄 Order Lifecycle

Each order transitions through the following states:

```
pending → routing → building → submitted → confirmed
                               ↘ failed
```

At every stage:

* Redis state is updated
* SQLite is persisted
* WebSocket notifications are pushed to connected clients

---

## ⚙️ Tech Stack

* **Python 3.11** — core execution engine
* **FastAPI** — async REST + WebSocket server
* **Asyncio** — concurrency & worker orchestration
* **Redis** — in-memory state + pub/sub
* **SQLite (SQLAlchemy)** — persistent storage
* **Pydantic** — request validation
* **HTML / JavaScript** — minimal local UI

---

## 📁 Project Structure

```
.
├── app.py               # FastAPI app & routing
├── workers.py           # Background async executors
├── websocket_manager.py # WebSocket connection manager
├── models.py            # Order models + mock DEX router
├── utils.py             # DB + Redis helpers
├── db.py                # Database configuration
├── static/index.html    # Minimal frontend UI
└── requirements.txt
```

---

## 🚀 Getting Started

### 1️⃣ Start Redis

```
redis-server &
```

### 2️⃣ Install Dependencies

```
pip install -r requirements.txt
```

### 3️⃣ Run the Server

```
python app.py
```

### 4️⃣ Open the UI

Navigate to:

```
http://localhost:8000
```

Submit a market order and observe real-time execution updates.

---

## 📊 Database Inspection

Orders are stored in:

```
orders.db
```

Inspect via CLI:

```
sqlite3 orders.db
.tables
SELECT * FROM orders;
```

You can also use GUI tools like DB Browser for SQLite or TablePlus.

---

## 📈 Why Market Orders?

Market orders prioritize execution speed — critical in volatile crypto markets.
They serve as a strong baseline for stress-testing routing and execution logic.

---

## 🔮 Future Improvements

* Integrate real DEX SDKs
* Add slippage tolerance controls
* Support limit order execution
* Add retry logic with exponential backoff
* Introduce latency metrics
* Dockerize deployment
* Replace SQLite with PostgreSQL

---

## 🧑‍💻 Contributing

1. Fork the repository
2. Create a new feature branch
3. Submit a pull request

---

## 📬 License

MIT — free to use and extend.
