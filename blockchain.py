import hashlib
import json
import time
import os
from datetime import datetime
from wallet import verify_signature, sign_transaction 

# --- BLOCK CLASS ---
class Block:
    """Represents a single block in the blockchain."""
    def __init__(self, index, timestamp, previous_hash, transactions, host_public_key, host_signature=None, host_private_key=None, proof=0):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.proof = proof
        self.host_public_key = host_public_key
        self.host_signature = host_signature
        
        # If private key is provided (only for host authority creating new block), sign the block
        if host_private_key:
            self.hash = self.calculate_hash()
            self.host_signature = self.sign_block(host_private_key)
        else:
            self.hash = self.calculate_hash()

    def calculate_hash(self):
        """Creates a SHA256 hash of the block's contents."""
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': self.transactions,
            'previous_hash': self.previous_hash,
            'proof': self.proof,
            'host_public_key': self.host_public_key 
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def sign_block(self, host_private_key):
        """Signs the block's hash using the Host's Private Key (Proof-of-Authority)."""
        if not host_private_key:
            return None
        return sign_transaction(host_private_key, self.hash)

    def verify_signature(self):
        """Verifies the block's signature against the stored Host Public Key."""
        if not self.host_signature:
            return False
        return verify_signature(self.host_public_key, self.hash, self.host_signature)
            
    def to_dict(self):
        """Converts the block object to a dictionary for JSON serialization."""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash,
            'transactions': self.transactions,
            'host_signature': self.host_signature,
            'host_public_key': self.host_public_key,
            'hash': self.hash,
            'proof': self.proof
        }

    @classmethod
    def from_dict(cls, data):
        """Creates a Block object from a dictionary."""
        block = cls(
            index=data['index'],
            timestamp=data['timestamp'],
            previous_hash=data['previous_hash'],
            transactions=data['transactions'],
            host_public_key=data['host_public_key'],
            host_signature=data.get('host_signature'),
            host_private_key=None, 
            proof=data.get('proof', 0)
        )
        block.hash = data['hash']
        return block

# --- BLOCKCHAIN CLASS ---
class Blockchain:
    """Manages the chain, adding new blocks and verifying integrity."""
    def __init__(self, host_public_key, host_private_key, filename):
        self.host_public_key = host_public_key
        self.host_private_key = host_private_key
        self.filename = filename
        self.chain = []
        self.pending_transactions = []
        
        if os.path.exists(self.filename) and os.path.getsize(self.filename) > 0:
            self.load_chain()
        
        if not self.chain:
            self.create_genesis_block()

    @property
    def last_block(self):
        """Returns the last block in the chain."""
        return self.chain[-1]

    def create_genesis_block(self):
        """Creates the first block in the chain."""
        genesis = Block(
            index=0,
            timestamp=time.time(),
            previous_hash="0",
            transactions=[{"message": "Genesis Block - Blockchain Initialized"}],
            host_public_key=self.host_public_key,
            host_private_key=self.host_private_key
        )
        self.chain.append(genesis)
        self.save_chain()

    def new_transaction(self, voter_id, candidate, message):
        """Adds a new vote transaction to the list of pending transactions."""
        self.pending_transactions.append({
            'voter_id': voter_id,
            'candidate': candidate,
            'message': message,
            'timestamp': time.time()
        })

    def new_block(self, proof=0):
        """Mines a new block by taking pending transactions and signing it."""
        block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            previous_hash=self.last_block.hash,
            transactions=self.pending_transactions,
            host_public_key=self.host_public_key,
            host_private_key=self.host_private_key,
            proof=proof
        )
        
        self.pending_transactions = []
        self.chain.append(block)
        self.save_chain()
        return block

    def is_valid(self):
        """Validates the entire chain."""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            if current_block.hash != current_block.calculate_hash():
                return False

            if current_block.previous_hash != previous_block.hash:
                return False
                
            if not current_block.verify_signature():
                return False

        return True

    def save_chain(self):
        """Saves the blockchain to a JSON file."""
        chain_data = [block.to_dict() for block in self.chain]
        with open(self.filename, 'w') as f:
            json.dump(chain_data, f, indent=4)
            
    def load_chain(self):
        """Loads the blockchain from a JSON file."""
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
                self.chain = [Block.from_dict(d) for d in data]
        except (FileNotFoundError, json.JSONDecodeError):
            self.chain = []
    
    def reset_chain(self):
        """Resets the blockchain."""
        if os.path.exists(self.filename):
            os.remove(self.filename)
        self.chain = []
        self.pending_transactions = []
        self.create_genesis_block()
