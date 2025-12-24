import ecdsa
import binascii

def generate_key_pair():
    # Generate SECP256k1 keys (Bitcoin standard)
    sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    pk = sk.get_verifying_key()
    return (
        binascii.hexlify(sk.to_string()).decode(),
        binascii.hexlify(pk.to_string()).decode()
    )

def sign_transaction(private_key_hex, message):
    try:
        sk_bytes = binascii.unhexlify(private_key_hex)
        sk = ecdsa.SigningKey.from_string(sk_bytes, curve=ecdsa.SECP256k1)
        signature = sk.sign(message.encode())
        return binascii.hexlify(signature).decode()
    except:
        return None

def verify_signature(public_key_hex, message, signature_hex):
    try:
        pk_bytes = binascii.unhexlify(public_key_hex)
        sig_bytes = binascii.unhexlify(signature_hex)
        pk = ecdsa.VerifyingKey.from_string(pk_bytes, curve=ecdsa.SECP256k1)
        return pk.verify(sig_bytes, message.encode())
    except:
        return False
