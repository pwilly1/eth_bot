import json
import os
import time
import threading
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

# This module exposes runtime state and the blockchain listener.
# FastAPI application and routes are created in `backend.api`.
try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv():
        return None

try:
    from pymongo import MongoClient, ASCENDING
    from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError, PyMongoError
except Exception:
    MongoClient = None
    ASCENDING = None
    DuplicateKeyError = Exception
    ServerSelectionTimeoutError = Exception
    PyMongoError = Exception

try:
    from web3 import Web3
except Exception:
    Web3 = None

# Import heavy Core modules lazily where needed to avoid import-time
# dependency on web3 when tooling imports this module.
from backend.auth import AuthManager
from backend.watchlist import WatchlistManager


# In-memory state
# ---------------------------
token_events: List[Dict[str, Any]] = []
wallet_alerts: List[str] = []
status_messages: List[str] = ["Starting..."]

# Dynamic watchlist and tracker state (populated at startup)
WATCHLIST: List[str] = []
# tokens we are currently tracking (lowercase addresses)
tracked_tokens: set = set()
# reference to the web3 instance used by the blockchain listener (set when listener starts)
web3_instance = None
# keep wallet tracker threads so they stay alive/referencable
wallet_tracker_threads: List[threading.Thread] = []


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


# Mongo init
# ---------------------------
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = db = token_collection = None
watchlist_collection = None
users_collection = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")  # fail fast if unreachable
        db = client["eth_bot_db"]
        token_collection = db["token_events"]
        # watchlist collection for persisted watchlist addresses
        watchlist_collection = db["watchlist"]
        users_collection = db["users"]
        print("Mongo connected")

        # Ensure index (do not crash if it fails)
        ensure_unique_index(token_collection)
        try:
            # Ensure unique index on address for watchlist
            watchlist_collection.create_index([("address", ASCENDING)], unique=True, name="uniq_watchlist_address")
        except Exception as e:
            print(f"Warning: could not ensure watchlist index: {e}")
    except Exception as e:
        msg = f"Mongo connected but index setup hit an issue: {e}"
        print(msg)
        status_messages.append(msg)
        # keep token_collection if connection succeeded                
else:
    print("MONGO_URI not set; running without Mongo")

# load watchlist from disk at startup into the global WATCHLIST
def load_watchlist():
    global WATCHLIST
    try:
        # Prefer DB-backed watchlist when available
        if watchlist_collection is not None:
            # DB-backed global watchlist stored in watchlist_collection
            try:
                docs = list(watchlist_collection.find({}, {"_id": 0, "address": 1}))
                WATCHLIST = [d.get("address", "").lower() for d in docs if d.get("address")]
            except Exception as e:
                print(f"Warning: failed to load watchlist from DB: {e}")
                WATCHLIST = []
        else:
            # Fallback to on-disk watchlist
            with open("resources/watchlist.json", "r") as f:
                data = json.load(f)
                WATCHLIST = [addr.lower() for addr in (data or [])]
    except Exception:
        print("Warning: failed to load watchlist (fallback to empty)")
        WATCHLIST = []

# Now that Mongo (if any) has been initialized, load the watchlist
load_watchlist()

# Initialize managers (use DB collections when available)
auth_manager = AuthManager(users_collection=users_collection, jwt_secret=os.getenv("JWT_SECRET"))
wl_manager = WatchlistManager(watchlist_collection=watchlist_collection, users_collection=users_collection)

# ---------------------------
# Blockchain listener
# ---------------------------
def run_blockchain_listener():
    global token_events, wallet_alerts, status_messages, client, db, token_collection
    print("▶ run_blockchain_listener STARTED", flush=True)
    status_messages.append("Blockchain listener started...")

    global web3_instance, tracked_tokens, WATCHLIST, wallet_tracker_threads
    wss = os.getenv("WEB3_PROVIDER")
    if not wss:
        print("WEB3_PROVIDER not found in .env file.")
        status_messages.append("Error: WEB3_PROVIDER not configured.")
        return

    web3 = Web3(Web3.LegacyWebSocketProvider(wss))
    PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")

    # Load configs/ABIs
    with open("resources/config.json") as f:
        config = json.load(f)
    UNISWAP_FACTORY = config["UNISWAP_FACTORY"]
    PAIR_CREATED_SIGNATURE = config["PAIR_CREATED_SIGNATURE"]

    with open("resources/abis.json") as f:
        PAIR_CREATED_ABI = json.load(f)
    # web3 instance visible to API handlers
    web3_instance = web3
    # expose web3 instance to the rest of the app
    # lazy-import analyzer and wallet tracker implementations so editors/tools
    analyzer_class = None
    wallet_tracker_class = None
    try:
        from backend.Core.analyzer.token_analyzer import TokenAnalyzer as _TokenAnalyzer
        analyzer_class = _TokenAnalyzer
    except Exception as e:
        msg = f"TokenAnalyzer import failed: {e}"
        print(msg)
        status_messages.append(msg)

    try:
        from backend.Core.wallet_tracker import WalletTracker as _WalletTracker
        wallet_tracker_class = _WalletTracker
    except Exception as e:
        msg = f"WalletTracker import failed: {e}"
        print(msg)
        status_messages.append(msg)

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
                    # record globally tracked tokens so new wallet trackers can subscribe
                    tracked_tokens.update(tracked)
                    if wallet_tracker_class is not None:
                        try:
                            wallet_tracker = wallet_tracker_class(web3, tracked, WATCHLIST)
                            wallet_tracker_thread = threading.Thread(target=wallet_tracker.run, daemon=True)
                            wallet_tracker_thread.start()
                            wallet_tracker_threads.append(wallet_tracker_thread)
                        except Exception as e:
                            msg = f"Failed to start WalletTracker: {e}"
                            print(msg)
                            status_messages.append(msg)
                    else:
                        msg = "WalletTracker implementation not available; skipping wallet tracker start."
                        print(msg)
                        status_messages.append(msg)

                if analyzer_class is None:
                    err = "TokenAnalyzer implementation not available; skipping analysis."
                    print(err)
                    status_messages.append(err)
                    result = {}
                else:
                    try:
                        analyzer = analyzer_class(web3, token0, token1, pair, config["UNISWAP_ROUTER"], PUBLIC_ADDRESS)
                        result = analyzer.analyze()
                    except Exception as e:
                        err = f"TokenAnalyzer failed: {e}"
                        print(err)
                        status_messages.append(err)
                        result = {}

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
