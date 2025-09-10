#!/usr/bin/env python3
"""
Test WalletTracker using the actual implementation but with a fake 'web3' module injected
so we don't need the real web3 package installed. This imports Core.wallet_tracker and
calls handle_event to produce a watchlog entry.
"""
import os
import sys
import types
import json


proj_root = os.getcwd()
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

# Inject a fake 'web3' module so "from web3 import Web3" in Core.wallet_tracker doesn't fail.
fake_web3 = types.ModuleType('web3')
class FakeWeb3:
    def __init__(self):
        pass
    def from_wei(self, value, unit):
        if unit == 'ether':
            return value / 1e18
        return value
fake_web3.Web3 = FakeWeb3
sys.modules['web3'] = fake_web3

# Now import the real WalletTracker implementation
from Core.wallet_tracker import WalletTracker

if __name__ == '__main__':
    os.makedirs('logs', exist_ok=True)

    watch_addr = '0x' + 'aa' * 20
    dummy_web3 = FakeWeb3()

    wt = WalletTracker(dummy_web3, tracked_tokens=set(), watchlist=[watch_addr])

    event = {
        'args': {
            'from': watch_addr,
            'to': '0x' + 'bb' * 20,
            'value': 2500000000000000000,  # 2.5 tokens (wei-like)
        },
        'transactionHash': bytes.fromhex('22' * 32),
    }
    token_addr = '0x' + '02' * 20

    wt.handle_event(event, token_addr)

    print('\n--- watchlog.jsonl contents ---')
    with open('logs/watchlog.jsonl', 'r') as f:
        print(f.read())
