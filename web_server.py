import json
from fastapi import FastAPI
from web3 import Web3
from dotenv import load_dotenv
from Core.analyzer.token_analyzer import TokenAnalyzer
from Core.wallet_tracker import WalletTracker
import os
import time
import threading
import asyncio
from contextlib import asynccontextmanager

# Data storage
token_events = []
wallet_alerts = []
status_messages = ["Starting..."]

def run_blockchain_listener():
    global token_events, wallet_alerts, status_messages
    print("▶ run_blockchain_listener STARTED", flush=True)
    status_messages.append("Blockchain listener started...")

    # === Load .env ===
    load_dotenv()
    wss = os.getenv("WEB3_PROVIDER")
    if not wss:
        print("WEB3_PROVIDER not found in .env file.")
        status_messages.append("Error: WEB3_PROVIDER not configured.")
        return
    web3 = Web3(Web3.LegacyWebSocketProvider(wss))
    PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")

    # === Load config and ABI ===
    with open("resources/config.json") as f:
        config = json.load(f)

    UNISWAP_FACTORY = config["UNISWAP_FACTORY"]
    PAIR_CREATED_SIGNATURE = config["PAIR_CREATED_SIGNATURE"]

    with open("resources/abis.json") as f:
        PAIR_CREATED_ABI = json.load(f)

    with open("resources/watchlist.json") as f:
        WATCHLIST = [addr.lower() for addr in json.load(f)]

    factory_contract = web3.eth.contract(address=UNISWAP_FACTORY, abi=PAIR_CREATED_ABI)
    event_signature = web3.keccak(text=PAIR_CREATED_SIGNATURE).hex()
    event_filter = web3.eth.filter({
        "address": UNISWAP_FACTORY,
        "topics": [event_signature]
    })

    status_messages.append("Connected & listening...")
    print("Watching for new token pairs on Uniswap...")

    while True:
        try:
            wallet_tracker_thread = None
            for log in event_filter.get_new_entries():
                event = factory_contract.events.PairCreated().process_log(log)
                token0 = event["args"]["token0"]
                token1 = event["args"]["token1"]
                pair = event["args"]["pair"]

                tx = web3.eth.get_transaction(log["transactionHash"])
                deployer = tx["from"].lower()
                
                if deployer in WATCHLIST:
                    message = f"Deployer {deployer} is in watchlist!"
                    print(f"⚠️ {message}")
                    wallet_alerts.append(message)
                    tracked = {token0.lower(), token1.lower()}
                    wallet_tracker = WalletTracker(web3, tracked, WATCHLIST)
                    wallet_tracker_thread = threading.Thread(target=wallet_tracker.run, daemon=True)
                    wallet_tracker_thread.start()

                analyzer = TokenAnalyzer(web3, token0, token1, pair, config["UNISWAP_ROUTER"], PUBLIC_ADDRESS)
                result = analyzer.analyze()

                token_info = {
                    'address': token0,
                    'pair_address': pair,
                    'liquidity_eth': result['liquidity_eth'],
                    'honeypot': result['honeypot'],
                    'ownership_renounced': result['ownership_renounced'],
                    'token0_info': result['token0'],
                    'token1_info': result['token1'],
                    'timestamp': time.time()
                }
                token_events.append(token_info)

            if wallet_tracker_thread and not wallet_tracker_thread.is_alive():
                wallet_alerts.append("Wallet tracker thread finished.")

            time.sleep(1)

        except Exception as e:
            error_message = f"Error in blockchain listener: {e}"
            print(error_message)
            status_messages.append(error_message)
            time.sleep(5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the blockchain listener in a background thread
    listener_thread = threading.Thread(target=run_blockchain_listener, daemon=True)
    listener_thread.start()
    yield
    # Clean up the resources if needed
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

@app.get("/api/")
def read_root():
    return {"status": "ok"}

@app.get("/api/watchlist")
def read_watchlist():
    with open("resources/watchlist.json", "r") as f:
        watchlist = json.load(f)
    return {"watchlist": watchlist}

@app.get("/api/status")
def get_status():
    return {"status": status_messages[-1] if status_messages else "No status yet."}

@app.get("/api/token_events")
def get_token_events():
    return {"token_events": token_events}

@app.get("/api/wallet_alerts")
def get_wallet_alerts():
    return {"wallet_alerts": wallet_alerts}

@app.get("/api/historical_data")
def get_historical_data():
    try:
        with open("logs/tokens.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "No historical data found."}
    except json.JSONDecodeError:
        return {"error": "Could not parse historical data."}
