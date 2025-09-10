import json
from web3 import Web3

ERC20_ABI = json.loads("""
[
  {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},
  {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},
  {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}
]
""")

def get_token_info(web3: Web3, token_address: str):
    token_contract = web3.eth.contract(address=token_address, abi=ERC20_ABI)
    try:
        name = token_contract.functions.name().call()
        symbol = token_contract.functions.symbol().call()
        decimals = token_contract.functions.decimals().call()
        return {
              "address": token_address,
              "name": name,
              "symbol": symbol,
              "decimals": decimals
          }
    except Exception as e:
        print(f"Error fetching token info for {token_address}: {e}")
        return {
            "address": token_address,
            "name": "Unknown",
            "symbol": "UNK",
            "decimals": 18
        }