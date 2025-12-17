import secrets
import hashlib
from datetime import date

# --- Configuration and Constants ---
MAX_CANDIDATES = 10
MAX_VOTERS = 100

class Voter:
    """Represents a registered voter with unique keys."""
    def __init__(self, name, dob):
        self.name = name
        self.dob = dob
        # Simple, non-cryptographic key generation for demonstration ease
        self.private_key = secrets.token_hex(16)
        self.public_key = hashlib.sha256(self.private_key.encode()).hexdigest()
        self.has_voted = False

class Candidate:
    """Represents an election candidate."""
    def __init__(self, name, party, id):
        self.name = name
        self.party = party
        self.id = id
