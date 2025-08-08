from web3 import Web3
from dotenv import load_dotenv
from Core.analyzer.token_analyzer import TokenAnalyzer
from Core.logger import save_token_log
from Core.wallet_tracker import WalletTracker
from Core.gui.gui_manager import setup_gui, render_gui, update_token_log, update_status, close_gui
import dearpygui.dearpygui as dpg
import os
import json
import time
import threading


def run_blockchain_listener():
    print("▶️ run_blockchain_listener STARTED", flush=True)

    # === Load .env ===
    load_dotenv()
    wss = os.getenv("WEB3_PROVIDER")
    web3 = Web3(Web3.LegacyWebSocketProvider(wss))
    PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")

    # === Load config and ABI ===
    with open("resources/config.json") as f:
        config = json.load(f)

    UNISWAP_ROUTER = config["UNISWAP_ROUTER"]
    UNISWAP_FACTORY = config["UNISWAP_FACTORY"]
    PAIR_CREATED_SIGNATURE = config["PAIR_CREATED_SIGNATURE"]
    WETH = config["WETH"]

    with open("resources/abis.json") as f:
        PAIR_CREATED_ABI = json.load(f)

    with open("resources/watchlist.json") as f:
        WATCHLIST = [addr.lower() for addr in json.load(f)]

    # Token Tracker Set (shared with wallet monitor)
    tracked_tokens = set()

    #setup_gui()
    #threading.Thread(target=render_gui, daemon=True).start()


    # === Contract Setup ===
    factory_contract = web3.eth.contract(address=UNISWAP_FACTORY, abi=PAIR_CREATED_ABI)
    event_signature = web3.keccak(text=PAIR_CREATED_SIGNATURE).hex()
    event_filter = web3.eth.filter({
        "address": UNISWAP_FACTORY,
        "topics": [event_signature]
    })



    # === Watch Loop ===
    print("Watching for new token pairs on Uniswap...")

    while True:
        try:
            for log in event_filter.get_new_entries():
                event = factory_contract.events.PairCreated().process_log(log)
                token0 = event["args"]["token0"]
                token1 = event["args"]["token1"]
                pair = event["args"]["pair"]

                # Deployer Check 
                tx = web3.eth.get_transaction(log["transactionHash"])
                deployer = tx["from"].lower()
                update_token_log(f"📦 New Pair: {token0} + {token1}")
                print("\n🇵 New Pair Created!")
                print(f"Pair Address: {pair}")
                print(f"Deployer: {deployer}")
                # Wallet Tracker Setup 
                if deployer in WATCHLIST:
                    print("⚠️ Deployer is in watchlist!")
                    
                    #  Run wallet tracker on this token pair 
                    tracked = {token0.lower(), token1.lower()}
                    wallet_tracker = WalletTracker(web3, tracked, WATCHLIST)
                    threading.Thread(target=wallet_tracker.run, daemon=True).start()

                # Run Analyzer 
                analyzer = TokenAnalyzer(web3, token0, token1, pair, UNISWAP_ROUTER, PUBLIC_ADDRESS)
                result = analyzer.analyze()

                print(f"→ Token0: {result['token0']}")
                print(f"→ Token1: {result['token1']}")
                update_token_log(f"Honeypot: {result['honeypot']}, Liquidity: {result['liquidity_eth']}")
                print(f"Honeypot suspected: {result['honeypot']}")
                print(f"Ownership renounced: {result['ownership_renounced']}")
                print(f"Liquidity (ETH): {result['liquidity_eth']}")

                # === Add to wallet tracking set ===
                tracked_tokens.add(token0.lower())
                tracked_tokens.add(token1.lower())

            time.sleep(1)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)

if __name__ == "__main__":
    # Build and show the GUI
    setup_gui()

    # blockchain listener in a background thread
    Thread1 = threading.Thread(target=run_blockchain_listener, daemon=True)

    # Update GUI status
    update_status("🟢 Connected & listening…")
    Thread1.start()
    while dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()
        time.sleep(0.01)

    # Only once the window is closed by the user do we destroy context:
    close_gui()
