# wallet_tracker.py (refactored)

import time
from datetime import datetime
import json
from web3 import Web3
from Core.gui.gui_manager import setup_gui, render_gui, update_token_log, update_status

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

class WalletTracker:
    def __init__(self, web3, tracked_tokens, watchlist):
        self.web3 = web3
        self.tracked_tokens = tracked_tokens
        self.watchlist = set(addr.lower() for addr in watchlist)
        self.contracts = {}

    def add_token(self, token_address):
        token = token_address.lower()
        if token not in self.tracked_tokens:
            try:
                contract = self.web3.eth.contract(address=token, abi=ERC20_ABI)
                event_filter = contract.events.Transfer.create_filter(fromBlock="latest")
                self.contracts[token] = event_filter
                self.tracked_tokens.add(token)
                print(f"+ Now tracking token: {token}")
            except Exception as e:
                print(f"Could not track token {token}: {e}")

    def run(self):
        print("Wallet tracker is running...")
        while True:
            for token, event_filter in list(self.contracts.items()):
                try:
                    for event in event_filter.get_new_entries():
                        self.handle_event(event, token)
                except Exception as e:
                    print(f"Error polling {token}: {e}")
            time.sleep(5)

    def handle_event(self, event, token):
        args = event["args"]
        sender = args["from"].lower()
        recipient = args["to"].lower()
        value = self.web3.from_wei(args["value"], "ether")
        tx_hash = event["transactionHash"].hex()

        if sender in self.watchlist or recipient in self.watchlist:
            print(f"{token}: {sender} → {recipient} | {value} tokens")
            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "token": token,
                "tx": tx_hash,
                "from": sender,
                "to": recipient,
                "value": str(value)
            }
            with open("logs/watchlog.jsonl", "a") as f:
                f.write(json.dumps(log_entry) + "\n")
