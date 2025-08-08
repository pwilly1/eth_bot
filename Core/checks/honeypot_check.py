from web3 import Web3

def simulate_trade(web3: Web3, token_address: str, router_address: str, weth_address: str, test_wallet: str):
    try:
        
        router_abi = [{
            "name": "getAmountsOut",
            "outputs": [{"name": "", "type": "uint256[]"}],
            "inputs": [
                {"name": "amountIn", "type": "uint256"},
                {"name": "path", "type": "address[]"}
            ],
            "constant": True,
            "payable": False,
            "type": "function"
        }]

        router = web3.eth.contract(address=router_address, abi=router_abi)

        test_amount = Web3.to_wei(0.01, "ether")  # Simulate with 0.01 ETH
        path_buy = [weth_address, token_address]
        path_sell = [token_address, weth_address]

        buy_out = router.functions.getAmountsOut(test_amount, path_buy).call()
        token_amount = buy_out[1]

        sell_out = router.functions.getAmountsOut(token_amount, path_sell).call()
        eth_back = sell_out[1]

        eth_back_ratio = eth_back / test_amount

        print(f"Simulated Buy → Sell Ratio: {eth_back_ratio:.2f}x")

        if eth_back_ratio < 0.4:
            print("Potential honeypot — you lose most ETH on sell.")
            return True
        else:
            return False

    except Exception as e:
        print(f"Honeypot check failed: {e}")
        return True  # default to caution
