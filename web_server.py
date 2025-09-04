import json
import os
import time
import threading
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError, PyMongoError
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
# Helpers
# ---------------------------
def ensure_unique_index(collection):
    """
    Clean legacy docs with missing or null keys and ensure a UNIQUE SPARSE index
    on (tx_hash, log_index). Sparse means docs missing either field are not
    indexed, so they don't collide. Also prevent inserting nulls in code.
    """
    try:
        # Drop any previous partial or wrong index if it exists
        try:
            collection.drop_index("uniq_txhash_logindex")
        except Exception:
            pass

        # 1) Remove legacy rows that would collide 
        cleanup_filter = {
            "$or": [
                {"tx_hash": {"$exists": False}},
                {"log_index": {"$exists": False}},
                {"tx_hash": None},
                {"log_index": None},
            ]
        }
        try:
            removed = collection.delete_many(cleanup_filter).deleted_count
            if removed:
                print(f"Cleaned {removed} legacy docs without tx_hash/log_index")
        except Exception as e:
            print(f"Warning: cleanup failed (continuing): {e}")

        #   Create UNIQUE SPARSE compound index
        #    (Only documents that contain BOTH fields are indexed.
        #     Missing fields are ignored; nulls would be indexed—so we cleaned them and we skip inserting nulls.)
        collection.create_index(
            [("tx_hash", ASCENDING), ("log_index", ASCENDING)],
            unique=True,
            name="uniq_txhash_logindex",
            sparse=True,
        )
        print("Unique sparse index ensured on (tx_hash, log_index)")
    except PyMongoError as e:
        print(f"Index ensure warning: {e}")

# ---------------------------
# Mongo init (safe)
# ---------------------------
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = db = token_collection = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")  # fail fast if unreachable
        db = client["eth_bot_db"]
        token_collection = db["token_events"]
        print("Mongo connected")

        # Ensure index (do not crash if it fails)
        ensure_unique_index(token_collection)
    except Exception as e:
        msg = f"Mongo connected but index setup hit an issue: {e}"
        print(msg)
        status_messages.append(msg)
        # keep token_collection if connection succeeded
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

                # Watchlist alert / wallet tracker (unchanged)
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

                # ---- Robust identifiers for idempotency
                raw_txh = log.get("transactionHash")
                raw_lix = log.get("logIndex")
                raw_blk = log.get("blockNumber")

                try:
                    tx_hash = raw_txh.hex() if hasattr(raw_txh, "hex") else str(raw_txh)
                except Exception:
                    tx_hash = None

                try:
                    log_index = int(raw_lix) if raw_lix is not None else None
                except Exception:
                    log_index = None

                try:
                    block_number = int(raw_blk) if raw_blk is not None else None
                except Exception:
                    block_number = None

                # If we can't identify uniquely, skip persisting
                if not tx_hash or log_index is None:
                    print("Skipping event: missing tx_hash/log_index")
                    continue

                # pick the non-WETH token for the 'address' field
                try:
                    target_token = analyzer.get_target_token()  # analyzer helper
                except Exception:
                    # fallback: pick non-WETH by symbol in result
                    t0 = result.get("token0", {}) or {}
                    t1 = result.get("token1", {}) or {}
                    target_token = (t1.get("address")
                                    if (t0.get("symbol", "") or "").upper() == "WETH"
                                    else t0.get("address"))

                token_info = {
                    "tx_hash": tx_hash,
                    "log_index": log_index,
                    "block_number": block_number,
                    "address": str(target_token or token0),
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
                    "timestamp": int(time.time()),
                }

                # ---- UPSERT using the unique key; only writes once globally
                inserted = False
                if token_collection is not None:
                    try:
                        res = token_collection.update_one(
                            {"tx_hash": tx_hash, "log_index": log_index},
                            {"$setOnInsert": token_info},
                            upsert=True,
                        )
                        inserted = res.upserted_id is not None
                        print(("Inserted" if inserted else "Duplicate skipped"), f"{tx_hash}:{log_index}")
                    except DuplicateKeyError:
                        inserted = False
                        print(f"DuplicateKeyError: {tx_hash}:{log_index} already exists")
                    except Exception as mongo_e:
                        print(f"Error saving to MongoDB: {mongo_e}")
                else:
                    # in-memory dedupe fallback (no Mongo)
                    global seen_keys
                    try:
                        seen_keys
                    except NameError:
                        seen_keys = set()
                    key = f"{tx_hash}:{log_index}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        inserted = True

                if inserted and token_collection is None:
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
    return {"status": status_messages[-1] if status_messages else "No status yet."}

@app.get("/api/token_events")
def get_token_events(
    q: Optional[str] = Query(None, description="search token address/name/symbol"),
    honeypot: Optional[bool] = Query(None, description="filter honeypot true/false"),
    min_liquidity: Optional[float] = Query(None, description="minimum liquidity in ETH"),
    ownership: Optional[bool] = Query(None, description="ownership renounced true/false"),
    start_ms: Optional[int] = Query(None, description="start time in ms since epoch"),
    end_ms: Optional[int] = Query(None, description="end time in ms since epoch"),
    limit: int = Query(200, description="max results"),
):
    """
    Return only plain JSON types the UI expects; never 500 on bad records.
    Timestamps are returned in **ms** for your UI.
    """
    try:
        docs: List[Dict[str, Any]] = []

        # start of today (UTC): only today's events
        # compute start of today in local timezone and convert to UTC timestamp
        # this ensures "today" matches the local day of the user running the server
        local_now = datetime.now().astimezone()
        start_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_day = int(start_local.astimezone(timezone.utc).timestamp())

        # override start/end if provided (client sends ms)
        if start_ms is not None:
            start_of_day = int(start_ms // 1000)
        end_of_day: Optional[int] = None
        if end_ms is not None:
            end_of_day = int(end_ms // 1000)

        if token_collection is not None:
            query: Dict[str, Any] = {"timestamp": {"$gte": start_of_day}}
            if end_of_day is not None:
                query["timestamp"]["$lte"] = end_of_day
            if honeypot is not None:
                query["honeypot"] = bool(honeypot)
            if min_liquidity is not None:
                query["liquidity_eth"] = {"$gte": float(min_liquidity)}
            if ownership is not None:
                query["ownership_renounced"] = bool(ownership)
            if q:
                regex = {"$regex": q, "$options": "i"}
                query["$or"] = [
                    {"address": regex},
                    {"token0_info.address": regex},
                    {"token1_info.address": regex},
                    {"token0_info.name": regex},
                    {"token1_info.name": regex},
                    {"token0_info.symbol": regex},
                    {"token1_info.symbol": regex},
                ]

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
            docs = list(token_collection.find(query, fields).sort("timestamp", -1).limit(limit))
        else:
            # in-memory fallback
            for e in token_events:
                ts = int(e.get("timestamp", 0))
                if ts < start_of_day:
                    continue
                if end_of_day is not None and ts > end_of_day:
                    continue
                if honeypot is not None and bool(e.get("honeypot", False)) != bool(honeypot):
                    continue
                if min_liquidity is not None and float(e.get("liquidity_eth", 0.0)) < float(min_liquidity):
                    continue
                if ownership is not None and bool(e.get("ownership_renounced", False)) != bool(ownership):
                    continue
                if q:
                    ql = q.lower()
                    found = False
                    for val in [
                        str(e.get("address", "")),
                        str((e.get("token0_info") or {}).get("address", "")),
                        str((e.get("token1_info") or {}).get("address", "")),
                        str((e.get("token0_info") or {}).get("name", "")),
                        str((e.get("token1_info") or {}).get("name", "")),
                        str((e.get("token0_info") or {}).get("symbol", "")),
                        str((e.get("token1_info") or {}).get("symbol", "")),
                    ]:
                        if ql in val.lower():
                            found = True
                            break
                    if not found:
                        continue
                docs.append(e)
            docs = sorted(docs, key=lambda x: int(x.get("timestamp", 0)), reverse=True)[:limit]

        safe = []
        for d in docs:
            safe.append({
                "timestamp": int(d.get("timestamp", 0)) * 1000,  # ms for UI
                "address": str(d.get("address", "")),
                "liquidity_eth": float(d.get("liquidity_eth", 0.0)),
                "honeypot": bool(d.get("honeypot", False)),
                "ownership_renounced": bool(d.get("ownership_renounced", False)),
                "token0": d.get("token0_info") or {},
                "token1": d.get("token1_info") or {},
            })
        return {"token_events": safe}

    except (ServerSelectionTimeoutError, PyMongoError) as e:
        status_messages.append(f"Mongo error: {e}")
        safe_mem = [{
            "timestamp": int(ev.get("timestamp", 0)) * 1000,
            "address": str(ev.get("address", "")),
            "liquidity_eth": float(ev.get("liquidity_eth", 0.0)),
            "honeypot": bool(ev.get("honeypot", False)),
            "ownership_renounced": bool(ev.get("ownership_renounced", False)),
            "token0": ev.get("token0_info") or {},
            "token1": ev.get("token1_info") or {},
        } for ev in token_events]
        return {"token_events": safe_mem}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"/api/token_events failed: {ex}")

@app.get("/api/wallet_alerts")
def get_wallet_alerts():
    return {"wallet_alerts": wallet_alerts}

@app.get("/api/historical_data")
def get_historical_data(
    q: Optional[str] = Query(None, description="search token address/name/symbol"),
    honeypot: Optional[bool] = Query(None, description="filter honeypot true/false"),
    min_liquidity: Optional[float] = Query(None, description="minimum liquidity in ETH"),
    ownership: Optional[bool] = Query(None, description="ownership renounced true/false"),
    start_ms: Optional[int] = Query(None, description="start time in ms since epoch"),
    end_ms: Optional[int] = Query(None, description="end time in ms since epoch"),
    limit: int = Query(500, description="max results"),
):
    """
    Return an array; normalize token0/token1 keys and convert timestamp to ms
    so the current React code renders correctly.
    """
    try:
        docs: List[Dict[str, Any]] = []
        if token_collection is not None:
            query: Dict[str, Any] = {}
            if honeypot is not None:
                query["honeypot"] = bool(honeypot)
            if min_liquidity is not None:
                query["liquidity_eth"] = {"$gte": float(min_liquidity)}
            if ownership is not None:
                query["ownership_renounced"] = bool(ownership)
            if start_ms is not None or end_ms is not None:
                query["timestamp"] = {}
                if start_ms is not None:
                    query["timestamp"]["$gte"] = int(start_ms // 1000)
                if end_ms is not None:
                    query["timestamp"]["$lte"] = int(end_ms // 1000)
            if q:
                regex = {"$regex": q, "$options": "i"}
                query["$or"] = [
                    {"address": regex},
                    {"token0_info.address": regex},
                    {"token1_info.address": regex},
                    {"token0_info.name": regex},
                    {"token1_info.name": regex},
                    {"token0_info.symbol": regex},
                    {"token1_info.symbol": regex},
                ]

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
            docs = list(token_collection.find(query, fields).sort("timestamp", -1).limit(limit))
        else:
            # in-memory fallback
            for e in token_events:
                if honeypot is not None and bool(e.get("honeypot", False)) != bool(honeypot):
                    continue
                if min_liquidity is not None and float(e.get("liquidity_eth", 0.0)) < float(min_liquidity):
                    continue
                if ownership is not None and bool(e.get("ownership_renounced", False)) != bool(ownership):
                    continue
                if start_ms is not None and int(e.get("timestamp", 0)) * 1000 < start_ms:
                    continue
                if end_ms is not None and int(e.get("timestamp", 0)) * 1000 > end_ms:
                    continue
                if q:
                    ql = q.lower()
                    found = False
                    for val in [
                        str(e.get("address", "")),
                        str((e.get("token0_info") or {}).get("address", "")),
                        str((e.get("token1_info") or {}).get("address", "")),
                        str((e.get("token0_info") or {}).get("name", "")),
                        str((e.get("token1_info") or {}).get("name", "")),
                        str((e.get("token0_info") or {}).get("symbol", "")),
                        str((e.get("token1_info") or {}).get("symbol", "")),
                    ]:
                        if ql in val.lower():
                            found = True
                            break
                    if not found:
                        continue
                docs.append(e)
            docs = sorted(docs, key=lambda x: int(x.get("timestamp", 0)), reverse=True)[:limit]

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



@app.get("/api/token/{address}")
def get_token_detail(address: str):
    """Return detailed info for a single token address (normalize and return helpful fields)."""
    try:
        addr = address.lower()
        if token_collection is not None:
            doc = token_collection.find_one({"address": {"$regex": f"^{addr}$", "$options": "i"}}, {"_id": 0})
        else:
            doc = next((e for e in token_events if str(e.get("address", "")).lower() == addr), None)

        if not doc:
            raise HTTPException(status_code=404, detail="Token not found")

        # Normalize token0/token1
        t0 = doc.get("token0_info") or doc.get("token0") or {}
        t1 = doc.get("token1_info") or doc.get("token1") or {}

        return {
            "timestamp": int(doc.get("timestamp", 0)) * 1000,
            "address": str(doc.get("address", "")),
            "pair_address": str(doc.get("pair_address", "")),
            "liquidity_eth": float(doc.get("liquidity_eth", 0.0)),
            "honeypot": bool(doc.get("honeypot", False)),
            "ownership_renounced": bool(doc.get("ownership_renounced", False)),
            "token0": {"name": str(t0.get("name", "")), "symbol": str(t0.get("symbol", "")), "address": str(t0.get("address", ""))},
            "token1": {"name": str(t1.get("name", "")), "symbol": str(t1.get("symbol", "")), "address": str(t1.get("address", ""))},
            "raw": doc,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"/api/token/{address} failed: {e}")
