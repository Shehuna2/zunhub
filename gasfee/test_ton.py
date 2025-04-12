from near_api.signer import KeyPair

for att in KeyPair:
    print(att)
keypair = KeyPair.random()
print(f"Private Key: {keypair.private_key}")
print(f"Public Key: {keypair.public_key}")