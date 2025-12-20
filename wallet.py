import hashlib
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from ecdsa.util import sigencode_der, sigdecode_der
import binascii

# --- KEY GENERATION ---

def generate_key_pair():
    """Generates a new ECC (ECDSA) Private Key and derives the Public Key."""
    # Use SECP256k1 curve (same as Bitcoin) for strong security
    sk = SigningKey.generate(curve=SECP256k1)
    
    # Private Key: raw hex string
    private_key = sk.to_string().hex()
    
    # Public Key: raw hex string
    public_key = sk.get_verifying_key().to_string().hex()
    
    return private_key, public_key

# --- SIGNING AND VERIFICATION ---

def sign_transaction(private_key, data_to_sign):
    """Signs a piece of data (e.g., a vote transaction) using a Private Key."""
    try:
        sk = SigningKey.from_string(bytes.fromhex(private_key), curve=SECP256k1)
        
        # Hash the data before signing
        hash_of_data = hashlib.sha256(data_to_sign.encode()).digest()
        
        # Sign the hash
        signature = sk.sign_digest(hash_of_data, sigencode=sigencode_der)
        return signature.hex()
        
    except Exception as e:
        print(f"Error signing transaction: {e}")
        return None

def verify_signature(public_key, data_to_verify, signature):
    """Verifies a signature against the original data and a Public Key."""
    try:
        vk = VerifyingKey.from_string(bytes.fromhex(public_key), curve=SECP256k1)
        
        # Hash the data again
        hash_of_data = hashlib.sha256(data_to_verify.encode()).digest()
        
        # Verify the signature
        return vk.verify_digest(
            bytes.fromhex(signature), 
            hash_of_data, 
            sigdecode=sigdecode_der
        )
        
    except Exception as e:
        print(f"Error during signature verification: {e}")
        return False
