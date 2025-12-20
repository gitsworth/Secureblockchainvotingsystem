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

@st.cache_resource
def initialize_system():
    voters_df_init = load_voters(DB_PATH)
    try:
        bc = Blockchain(HOST_PUBLIC_KEY, HOST_PRIVATE_KEY, BLOCKCHAIN_PATH)
        return voters_df_init, bc
    except Exception as e:
        st.error(f"Error initializing Blockchain: {e}")
        st.stop()

if 'blockchain' not in st.session_state:
    voters_df_init, bc = initialize_system()
    st.session_state.voters_df = voters_df_init
    st.session_state.blockchain = bc
    
blockchain = st.session_state.blockchain

# --- ELECTION STATE MANAGEMENT ---
if 'registration_open' not in st.session_state:
    st.session_state.registration_open = True
if 'voting_open' not in st.session_state:
    st.session_state.voting_open = False
if 'election_ended' not in st.session_state:
    st.session_state.election_ended = False
if 'candidates' not in st.session_state:
    st.session_state.candidates = ["Candidate A", "Candidate B"]

# --- HELPER FUNCTIONS ---
def get_total_votes(candidates):
    results = {name: 0 for name in candidates}
    for block in blockchain.chain[1:]:
        for tx in block.transactions:
            vote_candidate = tx.get('candidate')
            if vote_candidate in results:
                results[vote_candidate] += 1
    return results

def get_voter_info(public_key):
    voters_df = st.session_state.voters_df
    return voters_df[voters_df['public_key'].astype(str) == str(public_key)]

# --- MAIN APP LAYOUT ---
st.set_page_config(layout="wide", page_title="Secure Blockchain Voting System")

st.markdown("""
    <style>
    .big-font { font-size:25px !important; font-weight: bold; color: #1E40AF; }
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 10px; text-align: center; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Secure Blockchain Voting System")

# Create the Tabs
tab_reg, tab_voter, tab_results, tab_host, tab_ledger = st.tabs([
    "📝 Voter Registration",
    "🗳️ Voter Portal", 
    "📊 Election Results",
    "⚙️ Host Portal", 
    "🔗 Blockchain Ledger"
])

# ==============================================================================
# 1. VOTER REGISTRATION
# ==============================================================================
with tab_reg:
    st.markdown("<p class='big-font'>Voter Registration</p>", unsafe_allow_html=True)
    
    if st.session_state.registration_open:
        with st.form("voter_registration_form"):
            new_name = st.text_input("Full Name")
            dob = st.date_input("Date of Birth", min_value=date(1920, 1, 1), max_value=date.today())
            age = st.number_input("Enter Age", min_value=0, max_value=120, step=1)
            
            submitted = st.form_submit_button("Register & Generate Credentials")
            
            if submitted:
                voters_df = st.session_state.voters_df
                # Check duplication: Name + DOB
                duplicate = voters_df[(voters_df['name'].str.lower() == new_name.lower()) & 
                                     (voters_df['dob'] == str(dob))]
                
                if not new_name:
                    st.error("Please enter your name.")
                elif age < 18:
                    st.error("Registration denied: You must be 18 or older to vote.")
                elif not duplicate.empty:
                    st.warning("This person (Name and Date of Birth) is already registered.")
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
                    
                    st.success(f"Successfully Registered, {new_name}!")
                    st.info("⚠️ COPY THESE KEYS NOW. You will need them to vote. They will not be shown again.")
                    st.code(f"Public Key (ID): {public_key}")
                    st.code(f"Private Key (Secret): {private_key}")
    else:
        st.info("Registration is currently closed by the Host.")

# ==============================================================================
# 2. VOTER PORTAL
# ==============================================================================
with tab_voter:
    st.markdown("<p class='big-font'>Cast Your Secure Vote</p>", unsafe_allow_html=True)
    
    if st.session_state.voting_open:
        with st.form("vote_casting"):
            v_name = st.text_input("Registered Name")
            v_id = st.text_input("Public Key (Voter ID)")
            s_key = st.text_input("Private Key (Secret Key)", type="password")
            candidate = st.selectbox("Select Candidate:", st.session_state.candidates)
            
            if st.form_submit_button("Cast Vote Securely"):
                voter_row = get_voter_info(v_id)
                
                if voter_row.empty:
                    st.error("Invalid Voter ID.")
                else:
                    v_info = voter_row.iloc[0]
                    if v_info['name'].lower() != v_name.lower():
                        st.error("Name does not match our records for this ID.")
                    elif v_info['has_voted']:
                        st.warning("This ID has already cast a vote.")
                    elif str(v_info['private_key']) != str(s_key):
                        st.error("Incorrect Private Key.")
                    else:
                        data_to_sign = f"VOTE|{v_id}|{candidate}|{datetime.now().isoformat()}"
                        signature = sign_transaction(s_key, data_to_sign)
                        
                        if signature and verify_signature(v_id, data_to_sign, signature):
                            blockchain.new_transaction(v_id, candidate, "Vote Cast")
                            blockchain.new_block()
                            if update_voter_status(st.session_state.voters_df, v_id):
                                save_voters(st.session_state.voters_df, DB_PATH)
                                st.success(f"Vote cast successfully for {candidate}!")
                                st.rerun()
    else:
        st.warning("Voting is currently closed.")

# ==============================================================================
# 3. ELECTION RESULTS
# ==============================================================================
with tab_results:
    st.markdown("<p class='big-font'>Election Results</p>", unsafe_allow_html=True)
    
    if st.session_state.election_ended:
        results = get_total_votes(st.session_state.candidates)
        total_votes = sum(results.values())
        
        st.success("THE ELECTION HAS CONCLUDED. FINAL RESULTS:")
        st.metric("Total Votes Counted", total_votes)
        
        if total_votes > 0:
            res_df = pd.DataFrame(list(results.items()), columns=['Candidate', 'Votes'])
            st.bar_chart(res_df.set_index('Candidate'))
            st.table(res_df)
        else:
            st.info("No votes were cast in this election.")
    else:
        st.info("🔒 Results are hidden until the election has ended to ensure fairness.")

# ==============================================================================
# 4. HOST PORTAL
# ==============================================================================
with tab_host:
    st.markdown("<p class='big-font'>Host Authority Management</p>", unsafe_allow_html=True)
    
    st.subheader("Manage Candidates")
    if not st.session_state.voting_open and not st.session_state.election_ended:
        can_input = st.text_area("Update Candidate List (One per line)", value="\n".join(st.session_state.candidates))
        if st.button("Save Candidates"):
            new_list = [c.strip() for c in can_input.split('\n') if c.strip()]
            if len(new_list) != len(set(new_list)):
                st.error("Duplicate candidate names are not allowed.")
            elif not new_list:
                st.error("Candidate list cannot be empty.")
            else:
                st.session_state.candidates = new_list
                st.success("Candidate list updated.")
    else:
        st.warning("Candidate list is LOCKED because voting has started/ended.")
        st.write("Current Candidates:", st.session_state.candidates)

    st.markdown("---")
    st.subheader("Election Control")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Start Voting (Close Registration)"):
            st.session_state.registration_open = False
            st.session_state.voting_open = True
            st.rerun()
    with c2:
        if st.button("End Voting (Show Results)"):
            st.session_state.voting_open = False
            st.session_state.election_ended = True
            st.rerun()
    with c3:
        if st.button("Reset System"):
            blockchain.reset_chain()
            st.session_state.voters_df = pd.DataFrame(columns=['id','name','dob','age','public_key','private_key','has_voted','registration_date'])
            save_voters(st.session_state.voters_df, DB_PATH)
            st.session_state.registration_open = True
            st.session_state.voting_open = False
            st.session_state.election_ended = False
            st.rerun()

    st.subheader("Registered Voters Log")
    st.dataframe(st.session_state.voters_df[['name', 'dob', 'age', 'has_voted']])

# ==============================================================================
# 5. LEDGER
# ==============================================================================
with tab_ledger:
    st.markdown("<p class='big-font'>Blockchain Ledger</p>", unsafe_allow_html=True)
    for block in reversed(blockchain.chain):
        with st.expander(f"Block #{block.index} - Hash: {block.hash[:15]}..."):
            st.json(block.to_dict())
