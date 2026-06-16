# BTC Market Making Bot — Binance Testnet

Paper trading implementation of the Avellaneda-Stoikov market making strategy on Binance Testnet. Uses real order book data and live order execution — no real money involved.

Companion project to [market-making-sim](https://github.com/YouLi128/market-making-sim).

---

## Setup

### 1. Get Testnet API Keys

1. Go to **https://testnet.binance.vision**
2. Log in with GitHub
3. Click **Generate HMAC_SHA256 Key** → copy API Key and Secret
4. The testnet faucet gives you free test BTC and USDT automatically

### 2. Configure

```bash
cp .env.example .env
# Edit .env and paste your API key and secret
```

### 3. Install and Run

```bash
pip install -r requirements.txt
python run_bot.py
```

Press **Ctrl+C** to stop — open orders are cancelled automatically on exit.

---

## How It Works

```
WebSocket (best bid/ask) ─────────────┐
                                       ▼
                              every 5 seconds:
                              1. check fills → update position
                              2. cancel old orders
                              3. AS strategy → new bid/ask prices
                              4. place limit orders on Binance Testnet
```

**Strategy (Avellaneda-Stoikov):**
```
reservation price  r = mid − γ · inventory · τ
bid = r − δ(τ)     ask = r + δ(τ)
δ(τ) = δ₀·τ + δ_min   (narrows toward session end)
```

When long → ask gets cheaper → inventory sells down.  
When short → bid gets dearer → inventory buys back.

---

## Configuration (`config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SYMBOL` | BTCUSDT | Trading pair |
| `LOT_SIZE` | 0.001 BTC | Order size |
| `QUOTE_INTERVAL` | 5s | Requote frequency |
| `DELTA` | $50 | Baseline half-spread |
| `GAMMA` | 50 | Inventory skew sensitivity |
| `MAX_INVENTORY` | 0.05 BTC | Hard inventory cap |

---

## File Structure

```
btc-mm-bot/
├── bot/
│   ├── exchange.py   # Binance Testnet REST client (HMAC-signed)
│   ├── feed.py       # WebSocket real-time best bid/ask
│   ├── strategy.py   # Baseline + AS quote generation
│   └── tracker.py    # Position, cash, P&L tracking
├── run_bot.py        # Main async event loop
├── config.py         # Parameters
└── .env.example      # API key template
```

---

## References

Avellaneda, M. & Stoikov, S. (2008). *High-frequency trading in a limit order book*. Quantitative Finance, 8(3), 217–224.
