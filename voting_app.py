import streamlit as st
import pandas as pd
import time
from datetime import datetime, date
from database import load_voters, save_voters, update_voter_status 
from wallet import generate_key_pair, sign_transaction, verify_signature
from blockchain import Blockchain

# --- CONFIGURATION ---
DB_PATH = 'voters.csv' 
BC_PATH = 'blockchain_data.json'
ADMIN_PASSWORD = "admin123" # Change this for your presentation

# --- STATE INITIALIZATION ---
if 'blockchain' not in st.session_state:
    st.session_state.voters_df = load_voters(DB_PATH)
    st.session_state.blockchain = Blockchain(BC_PATH)
    st.session_state.reg_open = True
    st.session_state.vote_open = False
    st.session_state.ended = False
    st.session_state.candidates = ["Candidate A", "Candidate B"]
    st.session_state.admin_authenticated = False

st.set_page_config(layout="wide", page_title="Secure Blockchain Voting")

# --- UI TABS ---
tab_reg, tab_voter, tab_res, tab_host, tab_ledg = st.tabs([
    "📝 Registration", "🗳️ Vote", "📊 Results", "⚙️ Host", "🔗 Ledger"
])

# --- 1. REGISTRATION (Public Key Hidden from Voter) ---
with tab_reg:
    st.header("Voter Registration")
    if st.session_state.reg_open:
        with st.form("reg_form"):
            name = st.text_input("Full Name")
            dob = st.date_input("Date of Birth", min_value=date(1920,1,1), max_value=date.today())
            
            # Auto-calculate age
            today = date.today()
            calculated_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            st.info(f"Calculated Age: {calculated_age}")
            
            if st.form_submit_button("Register"):
                df = st.session_state.voters_df
                is_dup = not df[(df['name'].str.lower() == name.lower()) & (df['dob'] == str(dob))].empty
                
                if not name: st.error("Name required")
                elif calculated_age < 18: st.error("Must be 18+ to register.")
                elif is_dup: st.warning("User already registered.")
                else:
                    priv_key, pub_key = generate_key_pair()
                    new_voter = pd.DataFrame([{
                        'name': name,
                        'dob': str(dob),
                        'age': calculated_age,
                        'public_key': pub_key,
                        'has_voted': False
                    }])
                    st.session_state.voters_df = pd.concat([df, new_voter], ignore_index=True)
                    save_voters(st.session_state.voters_df, DB_PATH)
                    
                    st.success("Registration Successful!")
                    st.subheader("Your Secret Credentials")
                    st.warning("⚠️ IMPORTANT: Copy your Private Key now. It is your ONLY way to authorize your vote. It is NOT stored in our database.")
                    # Public key is hidden here as requested
                    st.code(f"Private Key (SECRET): {priv_key}", language="text")
                    st.info("To vote later, you only need to provide your Name, DOB, and this Private Key.")
    else:
        st.info("Registration is closed.")

# --- 2. VOTER PORTAL (Lookup via Name/DOB) ---
with tab_voter:
    st.header("Voter Portal")
    if st.session_state.vote_open:
        with st.form("vote_form"):
            v_name = st.text_input("Full Name")
            v_dob = st.date_input("Date of Birth", key="vote_dob")
            v_sk = st.text_input("Private Key (Secret)", type="password")
            candidate = st.selectbox("Select Candidate", st.session_state.candidates)
            
            if st.form_submit_button("Submit Vote"):
                df = st.session_state.voters_df
                # Automatic Public Key Lookup
                match = df[(df['name'].str.lower() == v_name.lower()) & (df['dob'] == str(v_dob))]
                
                if match.empty:
                    st.error("No registered voter found with these details.")
                else:
                    voter_data = match.iloc[0]
                    v_pk = voter_data['public_key']
                    
                    if voter_data['has_voted']:
                        st.warning("You have already voted.")
                    else:
                        # Message used for signing
                        msg = f"{v_pk}-{candidate}"
                        sig = sign_transaction(v_sk, msg)
                        
                        if sig and verify_signature(v_pk, msg, sig):
                            st.session_state.blockchain.new_transaction(v_pk, candidate)
                            st.session_state.blockchain.mine_block()
                            update_voter_status(st.session_state.voters_df, v_pk)
                            save_voters(st.session_state.voters_df, DB_PATH)
                            st.success("Vote Verified and Added to Blockchain!")
                        else:
                            st.error("Invalid Private Key for this identity.")
    else:
        st.warning("Voting is currently closed.")

# --- 3. RESULTS ---
with tab_res:
    st.header("Election Results")
    if st.session_state.ended:
        results = {c: 0 for c in st.session_state.candidates}
        for block in st.session_state.blockchain.chain[1:]:
            for tx in block.transactions:
                cand = tx.get('candidate')
                if cand in results: results[cand] += 1
        
        st.bar_chart(pd.DataFrame(list(results.items()), columns=['Candidate', 'Votes']).set_index('Candidate'))
    else:
        st.info("Results are hidden until the Host ends the election.")

# --- 4. HOST PORTAL (Password Protected) ---
with tab_host:
    st.header("Host Controls")
    
    if not st.session_state.admin_authenticated:
        pwd_input = st.text_input("Enter Admin Password", type="password")
        if st.button("Unlock Host Portal"):
            if pwd_input == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect Password")
    else:
        st.success("Authenticated as Administrator")
        
        c1, c2, c3 = st.columns(3)
        if c1.button("Start Voting"):
            st.session_state.reg_open, st.session_state.vote_open = False, True
            st.rerun()
        if c2.button("End Election"):
            st.session_state.vote_open, st.session_state.ended = False, True
            st.rerun()
        if c3.button("Reset All Data"):
            st.session_state.blockchain.reset_chain()
            st.session_state.voters_df = pd.DataFrame(columns=['name', 'dob', 'age', 'public_key', 'has_voted'])
            save_voters(st.session_state.voters_df, DB_PATH)
            st.session_state.reg_open, st.session_state.vote_open, st.session_state.ended = True, False, False
            st.rerun()

        st.subheader("Candidate Settings")
        if not st.session_state.vote_open and not st.session_state.ended:
            c_text = st.text_area("Candidates (One per line)", "\n".join(st.session_state.candidates))
            if st.button("Save Candidates"):
                st.session_state.candidates = [x.strip() for x in c_text.split("\n") if x.strip()]
                st.success("Updated")

        st.subheader("Voter Audit Log")
        # Admin can see Public Keys (Voter IDs) but NOT Private Keys
        st.dataframe(st.session_state.voters_df[['name', 'dob', 'age', 'public_key', 'has_voted']], use_container_width=True)

# --- 5. LEDGER ---
with tab_ledg:
    for block in reversed(st.session_state.blockchain.chain):
        st.json(block.to_dict())
