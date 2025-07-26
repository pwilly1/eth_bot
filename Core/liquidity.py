import json
from pathlib import Path
from web3 import Web3

PAIR_ABI = json.loads("""
[
  {
    "constant": true,
    "inputs": [],
    "name": "getReserves",
    "outputs": [
      { "name": "_reserve0", "type": "uint112" },
      { "name": "_reserve1", "type": "uint112" },
      { "name": "_blockTimestampLast", "type": "uint32" }
    ],
    "type": "function"
  },
  {
    "constant": true,
    "inputs": [],
    "name": "token0",
    "outputs": [{ "name": "", "type": "address" }],
    "type": "function"
  },
  {
    "constant": true,
    "inputs": [],
    "name": "token1",
    "outputs": [{ "name": "", "type": "address" }],
    "type": "function"
  }
]
""")

def check_liquidity(web3, pair_address, token0, token1, weth_address):
    try:
        pair_abi = PAIR_ABI
        pair_contract = web3.eth.contract(address=pair_address, abi=pair_abi)
        reserves = pair_contract.functions.getReserves().call()

        token0_reserve = reserves[0] / (10 ** 18)
        token1_reserve = reserves[1] / (10 ** 18)

        weth_reserve = 0
        if token0.lower() == weth_address.lower():
            weth_reserve = token0_reserve
        elif token1.lower() == weth_address.lower():
            weth_reserve = token1_reserve

        print(f"Token Reserve: {token0_reserve:.4f}")
        print(f"WETH Reserve: {weth_reserve:.4f}")
        return weth_reserve

    except Exception as e:
        print("Error checking liquidity:", e)
        return 0

