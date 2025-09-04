import json
import os
import time
import threading
import asyncio
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, PyMongoError
from web3 import Web3

from Core.analyzer.token_analyzer import TokenAnalyzer
from Core.wallet_tracker import WalletTracker

# ---------------------------
# In-memory state
# ---------------------------
token_events: List[Dict[str, Any]] = []
wallet_alerts: List[str] = []
status_messages: List[str] = ["Starting..."]

# ---------------------------
# Mongo init (safe)
# ---------------------------
load_dotenv()  # load .env for MONGO_URI / WEB3_PROVIDER / PUBLIC_ADDRESS
MONGO_URI = os.getenv("MONGO_URI")

client = None
db = None
token_collection = None

if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")  # fail fast if unreachable
        db = client["eth_bot_db"]
        token_collection = db["token_events"]
        print("Mongo connected")
    except Exception as e:
        msg = f"Mongo unavailable: {e}"
        print(msg)
        status_messages.append(msg)
        client = db = token_collection = None
else:
    print("MONGO_URI not set; running without Mongo")

# ---------------------------
# Blockchain listener
# ---------------------------
def run_blockchain_listener():
    global token_events, wallet_alerts, status_messages, client, db, token_collection
    print("▶ run_blockchain_listener STARTED", flush=True)
    status_messages.append("Blockchain listener started...")

    wss = os.getenv("WEB3_PROVIDER")
    if not wss:
        print("WEB3_PROVIDER not found in .env file.")
        status_messages.append("Error: WEB3_PROVIDER not configured.")
        return

    web3 = Web3(Web3.LegacyWebSocketProvider(wss))
    PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")

    # Load configs/ABIs/watchlist
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
    event_filter = web3.eth.filter({"address": UNISWAP_FACTORY, "topics": [event_signature]})

    status_messages.append("Connected & listening...")
    print("Watching for new token pairs on Uniswap...")

    while True:
        try:
            if not web3.is_connected():
                print("Web3 is not connected. Reconnecting...")
                web3 = Web3(Web3.LegacyWebSocketProvider(wss))
                factory_contract = web3.eth.contract(address=UNISWAP_FACTORY, abi=PAIR_CREATED_ABI)
                event_filter = web3.eth.filter({"address": UNISWAP_FACTORY, "topics": [event_signature]})
                status_messages.append("Reconnected to Web3 provider.")
                time.sleep(5)
                continue

            wallet_tracker_thread = None

            for log in event_filter.get_new_entries():
                event = factory_contract.events.PairCreated().process_log(log)
                token0 = event["args"]["token0"]
                token1 = event["args"]["token1"]
                pair = event["args"]["pair"]

                tx = web3.eth.get_transaction(log["transactionHash"])
                deployer = tx["from"].lower()

                if deployer in WATCHLIST:
                    message = f"Deployer {deployer} is in watchlist! ✅"
                    print(f"⚠️ {message}")
                    wallet_alerts.append(message)
                    tracked = {token0.lower(), token1.lower()}
                    wallet_tracker = WalletTracker(web3, tracked, WATCHLIST)
                    wallet_tracker_thread = threading.Thread(target=wallet_tracker.run, daemon=True)
                    wallet_tracker_thread.start()

                analyzer = TokenAnalyzer(web3, token0, token1, pair, config["UNISWAP_ROUTER"], PUBLIC_ADDRESS)
                result = analyzer.analyze()

                # JSON-safe, flat shape (coerce types)
                token_info = {
                    "address": str(token0),
                    "pair_address": str(pair),
                    "liquidity_eth": float(result.get("liquidity_eth", 0.0)),
                    "honeypot": bool(result.get("honeypot", False)),
                    "ownership_renounced": bool(result.get("ownership_renounced", False)),
                    "token0_info": {
                        "name":   str(result.get("token0", {}).get("name", "")),
                        "symbol": str(result.get("token0", {}).get("symbol", "")),
                        "address":str(result.get("token0", {}).get("address", "")),
                    },
                    "token1_info": {
                        "name":   str(result.get("token1", {}).get("name", "")),
                        "symbol": str(result.get("token1", {}).get("symbol", "")),
                        "address":str(result.get("token1", {}).get("address", "")),
                    },
                    "timestamp": int(time.time()),  # seconds
                }

                # Save to Mongo (only if connected)
                if token_collection is not None:
                    try:
                        token_collection.insert_one(token_info)
                        print(f"Token info saved to MongoDB: {token_info['address']}")
                    except Exception as mongo_e:
                        print(f"Error saving to MongoDB: {mongo_e}")

                # Keep in memory for current session
                token_events.append(token_info)

            if wallet_tracker_thread and not wallet_tracker_thread.is_alive():
                wallet_alerts.append("Wallet tracker thread finished.")

            time.sleep(1)

        except Exception as e:
            error_message = f"Error in blockchain listener: {e}"
            print(error_message)
            status_messages.append(error_message)

            if "filter not found" in str(e).lower():
                print("Filter not found. Recreating filter...")
                event_filter = web3.eth.filter({"address": UNISWAP_FACTORY, "topics": [event_signature]})
                status_messages.append("Blockchain filter re-created.")

            time.sleep(5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    listener_thread = threading.Thread(target=run_blockchain_listener, daemon=True)
    listener_thread.start()
    yield
    print("Shutting down...")
    if client is not None:
        try:
            client.close()
            print("MongoDB client closed.")
        except Exception:
            pass

app = FastAPI(lifespan=lifespan)

# ---------------------------
# CORS
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://eth-tracker-front.onrender.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# API routes
# ---------------------------
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
    # last status message if any
    return {"status": status_messages[-1] if status_messages else "No status yet."}

@app.get("/api/token_events")
def get_token_events():
    """
    Return only plain JSON types the UI expects; never 500 on bad records.
    """
    try:
        docs: List[Dict[str, Any]] = []
        if token_collection is not None:
            fields = {
                "_id": 0,
                "timestamp": 1,
                "address": 1,
                "liquidity_eth": 1,
                "honeypot": 1,
                "ownership_renounced": 1,
            }
            docs = list(token_collection.find({}, fields).sort("timestamp", -1).limit(200))
        else:
            docs = token_events

        safe = []
        for d in docs:
            safe.append({
                "timestamp": int(d.get("timestamp", 0)),                 # seconds
                "address": str(d.get("address", "")),
                "liquidity_eth": float(d.get("liquidity_eth", 0.0)),
                "honeypot": bool(d.get("honeypot", False)),
                "ownership_renounced": bool(d.get("ownership_renounced", False)),
            })
        return {"token_events": safe}

    except (ServerSelectionTimeoutError, PyMongoError) as e:
        # Fall back to in-memory; do not crash
        status_messages.append(f"Mongo error: {e}")
        safe_mem = [{
            "timestamp": int(e.get("timestamp", 0)),
            "address": str(e.get("address", "")),
            "liquidity_eth": float(e.get("liquidity_eth", 0.0)),
            "honeypot": bool(e.get("honeypot", False)),
            "ownership_renounced": bool(e.get("ownership_renounced", False)),
        } for e in token_events]
        return {"token_events": safe_mem}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"/api/token_events failed: {ex}")

@app.get("/api/wallet_alerts")
def get_wallet_alerts():
    return {"wallet_alerts": wallet_alerts}

@app.get("/api/historical_data")
def get_historical_data():
    """
    Return an array; normalize token0/token1 keys and convert timestamp to ms
    so the current React code renders correctly.
    """
    try:
        docs: List[Dict[str, Any]] = []
        if token_collection is not None:
            fields = {
                "_id": 0,
                "timestamp": 1,
                "liquidity_eth": 1,
                "honeypot": 1,
                "ownership_renounced": 1,
                "token0_info": 1,
                "token1_info": 1,
                "address": 1,
            }
            docs = list(token_collection.find({}, fields).sort("timestamp", -1).limit(500))
        else:
            docs = token_events

        out = []
        for e in docs:
            t0 = e.get("token0_info") or e.get("token0") or {}
            t1 = e.get("token1_info") or e.get("token1") or {}
            out.append({
                "timestamp": int(e.get("timestamp", 0)) * 1000,          # ms (UI expects ms)
                "liquidity_eth": float(e.get("liquidity_eth", 0.0)),
                "honeypot": bool(e.get("honeypot", False)),
                "ownership_renounced": bool(e.get("ownership_renounced", False)),
                "token0": {
                    "name":   str(t0.get("name", "")),
                    "symbol": str(t0.get("symbol", "")),
                    "address":str(t0.get("address", "")),
                },
                "token1": {
                    "name":   str(t1.get("name", "")),
                    "symbol": str(t1.get("symbol", "")),
                    "address":str(t1.get("address", "")),
                },
                "address": str(e.get("address", "")),
            })
        return out
    except (ServerSelectionTimeoutError, PyMongoError) as e:
        status_messages.append(f"Mongo error: {e}")
        return []
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"/api/historical_data failed: {ex}")
