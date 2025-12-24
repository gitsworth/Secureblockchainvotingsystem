import ecdsa
import base64

def generate_key_pair():
    sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    pk = sk.verifying_key
    return sk.to_string().hex(), pk.to_string().hex()

def sign_transaction(private_key_hex, message):
    try:
        sk = ecdsa.SigningKey.from_string(bytes.fromhex(private_key_hex), curve=ecdsa.SECP256k1)
        return sk.sign(message.encode()).hex()
    except:
        return None

def verify_signature(public_key_hex, message, signature_hex):
    try:
        pk = ecdsa.VerifyingKey.from_string(bytes.fromhex(public_key_hex), curve=ecdsa.SECP256k1)
        return pk.verify(bytes.fromhex(signature_hex), message.encode())
    except:
        return False
