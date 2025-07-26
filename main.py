from web3 import Web3
from Core.logger import save_token_log
from Core.ownership_check import is_renounced
from Core.liquidity import check_liquidity
from Core.token_info import get_token_info
from Core.honeypot_check import simulate_trade
from dotenv import load_dotenv
import os
import json
import time

# === Load .env ===
load_dotenv()
wss = os.getenv("WEB3_PROVIDER")
web3 = Web3(Web3.LegacyWebSocketProvider(wss))
UNISWAP_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"  # Uniswap V2
PUBLIC_ADDRESS = os.getenv("PUBLIC_ADDRESS")

# === Uniswap Info ===
UNISWAP_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

# === ABI for PairCreated ===
PAIR_CREATED_ABI = json.loads("""
[
  {
    "anonymous": false,
    "inputs": [
      { "indexed": true, "internalType": "address", "name": "token0", "type": "address" },
      { "indexed": true, "internalType": "address", "name": "token1", "type": "address" },
      { "indexed": false, "internalType": "address", "name": "pair", "type": "address" },
      { "indexed": false, "internalType": "uint256", "name": "", "type": "uint256" }
    ],
    "name": "PairCreated",
    "type": "event"
  }
]
""")

# === Contract Setup ===
factory_contract = web3.eth.contract(address=UNISWAP_FACTORY, abi=PAIR_CREATED_ABI)
event_signature = web3.keccak(text="PairCreated(address,address,address,uint256)").hex()
event_filter = web3.eth.filter({
    "address": UNISWAP_FACTORY,
    "topics": [event_signature]
})

# === Watch Loop ===
print(" Watching for new token pairs on Uniswap...")

while True:
    try:
        for log in event_filter.get_new_entries():
            event = factory_contract.events.PairCreated().process_log(log)
            token0 = event["args"]["token0"]
            token1 = event["args"]["token1"]
            pair = event["args"]["pair"]

            print("\n New Pair Created!")
            print(f"Pair Address: {pair}")
            print(f"Token0: {token0}")
            print(f"Token1: {token1}")

            name0, sym0, dec0 = get_token_info(web3, token0)
            name1, sym1, dec1 = get_token_info(web3, token1)

            print(f"→ Token0: {name0} ({sym0}), Decimals: {dec0}")
            print(f"→ Token1: {name1} ({sym1}), Decimals: {dec1}")

            if token0.lower() == WETH.lower() or token1.lower() == WETH.lower():
                print("WETH pair — checking liquidity...")
                liquidity = check_liquidity(web3, pair, token0, token1, WETH)
            else:
                print("Not a WETH pair — ignoring")

            # Check ownership of the **non-WETH** token
            target_token = token0 if token1.lower() == WETH.lower() else token1
            renounced = is_renounced(web3, target_token)
            if renounced:
                print("Ownership is renounced — safer to proceed.")
            else:
                print("Dev still owns contract — caution advised.")

            if not simulate_trade(web3, target_token, UNISWAP_ROUTER, WETH, PUBLIC_ADDRESS):
                print("Token passed honeypot check — looks tradable.")
            else:
                print("Honeypot suspected — skipping token.")

                 # === Perform Checks ===
            honeypot_result = simulate_trade(web3, target_token, UNISWAP_ROUTER, WETH, PUBLIC_ADDRESS)

            # === Log Results ===
            log_entry = {
                "pair_address": pair,
                "token0": {
                    "address": token0,
                    "symbol": sym0,
                    "name": name0,
                    "decimals": dec0,
                },
                "token1": {
                    "address": token1,
                    "symbol": sym1,
                    "name": name1,
                    "decimals": dec1,
                },
                "is_weth_pair": token0.lower() == WETH.lower() or token1.lower() == WETH.lower(),
                "liquidity_eth": float(liquidity),
                "honeypot": honeypot_result,
                "ownership_renounced": renounced
            }

            save_token_log(log_entry)
        time.sleep(1)

           
    except Exception as e:
        print("Error:", e)
        time.sleep(5)
