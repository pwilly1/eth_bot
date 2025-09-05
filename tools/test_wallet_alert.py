#!/usr/bin/env python3
"""
Simple local test to simulate a Transfer event and trigger WalletTracker's alert handling.
Creates/uses logs/watchlog.jsonl in the repo root.
"""
import os
import json
def from_wei(value, unit):
    if unit == 'ether':
        return value / 1e18
    return value

def handle_event(event, token):
    args = event['args']
    sender = args['from'].lower()
    recipient = args['to'].lower()
    value = from_wei(args['value'], 'ether')
    tx_hash = event['transactionHash'].hex() if isinstance(event['transactionHash'], bytes) else str(event['transactionHash'])

    # For this test, assume the watchlist contains the sender address
    log_entry = {
        'timestamp': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
        'token': token,
        'tx': tx_hash,
        'from': sender,
        'to': recipient,
        'value': str(value)
    }
    os.makedirs('logs', exist_ok=True)
    with open('logs/watchlog.jsonl', 'a') as f:
        f.write(json.dumps(log_entry) + "\n")

if __name__ == '__main__':
    # Simulate an ERC20 Transfer event
    watch_addr = '0x' + 'ab' * 20
    event = {
        'args': {
            'from': watch_addr,
            'to': '0x' + 'cd' * 20,
            'value': 1234567890000000000,
        },
        'transactionHash': bytes.fromhex('11' * 32),
    }
    token_addr = '0x' + '01' * 20
    handle_event(event, token_addr)

    print('\n--- watchlog.jsonl contents ---')
    with open('logs/watchlog.jsonl', 'r') as f:
        print(f.read())
