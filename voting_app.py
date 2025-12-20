import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime, date

# --- Module Imports ---
from database import load_voters, save_voters, update_voter_status 
from wallet import generate_key_pair, sign_transaction, verify_signature
from blockchain import Blockchain

# --- HOST KEYS ---
HOST_PUBLIC_KEY = "04f9812f864e29c8e29a99f18731d1020786522c07342921b777a824100c5c7d0d6118d052d9a3028211b777a824100c5c7d0d6118d052d9a3028211b714f3b573e35a11956e300109968412030040682121"
HOST_PRIVATE_KEY = "c8b4b74581f1d19d7e5d263a568c078864d2d4808386375354972e25d25e0c50"

# --- CONFIGURATION ---
DB_PATH = 'voters.csv' 
BLOCKCHAIN_PATH = 'blockchain_data.json'

# --- INITIALIZATION ---
if 'blockchain' not in st.session_state:
    st.session_state.voters_df = load_voters(DB_PATH)
    st.session_state.blockchain = Blockchain(HOST_PUBLIC_KEY, HOST_PRIVATE_KEY, BLOCKCHAIN_PATH)
    
    # Election State
    st.session_state.registration_open = True
    st.session_state.voting_open = False
    st.session_state.election_ended = False
    st.session_state.candidates = ["Candidate A", "Candidate B"]

blockchain = st.session_state.blockchain

# --- HELPER FUNCTIONS ---
def get_total_votes(candidates):
    results = {name: 0 for name in candidates}
    for block in blockchain.chain[1:]:
        for tx in block.transactions:
            vote_candidate = tx.get('candidate')
            if vote_candidate in results:
                results[vote_candidate] += 1
    return results

# --- APP LAYOUT ---
st.set_page_config(layout="wide", page_title="Secure Blockchain Voting System")

st.markdown("""
    <style>
    .header-font { font-size:30px !important; font-weight: bold; color: #1E40AF; border-bottom: 2px solid #60A5FA; }
    .stButton>button { border-radius: 8px; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Secure Blockchain Voting System")

tab_reg, tab_voter, tab_results, tab_host, tab_ledger = st.tabs([
    "📝 Voter Registration", 
    "🗳️ Voter Portal", 
    "📊 Election Results", 
    "⚙️ Host Portal", 
    "🔗 Ledger"
])

# ==============================================================================
# 1. VOTER REGISTRATION
# ==============================================================================
with tab_reg:
    st.markdown("<p class='header-font'>Voter Registration</p>", unsafe_allow_html=True)
    
    if st.session_state.registration_open:
        with st.form("registration_form"):
            new_name = st.text_input("Full Name")
            dob = st.date_input("Date of Birth", min_value=date(1920, 1, 1), max_value=date.today())
            age = st.number_input("Current Age", min_value=0, max_value=120, step=1)
            
            if st.form_submit_button("Register & Generate Wallet"):
                voters_df = st.session_state.voters_df
                # Duplicate Check (Name + DOB)
                is_duplicate = not voters_df[(voters_df['name'].str.lower() == new_name.lower()) & 
                                            (voters_df['dob'] == str(dob))].empty
                
                if not new_name:
                    st.error("Name is required.")
                elif age < 18:
                    st.error("Access Denied: You must be at least 18 years old to register.")
                elif is_duplicate:
                    st.warning("This person is already registered in the system.")
                else:
                    private_key, public_key = generate_key_pair()
                    new_voter = pd.DataFrame([{
                        'id': voters_df['id'].max() + 1 if not voters_df.empty else 1,
                        'name': new_name,
                        'dob': str(dob),
                        'age': age,
                        'public_key': public_key,
                        'private_key': private_key,
                        'has_voted': False,
                        'registration_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    st.session_state.voters_df = pd.concat([voters_df, new_voter], ignore_index=True)
                    save_voters(st.session_state.voters_df, DB_PATH)
                    
                    st.success(f"Successfully registered {new_name}!")
                    st.warning("⚠️ COPY YOUR KEYS NOW. You cannot retrieve them later.")
                    st.code(f"Public Key (Voter ID): {public_key}")
                    st.code(f"Private Key (Secret): {private_key}")
    else:
        st.info("Registration is currently closed.")

# ==============================================================================
# 2. VOTER PORTAL
# ==============================================================================
with tab_voter:
    st.markdown("<p class='header-font'>Voter Portal</p>", unsafe_allow_html=True)
    
    if st.session_state.voting_open:
        with st.form("voting_form"):
            v_name = st.text_input("Registered Full Name")
            v_id = st.text_input("Public Key (Voter ID)")
            v_key = st.text_input("Private Key", type="password")
            candidate = st.selectbox("Choose Candidate", st.session_state.candidates)
            
            if st.form_submit_button("Submit Secure Vote"):
                voters_df = st.session_state.voters_df
                voter_row = voters_df[voters_df['public_key'] == v_id]
                
                if voter_row.empty:
                    st.error("Invalid Voter ID.")
                else:
                    v_info = voter_row.iloc[0]
                    if v_info['name'].lower() != v_name.lower():
                        st.error("Verification failed: Name does not match ID.")
                    elif v_info['has_voted']:
                        st.warning("You have already cast your vote.")
                    elif str(v_info['private_key']) != str(v_key):
                        st.error("Authentication failed: Incorrect Private Key.")
                    else:
                        # Logic to sign and add to blockchain
                        data = f"{v_id}|{candidate}|{time.time()}"
                        signature = sign_transaction(v_key, data)
                        
                        if signature and verify_signature(v_id, data, signature):
                            blockchain.new_transaction(v_id, candidate, "Vote Cast")
                            blockchain.new_block()
                            update_voter_status(st.session_state.voters_df, v_id)
                            save_voters(st.session_state.voters_df, DB_PATH)
                            st.success("Vote recorded successfully on the blockchain!")
                            st.rerun()
    else:
        st.warning("The voting window is currently closed.")

# ==============================================================================
# 3. ELECTION RESULTS
# ==============================================================================
with tab_results:
    st.markdown("<p class='header-font'>Election Results</p>", unsafe_allow_html=True)
    
    if st.session_state.election_ended:
        results = get_total_votes(st.session_state.candidates)
        total = sum(results.values())
        st.success(f"Final Count: {total} votes cast.")
        
        res_df = pd.DataFrame(list(results.items()), columns=['Candidate', 'Votes'])
        st.bar_chart(res_df.set_index('Candidate'))
        st.table(res_df)
    else:
        st.info("🔒 Results are currently hidden. They will be revealed once the Host ends the election.")

# ==============================================================================
# 4. HOST PORTAL
# ==============================================================================
with tab_host:
    st.markdown("<p class='header-font'>Host Authority Management</p>", unsafe_allow_html=True)
    
    # Candidate Setup
    st.subheader("1. Candidate Management")
    if not st.session_state.voting_open and not st.session_state.election_ended:
        c_input = st.text_area("Candidate List (One per line)", value="\n".join(st.session_state.candidates))
        if st.button("Update Candidates"):
            raw_list = [c.strip() for c in c_input.split('\n') if c.strip()]
            if len(raw_list) != len(set(raw_list)):
                st.error("Error: Duplicate candidate names detected.")
            elif not raw_list:
                st.error("Error: Candidate list cannot be empty.")
            else:
                st.session_state.candidates = raw_list
                st.success("Candidate list updated successfully.")
    else:
        st.warning("Candidate management is locked while voting is active or ended.")

    # Election Status
    st.subheader("2. Election Controls")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Start Voting (Closes Registration)"):
            st.session_state.registration_open = False
            st.session_state.voting_open = True
            st.rerun()
    with c2:
        if st.button("End Voting (Reveals Results)"):
            st.session_state.voting_open = False
            st.session_state.election_ended = True
            st.rerun()
    with c3:
        if st.button("Reset Election System"):
            blockchain.reset_chain()
            st.session_state.voters_df = pd.DataFrame(columns=['id','name','dob','age','public_key','private_key','has_voted','registration_date'])
            save_voters(st.session_state.voters_df, DB_PATH)
            st.session_state.registration_open, st.session_state.voting_open, st.session_state.election_ended = True, False, False
            st.rerun()

    # Voter Base Table
    st.subheader("3. Registered Voter Database (Admin View)")
    # Added 'public_key' and 'private_key' to the displayed columns as requested
    st.dataframe(st.session_state.voters_df[['name', 'dob', 'age', 'public_key', 'private_key', 'has_voted']], use_container_width=True)

# ==============================================================================
# 5. BLOCKCHAIN LEDGER
# ==============================================================================
with tab_ledger:
    st.markdown("<p class='header-font'>Blockchain Ledger</p>", unsafe_allow_html=True)
    for block in reversed(blockchain.chain):
        with st.expander(f"Block #{block.index} [Hash: {block.hash[:15]}...]"):
            st.json(block.to_dict())
