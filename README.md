# Uniswap Token & Wallet Tracker

A **real-time Uniswap monitoring and analysis tool** built with **Python, Web3.py, and Dear PyGui**.  
It continuously listens for **new liquidity pair creations** on Uniswap, automatically analyzes tokens for safety, and can also track wallet activity for known addresses.

---

##  Features

- ** Live Uniswap Pair Detection**  
  Monitors the Ethereum blockchain for new Uniswap liquidity pairs in real time.

- ** Automated Token Analysis**  
  - Fetches token metadata (name, symbol, decimals, etc)  
  - Checks for **honeypots** via simulated buy/sell  
  - Verifies **ownership renouncement**  
  - Evaluates **liquidity in ETH**

- ** Wallet Activity Tracking**  
  Watches on-chain ERC-20 transfers involving addresses in a custom watchlist.

- ** GUI Dashboard** *(Dear PyGui)*  
  - Displays live token events with filtering and search  
  - Historical data viewer  
  - Wallet alert feed

- ** Persistent Logging**  
  Saves analysis results and wallet alerts to JSON logs for later review.

---

## Tech Stack

- **Python 3**
- **[Web3.py](https://web3py.readthedocs.io/)** – Ethereum blockchain interaction
- **[Dear PyGui](https://github.com/hoffstadt/DearPyGui)** – GUI dashboard
- **[python-dotenv](https://pypi.org/project/python-dotenv/)** – Secure configuration management

---

## Potential Use Cases

- Detect **rug pulls** and scam tokens early
- Monitor **insider or influencer wallet activity**
- Research token launches and liquidity trends

---


---

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git](https://github.com/pwilly1/eth_bot.git

   pip install web3 dearpygui python-dotenv
   

Set up your .env file in the project root:

WEB3_PROVIDER=wss://mainnet.infura.io/ws/v3/PROJECT_ID

PUBLIC_ADDRESS=0xWALLET_ADDRESS

Optional: Add your Watchlist Addresses to watchlist.json

Run the main script:

```bash
python main.py





