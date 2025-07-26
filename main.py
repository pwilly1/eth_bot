from web3 import Web3
from dotenv import load_dotenv
from Core.analyzer.token_analyzer import TokenAnalyzer
from Core.logger import save_token_log
import os
import json
import time

# === Load .env ===
load_dotenv()
wss = os.getenv("WEB3_PROVIDER")
web3 = Web3(Web3.LegacyWebSocketProvider(wss))
UNISWAP_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"  # Uniswap V2
PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")

# === Load config and ABI ===
with open("resources/config.json") as f:
    config = json.load(f)

UNISWAP_FACTORY = config["UNISWAP_FACTORY"]
PAIR_CREATED_SIGNATURE = config["PAIR_CREATED_SIGNATURE"]

with open("resources/abis.json") as f:
    PAIR_CREATED_ABI = json.load(f)

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

            print("\n🇵 New Pair Created!")
            print(f"Pair Address: {pair}")
            print(f"Token0: {token0}")
            print(f"Token1: {token1}")

            analyzer = TokenAnalyzer(web3, token0, token1, pair, UNISWAP_ROUTER, PUBLIC_ADDRESS)
            result = analyzer.analyze()

            print(f"→ Token0: {result['token0_info']}")
            print(f"→ Token1: {result['token1_info']}")
            print(f"Honeypot suspected: {result['honeypot']}")
            print(f"Ownership renounced: {result['ownership_renounced']}")
            print(f"Liquidity (ETH): {result['liquidity_eth']}")

            save_token_log({
                "pair": pair,
                "token0": result['token0_info'],
                "token1": result['token1_info'],
                "honeypot": result['honeypot'],
                "ownership_renounced": result['ownership_renounced'],
                "liquidity_eth": result['liquidity_eth']
            })
        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
