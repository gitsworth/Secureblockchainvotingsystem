import streamlit as st
import datetime as dt
import hashlib
import json
import pandas as pd
import secrets
from datetime import date
from io import StringIO

# --- Configuration and Constants ---
MAX_CANDIDATES = 10
MAX_VOTERS = 100
ADMIN_PASSWORD = "host123" # Simple admin password for demo purposes

# --- Core Blockchain and Data Classes ---

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

    def add_vote(self, vote_data):
        """Adds a vote to the pending list and triggers mining."""
        if not self.is_voting_active:
            st.error("Voting is not currently active. The Host must start the election.")
            return False

        if not self.validate_vote_data(vote_data):
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

    def validate_vote_data(self, vote_data):
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
        if candidate_id not in [c.id for c in st.session_state.candidates]:
            st.error(f"Operation Invalid: Candidate ID '{candidate_id}' does not exist.")
            return False

        return True

    def get_vote_counts(self):
        """Tallies votes from the entire chain."""
        counts = {c.id: 0 for c in st.session_state.candidates}
        total_votes = 0
        for block in self.chain:
            if block.data and 'votes' in block.data:
                for vote in block.data['votes']:
                    candidate_id = vote.get('candidate_id')
                    if candidate_id in counts:
                        counts[candidate_id] += 1
                        total_votes += 1
        return counts, total_votes

class Voter:
    """Represents a registered voter."""
    def __init__(self, name, dob):
        self.name = name
        self.dob = dob
        # Simple, non-cryptographic key generation for demonstration ease in Streamlit
        self.private_key = secrets.token_hex(16)
        self.public_key = hashlib.sha256(self.private_key.encode()).hexdigest()
        self.has_voted = False

class Candidate:
    """Represents an election candidate."""
    def __init__(self, name, party, id):
        self.name = name
        self.party = party
        self.id = id

# --- State Initialization ---

def init_session_state():
    """Initializes all necessary session state variables."""
    if 'blockchain' not in st.session_state:
        st.session_state.blockchain = Blockchain()
        st.session_state.blockchain.is_voting_active = False # Start in inactive state
    if 'voters' not in st.session_state:
        st.session_state.voters = []
    if 'candidates' not in st.session_state:
        st.session_state.candidates = []
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'admin_login_success' not in st.session_state:
        st.session_state.admin_login_success = False
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "Voter: Registration"

    # Pre-populate for demonstration
    if not st.session_state.voters:
        st.session_state.voters.append(Voter("Alice Smith", "1985-05-15"))
    if not st.session_state.candidates:
        st.session_state.candidates.append(Candidate("John Doe", "Progressive", 1))
        st.session_state.candidates.append(Candidate("Jane Ray", "Conservative", 2))

# --- Tab View Functions ---

def host_login_tab():
    """Handles Host (Admin) authentication."""
    st.title("Host Portal Access")
    if st.session_state.admin_login_success:
        st.success("Access Granted. Use the sidebar to navigate Host tabs.")
        return

    password = st.text_input("Enter Host Password:", type="password")
    if st.button("Login"):
        if password == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.session_state.admin_login_success = True
            st.success("Login successful! Welcome, Host.")
            st.experimental_rerun()
        else:
            st.error("Invalid Host Password. Access denied.")

def host_management_tab():
    """Host: Management (Start/End Vote, Candidates CRUD)."""
    st.title("Host: Election Management")

    # --- Vote Status Control ---
    st.header("1. Election Status Control")
    is_active = st.session_state.blockchain.is_voting_active
    status_text = "🟢 ACTIVE" if is_active else "🔴 INACTIVE"
    st.markdown(f"**Current Voting Status:** **{status_text}**")

    col1, col2 = st.columns(2)

    with col1:
        if not is_active:
            if st.button("▶️ Start Voting"):
                st.session_state.blockchain.is_voting_active = True
                st.success("Voting has been **STARTED**. Voters can now cast their ballots.")
                st.experimental_rerun()
        else:
            st.button("Start Voting", disabled=True, help="Voting is already active.")

    with col2:
        if is_active:
            if st.button("🛑 End Voting"):
                st.session_state.blockchain.is_voting_active = False
                st.info("Voting has been **ENDED**. Results can now be calculated and viewed.")
                st.experimental_rerun()
        else:
            st.button("End Voting", disabled=True, help="Voting is currently inactive.")

    # --- Candidate Management ---
    st.header("2. Candidate Management")
    if is_active:
        st.warning("Restriction: **Candidates cannot be modified while voting is active.** Please end the election first.")
    
    current_candidates = st.session_state.candidates
    can_modify = not is_active

    # Add Candidate
    st.subheader("Add New Candidate")
    if len(current_candidates) >= MAX_CANDIDATES:
        st.error(f"Restriction: Maximum candidate limit of {MAX_CANDIDATES} reached.")
    
    with st.form("add_candidate_form", clear_on_submit=True):
        new_name = st.text_input("Name", disabled=not can_modify)
        new_party = st.text_input("Party/Affiliation", disabled=not can_modify)
        
        submitted = st.form_submit_button("Add Candidate", disabled=not can_modify or len(current_candidates) >= MAX_CANDIDATES)
        
        if submitted and can_modify and len(current_candidates) < MAX_CANDIDATES:
            if not new_name or not new_party:
                 st.error("Operation Invalid: Candidate Name and Party are required.")
            else:
                new_id = len(current_candidates) + 1
                st.session_state.candidates.append(Candidate(new_name, new_party, new_id))
                st.success(f"Candidate {new_name} added with ID {new_id}.")

    # Current Candidates List and Deletion
    st.subheader("Current Candidates (Max 10)")
    if current_candidates:
        df_candidates = pd.DataFrame([
            {"ID": c.id, "Name": c.name, "Party": c.party} for c in current_candidates
        ])
        st.dataframe(df_candidates, hide_index=True)

        # Delete Candidate
        candidate_to_delete = st.selectbox(
            "Select Candidate ID to Remove",
            options=[""] + [c.id for c in current_candidates],
            disabled=not can_modify
        )
        if st.button("Remove Selected Candidate", disabled=not can_modify or not candidate_to_delete):
            st.session_state.candidates = [c for c in current_candidates if c.id != candidate_to_delete]
            # Re-index remaining candidates for clean IDs (optional, but good practice)
            for i, c in enumerate(st.session_state.candidates):
                c.id = i + 1
            st.success(f"Candidate ID {candidate_to_delete} removed. Remaining candidates re-indexed.")
            st.experimental_rerun()
    else:
        st.info("No candidates registered yet.")

def host_voter_database_tab():
    """Host: Voter Database (View voters, remove voters, MAX 100)."""
    st.title("Host: Voter Database (Max 100)")
    st.subheader(f"Registered Voters: {len(st.session_state.voters)} / {MAX_VOTERS}")

    voters_data = []
    for v in st.session_state.voters:
        voters_data.append({
            "Name": v.name,
            "DOB": v.dob,
            "Public Key": v.public_key,
            "Voted": "Yes" if v.has_voted else "No"
        })

    if voters_data:
        df_voters = pd.DataFrame(voters_data)
        st.dataframe(df_voters, hide_index=True)

        # Remove Voter
        st.subheader("Remove Registered Voter")
        voter_to_remove_name = st.selectbox(
            "Select Voter Name to Remove",
            options=[""] + [v.name for v in st.session_state.voters]
        )
        if st.button("Remove Voter"):
            if voter_to_remove_name:
                st.session_state.voters = [v for v in st.session_state.voters if v.name != voter_to_remove_name]
                st.success(f"Voter '{voter_to_remove_name}' successfully removed.")
                st.experimental_rerun()
            else:
                st.error("Please select a voter to remove.")
    else:
        st.info("No voters are currently registered.")

def host_private_keys_tab():
    """Host: Private Keys (Demo) (Shows private keys, cannot remove voters)."""
    st.title("Host: Private Keys (Demonstration)")
    st.warning("🚨 This tab contains sensitive private keys for demonstration purposes. In a real system, these would be securely stored or managed by the voter.")
    
    voters_data = []
    for v in st.session_state.voters:
        voters_data.append({
            "Name": v.name,
            "DOB": v.dob,
            "Public Key": v.public_key,
            "Private Key (Demo)": v.private_key # Private key included here
        })

    if voters_data:
        df_voters = pd.DataFrame(voters_data)
        st.dataframe(df_voters, hide_index=True)

        st.info("Restriction Note: You cannot remove candidates or voters from this specific view. Use the 'Voter Database' tab for voter removal.")
    else:
        st.info("No voters are currently registered.")

def registration_tab():
    """Voter: Registration (Age check, uniqueness, key generation)."""
    st.title("Voter: Registration")

    if len(st.session_state.voters) >= MAX_VOTERS:
        st.error(f"Registration Closed: Maximum voter capacity of {MAX_VOTERS} has been reached.")
        return

    with st.form("registration_form", clear_on_submit=True):
        name = st.text_input("Full Name (Case Insensitive)", max_chars=100).strip()
        dob = st.date_input("Date of Birth", min_value=date(1900, 1, 1), max_value=date.today(), value=date(2000, 1, 1))

        submitted = st.form_submit_button("Register")

        if submitted:
            # 1. Check Age (Must be over 18)
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 18:
                st.error("Operation Invalid: **Registration Rejected.** You must be 18 years or older to register.")
                return

            # 2. Check Uniqueness (Name and DOB must be unique)
            is_duplicate = any(
                (v.name.lower() == name.lower() and v.dob == dob.strftime("%Y-%m-%d"))
                for v in st.session_state.voters
            )
            if is_duplicate:
                st.error("Operation Invalid: **Registration Rejected.** A voter with this exact Name and Date of Birth already exists.")
                return

            # 3. Registration Success
            new_voter = Voter(name, dob.strftime("%Y-%m-%d"))
            st.session_state.voters.append(new_voter)
            st.success("Registration Successful! Your unique keys are displayed below. **Please copy them securely to vote.**")
            
            st.markdown("---")
            st.subheader("Your Generated Keys")
            st.code(f"PUBLIC KEY: {new_voter.public_key}", language='markdown')
            st.code(f"PRIVATE KEY: {new_voter.private_key}", language='markdown')
            st.info("Use your Public and Private Keys on the 'Voter: Voting Booth' tab.")

def voting_tab():
    """Voter: Voting Booth (Submit vote, uses keys, no double votes)."""
    st.title("Voter: Voting Booth")

    if not st.session_state.blockchain.is_voting_active:
        st.warning("Voting is currently **INACTIVE**. Please check back when the Host starts the election.")
        return

    if not st.session_state.candidates:
        st.error("No candidates have been registered by the Host yet.")
        return

    st.header("1. Enter Your Credentials")
    
    voter_pub_key = st.text_input("Your Public Key")
    voter_priv_key = st.text_input("Your Private Key", type="password")

    st.header("2. Cast Your Ballot")
    
    candidate_options = {c.name: c.id for c in st.session_state.candidates}
    selected_name = st.radio(
        "Select the Candidate you wish to vote for:",
        options=list(candidate_options.keys()),
        index=0
    )
    selected_id = candidate_options.get(selected_name)

    if st.button("Submit Vote"):
        # 1. Key Validation (Simple check against registered voters)
        valid_voter = None
        for v in st.session_state.voters:
            if v.public_key == voter_pub_key and v.private_key == voter_priv_key:
                valid_voter = v
                break

        if not valid_voter:
            st.error("Operation Invalid: **Invalid Credentials.** Public or Private Key is incorrect or not registered.")
            return

        # 2. Double Vote Check is handled by the Blockchain's add_vote method (Chain traversal)

        vote_data = {
            "public_key": voter_pub_key,
            "candidate_id": selected_id,
            "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        if st.session_state.blockchain.add_vote(vote_data):
            # If successful, mark voter as having voted (for UI/DB view convenience)
            valid_voter.has_voted = True
            st.balloons()
            st.info("Vote successfully submitted and mined into the Blockchain!")

def results_tab():
    """Public: Results (Bar graph and tally table, only shows after voting ends)."""
    st.title("Election Results")
    
    if st.session_state.blockchain.is_voting_active:
        st.warning("Restriction: **Results are confidential and cannot be viewed while voting is active.** Please wait for the Host to end the election.")
        return

    if not st.session_state.candidates:
        st.info("No candidates available to display results.")
        return
    
    counts, total_votes = st.session_state.blockchain.get_vote_counts()
    
    st.header(f"Final Tally: {total_votes} Total Votes")
    if total_votes == 0:
        st.info("No votes have been cast in this election.")
        return

    candidate_names = {c.id: c.name for c in st.session_state.candidates}
    
    # Prepare data for display
    results_list = []
    for c_id, count in counts.items():
        percent = (count / total_votes) * 100 if total_votes > 0 else 0
        results_list.append({
            "Candidate": candidate_names.get(c_id, f"Unknown ID {c_id}"),
            "Votes": count,
            "Percentage": f"{percent:.2f}%"
        })

    df_results = pd.DataFrame(results_list).sort_values(by="Votes", ascending=False)
    
    # Tally Table
    st.subheader("Tally Table")
    st.dataframe(df_results, hide_index=True)

    # Bar Graph
    st.subheader("Results Bar Graph")
    chart_data = df_results.set_index('Candidate')['Votes']
    st.bar_chart(chart_data)

def blockchain_tab():
    """Public: Blockchain Ledger (Updates as new votes are added/mined)."""
    st.title("Blockchain Ledger")
    st.info("The ledger is displayed below. New blocks are automatically mined upon vote submission, ensuring transparency.")

    chain_data = []
    for block in st.session_state.blockchain.chain:
        chain_data.append({
            "Index": block.index,
            "Timestamp": block.timestamp,
            "Previous Hash": block.previous_hash[:10] + "...",
            "Hash": block.hash[:10] + "...",
            "Nonce": block.nonce,
            "Data (Votes)": json.dumps(block.data)
        })

    df_chain = pd.DataFrame(chain_data)
    st.dataframe(df_chain, hide_index=True)

    st.header("Inspect Blocks")
    
    block_index = st.number_input(
        "Enter Block Index to View Full Details:",
        min_value=0, 
        max_value=len(st.session_state.blockchain.chain) - 1, 
        value=0
    )
    
    if block_index is not None and 0 <= block_index < len(st.session_state.blockchain.chain):
        block = st.session_state.blockchain.chain[block_index]
        st.json({
            "Index": block.index,
            "Timestamp": block.timestamp,
            "Previous Hash": block.previous_hash,
            "Hash": block.hash,
            "Nonce": block.nonce,
            "Data": block.data
        })

# --- Main Application Logic ---

def main():
    """The main function to run the Streamlit application."""
    st.set_page_config(layout="wide", page_title="Decentralized Voting App")
    init_session_state()

    # --- Sidebar Navigation ---
    st.sidebar.title("Navigation")
    
    host_tabs = [
        "Host: Management", 
        "Host: Voter Database", 
        "Host: Private Keys (Demo)"
    ]
    
    public_tabs = [
        "Voter: Registration", 
        "Voter: Voting Booth", 
        "Public: Results", 
        "Public: Blockchain Ledger"
    ]

    # --- Host Portal Section ---
    st.sidebar.subheader("Host Portal")
    if not st.session_state.admin_login_success:
        st.session_state.active_tab = "Host: Login"
    
    # Always show Host Login button unless successful
    if not st.session_state.admin_login_success:
        if st.sidebar.button("Host Login"):
            st.session_state.active_tab = "Host: Login"
    else:
        # If logged in, show host-only tabs
        selected_host_tab = st.sidebar.selectbox(
            "Admin Views",
            options=host_tabs,
            index=host_tabs.index(st.session_state.active_tab) if st.session_state.active_tab in host_tabs else 0,
            key='host_tab_select'
        )
        st.session_state.active_tab = selected_host_tab
        if st.sidebar.button("Logout"):
            st.session_state.admin_login_success = False
            st.session_state.is_admin = False
            st.session_state.active_tab = "Voter: Registration"
            st.experimental_rerun()

    # --- Voter/Public Section ---
    st.sidebar.subheader("Voter & Public Access")
    if st.session_state.admin_login_success and st.session_state.active_tab not in host_tabs:
        # Default to a public tab if admin logged in but hasn't selected an admin tab
        current_public_tab_index = 0
    elif st.session_state.active_tab in public_tabs:
        current_public_tab_index = public_tabs.index(st.session_state.active_tab)
    else:
        current_public_tab_index = 0 # Default to Registration

    selected_public_tab = st.sidebar.selectbox(
        "Public Views",
        options=public_tabs,
        index=current_public_tab_index,
        key='public_tab_select'
    )
    
    # Only update active tab if it's not the Host Login screen
    if st.session_state.active_tab != "Host: Login" or st.session_state.admin_login_success:
        st.session_state.active_tab = selected_public_tab

    # --- Render Selected Tab ---
    st.header(f"Decentralized Voting System")
    st.subheader(f"Current View: {st.session_state.active_tab}")
    st.markdown("---")


    if st.session_state.active_tab == "Host: Login":
        host_login_tab()
    elif st.session_state.active_tab == "Host: Management":
        if st.session_state.is_admin:
            host_management_tab()
        else:
            host_login_tab() # Redirect if direct access attempted
    elif st.session_state.active_tab == "Host: Voter Database":
        if st.session_state.is_admin:
            host_voter_database_tab()
        else:
            host_login_tab()
    elif st.session_state.active_tab == "Host: Private Keys (Demo)":
        if st.session_state.is_admin:
            host_private_keys_tab()
        else:
            host_login_tab()
    elif st.session_state.active_tab == "Voter: Registration":
        registration_tab()
    elif st.session_state.active_tab == "Voter: Voting Booth":
        voting_tab()
    elif st.session_state.active_tab == "Public: Results":
        results_tab()
    elif st.session_state.active_tab == "Public: Blockchain Ledger":
        blockchain_tab()

if __name__ == "__main__":
    main()
