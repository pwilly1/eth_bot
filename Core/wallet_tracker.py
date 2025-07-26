from web3 import Web3
import json
from pathlib import Path

# Load watchlist of wallets (lowercase for consistency)
WATCHLIST_PATH = Path("watchlist.json")
if WATCHLIST_PATH.exists():
    watchlist = [addr.lower() for addr in json.loads(WATCHLIST_PATH.read_text())]
else:
    watchlist = []
    print(" No watchlist.json found!")

# Minimal ERC-20 ABI with Transfer event
ERC20_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"}
        ],
        "name": "Transfer",
        "type": "event"
    }
]

def watch_transfers(web3, token_address):
    token = web3.eth.contract(address=token_address, abi=ERC20_ABI)
    transfer_event = token.events.Transfer.create_filter(fromBlock='latest')

    print(f"[👁️] Watching transfers for {token_address}...")

    while True:
        try:
            for entry in transfer_event.get_new_entries():
                frm = entry["args"]["from"].lower()
                to = entry["args"]["to"].lower()
                value = entry["args"]["value"]

                if frm in watchlist or to in watchlist:
                    print(f"\nTransfer involving tracked wallet:")
                    print(f"→ From: {frm}")
                    print(f"→ To:   {to}")
                    print(f"→ Value: {web3.fromWei(value, 'ether')} tokens")

        except Exception as e:
            print("Wallet tracker error:", e)

        web3.middleware_onion.sleep(2)  # Basic rate limiting
