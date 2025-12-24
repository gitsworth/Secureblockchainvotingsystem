import hashlib
import json
import time
import os

class Block:
    def __init__(self, index, timestamp, previous_hash, transactions, hash=None):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.hash = hash or self.calculate_hash()

    def calculate_hash(self):
        content = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': self.transactions,
            'previous_hash': self.previous_hash
        }, sort_keys=True).encode()
        return hashlib.sha256(content).hexdigest()

    def to_dict(self):
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': self.transactions,
            'previous_hash': self.previous_hash,
            'hash': self.hash
        }

class Blockchain:
    def __init__(self, filename='blockchain_data.json'):
        self.filename = filename
        self.chain = []
        self.pending_transactions = []
        if os.path.exists(self.filename):
            self.load_chain()
        else:
            self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = Block(0, time.time(), "0", [])
        self.chain.append(genesis_block)
        self.save_chain()

    def new_transaction(self, voter_id, candidate):
        # PRIVACY UPGRADE: Masking the voter_id so it cannot be linked back to the CSV easily
        masked_id = hashlib.sha256(voter_id.encode()).hexdigest()
        
        self.pending_transactions.append({
            'masked_voter_id': masked_id,
            'candidate': candidate,
            'timestamp': time.time()
        })

    def mine_block(self):
        if not self.pending_transactions:
            return False
        
        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            previous_hash=self.chain[-1].hash,
            transactions=self.pending_transactions
        )
        self.chain.append(new_block)
        self.pending_transactions = []
        self.save_chain()
        return True

    def save_chain(self):
        with open(self.filename, 'w') as f:
            json.dump([b.to_dict() for b in self.chain], f, indent=4)

    def load_chain(self):
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
                self.chain = [Block(**d) for d in data]
        except:
            self.create_genesis_block()

    def reset_chain(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)
        self.chain = []
        self.pending_transactions = []
        self.create_genesis_block()
