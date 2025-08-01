from Core.token_info import get_token_info
from Core.checks.liquidity import check_liquidity
from Core.checks.honeypot_check import simulate_trade
from Core.checks.ownership_check import is_renounced
import json
import os

with open("resources/config.json") as f:
    config = json.load(f)
    WETH = config["WETH"]
class TokenAnalyzer:
    def __init__(self, web3, token0, token1, pair, router, public_address):
        self.web3 = web3
        self.token0 = token0
        self.token1 = token1
        self.pair = pair
        self.router = router
        self.public_address = public_address

    def is_weth_pair(self):
        return self.token0.lower() == WETH.lower() or self.token1.lower() == WETH.lower()

    def get_target_token(self):
        return self.token0 if self.token1.lower() == WETH.lower() else self.token1

    def analyze(self):
        result = {}

        # Basic token info
        result["token0_info"] = get_token_info(self.web3, self.token0)
        result["token1_info"] = get_token_info(self.web3, self.token1)

        # Determine target token
        target_token = self.get_target_token()

        # Honeypot check
        result["honeypot"] = simulate_trade(
            self.web3, target_token, self.router, WETH, self.public_address
        )

        # Ownership check
        result["ownership_renounced"] = is_renounced(self.web3, target_token)

        # Liquidity check
        result["liquidity_eth"] = check_liquidity(
            self.web3, self.pair, self.token0, self.token1, WETH
        )

        return result
