# ETH Token Tracker (FastAPI + React)

Track freshly-created Uniswap pairs in near-real time, run safety checks (honeypot / ownership), compute liquidity, and surface alerts for watch-listed deployers.  
Backend: **FastAPI + web3.py + MongoDB**. Frontend: **React**.

**Live**  
- Frontend: `https://eth-tracker-front.onrender.com`  
- Backend (API root): `https://eth-tracker-7c4b.onrender.com/api/`

---

## Features

- Live listener for Uniswap **PairCreated** events (WebSocket RPC)
- Per-token analysis:
  - Liquidity (ETH)
  - Honeypot simulation (buy/sell)
  - Ownership renounced check
  - Metadata retrieval
- Watchlist alerts for specific deployers
- **Idempotent DB writes** (Mongo upsert on `tx_hash + log_index`, unique sparse index)
- Dashboards:
  - **Token Events** (today; search & filters)
  - **Historical Data** (all time; search & filters)
  - **Wallet Alerts** (watchlist hits)
- Production-friendly: CORS + Render rewrites

---

## Tech Stack

- **Python 3**
- **[Web3.py](https://web3py.readthedocs.io/)** – Ethereum blockchain interaction
- **FastAPI**
- **MongoDB**
- **React** - UI

---

## Potential Use Cases

- Detect **rug pulls** and scam tokens early
- Monitor **insider or influencer wallet activity**
- Research token launches and liquidity trends









