from web3 import Web3

def is_renounced(web3: Web3, token_address: str) -> bool:
    renounced_addresses = [
        "0x0000000000000000000000000000000000000000",
        "0x000000000000000000000000000000000000dEaD"
    ]
    try:
        contract = web3.eth.contract(address=token_address, abi=[{
            "constant": True,
            "inputs": [],
            "name": "owner",
            "outputs": [{"name": "", "type": "address"}],
            "type": "function"
        }])

        owner = contract.functions.owner().call()
        if owner.lower() in renounced_addresses:
            return True
        else:
            print(f" Ownership still active — owner is {owner}")
            return False
    except Exception as e:
        print(f" Could not check ownership for {token_address}: {e}")
        return False  # default to caution
