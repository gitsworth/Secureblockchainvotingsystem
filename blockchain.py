import datetime as dt
import hashlib
import json
import streamlit as st # Used for displaying toast and error messages

class Block:
    """Represents a single block in the blockchain ledger."""
    def __init__(self, index, timestamp, data, previous_hash=''):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        """Calculates the SHA-256 hash of the block's content."""
        block_string = str(self.index) + str(self.timestamp) + str(self.data) + str(self.previous_hash) + str(self.nonce)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty):
        """Mines the block by finding a hash that meets the difficulty requirement."""
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
        # st.toast(f"Block {self.index} Mined!")

class Blockchain:
    """Manages the chain of blocks."""
    def __init__(self):
        self.chain = []
        self.difficulty = 2 # Mining difficulty (e.g., hash must start with '00')
        self.pending_votes = []
        self.create_genesis_block()
        self.is_voting_active = False

    def create_genesis_block(self):
        """Creates the first block in the chain."""
        self.chain.append(Block(0, dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Genesis Block", "0"))

    def get_latest_block(self):
        """Returns the last block in the chain."""
        return self.chain[-1]

    def add_vote(self, vote_data, candidates):
        """Adds a vote to the pending list and triggers mining."""
        if not self.is_voting_active:
            st.error("Voting is not currently active. The Host must start the election.")
            return False

        if not self.validate_vote_data(vote_data, candidates):
            return False

        # Add vote to pending list
        self.pending_votes.append(vote_data)
        st.success("Vote recorded successfully! Mining block...")
        self.mine_pending_votes()
        return True

    def mine_pending_votes(self):
        """Mines a new block containing all pending votes."""
        if not self.pending_votes:
            return

        index = len(self.chain)
        timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {"votes": self.pending_votes, "miner": "AutoMiner"}
        previous_hash = self.get_latest_block().hash

        new_block = Block(index, timestamp, data, previous_hash)
        new_block.mine_block(self.difficulty)

        self.chain.append(new_block)
        self.pending_votes = [] # Clear pending votes after mining

    def validate_vote_data(self, vote_data, candidates):
        """Checks for double voting and valid candidate."""
        voter_pub_key = vote_data['public_key']
        candidate_id = vote_data['candidate_id']

        # 1. Check if voter already voted (iterate through the entire chain)
        for block in self.chain:
            if block.data and 'votes' in block.data:
                for vote in block.data['votes']:
                    if vote.get('public_key') == voter_pub_key:
                        st.error("Operation Invalid: **Double Vote Detected!** Your Public Key is already recorded in the Blockchain.")
                        return False

        # 2. Check if the candidate exists
        if candidate_id not in [c.id for c in candidates]:
            st.error(f"Operation Invalid: Candidate ID '{candidate_id}' does not exist.")
            return False

        return True

    def get_vote_counts(self, candidates):
        """Tallies votes from the entire chain."""
        counts = {c.id: 0 for c in candidates}
        total_votes = 0
        for block in self.chain:
            if block.data and 'votes' in block.data:
                for vote in block.data['votes']:
                    candidate_id = vote.get('candidate_id')
                    if candidate_id in counts:
                        counts[candidate_id] += 1
                        total_votes += 1
        return counts, total_votes
