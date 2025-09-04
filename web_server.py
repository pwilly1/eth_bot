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
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException


# Data storage
token_events = [] # This will eventually be replaced by MongoDB
wallet_alerts = []
status_messages = ["Starting..."]

# MongoDB Connection
load_dotenv() # Load .env for local MONGO_URI
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("MONGO_URI not found in .env file. MongoDB will not be connected.")
    # Handle this case appropriately, maybe exit or raise an error
    # For now, we'll just set client to None and handle it in functions
    client = None
    db = None
    token_collection = None
else:
    client = MongoClient(MONGO_URI)
    db = client.eth_bot_db # You can change your database name here
    token_collection = db.token_events # Collection for token events

def run_blockchain_listener():
    global token_events, wallet_alerts, status_messages, client, db, token_collection
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
            if not web3.is_connected():
                print("Web3 is not connected. Reconnecting...")
                web3 = Web3(Web3.LegacyWebSocketProvider(wss))
                factory_contract = web3.eth.contract(address=UNISWAP_FACTORY, abi=PAIR_CREATED_ABI)
                event_filter = web3.eth.filter({
                    "address": UNISWAP_FACTORY,
                    "topics": [event_signature]
                })
                status_messages.append("Reconnected to Web3 provider.")
                time.sleep(5) # Give some time for connection to establish
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

                token_info = {
                    'address': token0,
                    'pair_address': pair,
                    'liquidity_eth': result['liquidity_eth'],
                    'honeypot': result['honeypot'],
                    'ownership_renounced': result['ownership_renounced'],
                    'token0_info': result['token0'],
                    'token1_info': result['token1'],
                    'timestamp': time.time() # Store as Unix timestamp
                }
                
                # Save to MongoDB
                if token_collection:
                    try:
                        
                        token_info = {
                            "address": str(token0),
                            "pair_address": str(pair),
                            "liquidity_eth": float(result.get("liquidity_eth", 0)),
                            "honeypot": bool(result.get("honeypot", False)),
                            "ownership_renounced": bool(result.get("ownership_renounced", False)),
                            
                            "token0_info": {
                                "name":  str(result.get("token0", {}).get("name", "")),
                                "symbol":str(result.get("token0", {}).get("symbol", "")),
                                "address":str(result.get("token0", {}).get("address", "")),
                            },
                            "token1_info": {
                                "name":  str(result.get("token1", {}).get("name", "")),
                                "symbol":str(result.get("token1", {}).get("symbol", "")),
                                "address":str(result.get("token1", {}).get("address", "")),
                            },
                            "timestamp": int(time.time()),  # seconds
                        }

                        token_collection.insert_one(token_info)
                        print(f"Token info saved to MongoDB: {token_info['address']}")
                    except Exception as mongo_e:
                        print(f"Error saving to MongoDB: {mongo_e}")
                
                # Keep in memory for current session display (optional, can remove if only using DB)
                token_events.append(token_info) 

            if wallet_tracker_thread and not wallet_tracker_thread.is_alive():
                wallet_alerts.append("Wallet tracker thread finished.")

            time.sleep(1)

        except Exception as e:
            error_message = f"Error in blockchain listener: {e}"
            print(error_message)
            status_messages.append(error_message)
            if "filter not found" in str(e):
                print("Filter not found. Recreating filter...")
                # Recreate the filter
                event_filter = web3.eth.filter({
                    "address": UNISWAP_FACTORY,
                    "topics": [event_signature]
                })
                status_messages.append("Blockchain filter re-created.")
            time.sleep(5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the blockchain listener in a background thread
    listener_thread = threading.Thread(target=run_blockchain_listener, daemon=True)
    listener_thread.start()
    yield
    # Clean up the resources if needed
    print("Shutting down...")
    if client:
        client.close()
        print("MongoDB client closed.")

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://eth-tracker-front.onrender.com",  # your frontend
        "http://localhost:3000",                   # for local dev
        "http://127.0.0.1:3000"
    ],
    allow_credentials=False,
    allow_methods=["*"],  # allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # allow all headers
)


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
    try:
        if token_collection:
            fields = {
                "_id": 0,
                "timestamp": 1,
                "address": 1,
                "liquidity_eth": 1,
                "honeypot": 1,
                "ownership_renounced": 1,
            }
            docs = list(token_collection.find({}, fields).sort("timestamp", -1).limit(200))
            # defensive coercion (in case Mongo stored Decimals, etc.)
            safe = []
            for d in docs:
                safe.append({
                    "timestamp": int(d.get("timestamp", 0)),
                    "address": str(d.get("address", "")),
                    "liquidity_eth": float(d.get("liquidity_eth", 0.0)),
                    "honeypot": bool(d.get("honeypot", False)),
                    "ownership_renounced": bool(d.get("ownership_renounced", False)),
                })
            return {"token_events": safe}
        # fallback to in-memory if Mongo is not configured
        safe_mem = [{
            "timestamp": int(e.get("timestamp", 0)),
            "address": str(e.get("address", "")),
            "liquidity_eth": float(e.get("liquidity_eth", 0.0)),
            "honeypot": bool(e.get("honeypot", False)),
            "ownership_renounced": bool(e.get("ownership_renounced", False)),
        } for e in token_events]
        return {"token_events": safe_mem}
    except Exception as ex:
        # surfaces a readable 500 to the client (and keeps logs useful)
        raise HTTPException(status_code=500, detail=f"/api/token_events failed: {ex}")

@app.get("/api/wallet_alerts")
def get_wallet_alerts():
    return {"wallet_alerts": wallet_alerts}

@app.get("/api/historical_data")
def get_historical_data():
    try:
        if token_collection:
            # include names/symbols too
            fields = {
                "_id": 0,
                "timestamp": 1,
                "address": 1,
                "liquidity_eth": 1,
                "honeypot": 1,
                "ownership_renounced": 1,
                "token0_info": 1,
                "token1_info": 1,
            }
            docs = list(token_collection.find({}, fields).sort("timestamp", -1).limit(500))
        else:
            docs = token_events

        out = []
        for e in docs:
            t0 = e.get("token0_info") or e.get("token0") or {}
            t1 = e.get("token1_info") or e.get("token1") or {}
            out.append({
                # convert to ms so your current React code displays correct times
                "timestamp": int(e.get("timestamp", 0)) * 1000,
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
            })
        return out
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"/api/historical_data failed: {ex}")
