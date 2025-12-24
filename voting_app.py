import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
from database import load_voters, save_voters, update_voter_status 
from wallet import generate_key_pair, sign_transaction, verify_signature
from blockchain import Blockchain

# --- CONFIGURATION ---
DB_PATH = 'voters.csv' 
BC_PATH = 'blockchain_data.json'
CONFIG_PATH = 'election_config.json'
ADMIN_PASSWORD = "admin123"

# --- PERSISTENT STATE MANAGEMENT ---
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "reg_open": True,
        "vote_open": False,
        "ended": False,
        "candidates": ["Candidate A", "Candidate B"]
    }

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f)

# Initialize state
config_data = load_config()

if 'blockchain' not in st.session_state:
    st.session_state.voters_df = load_voters(DB_PATH)
    st.session_state.blockchain = Blockchain(BC_PATH)
    st.session_state.admin_authenticated = False

st.set_page_config(layout="wide", page_title="Secure Blockchain Voting")

# --- NAVIGATION LOGIC ---
query_params = st.query_params
current_page = query_params.get("page", "voter")

# --- SHARED FUNCTIONS ---
def show_results():
    st.header("📊 Election Results")
    if config_data["ended"]:
        results_tally = {c: 0 for c in config_data["candidates"]}
        for block in st.session_state.blockchain.chain[1:]:
            for tx in block.transactions:
                cand = tx.get('candidate')
                if cand in results_tally:
                    results_tally[cand] += 1
        
        results_df = pd.DataFrame(list(results_tally.items()), columns=['Candidate', 'Votes'])
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("Vote Count Tally")
            st.table(results_df.set_index('Candidate'))
            st.metric("Total Votes Cast", results_df['Votes'].sum())
        with col2:
            st.subheader("Visual Representation")
            st.bar_chart(results_df.set_index('Candidate'))
    else:
        st.info("Results are hidden until the Host ends the election.")

def show_ledger():
    st.header("🔗 Blockchain Ledger")
    for block in reversed(st.session_state.blockchain.chain):
        st.json(block.to_dict())

# --- PAGE ROUTING ---
if current_page == "host":
    st.title("🛡️ Host Administration Portal")
    tab_host, tab_res, tab_ledg = st.tabs(["⚙️ Controls", "📊 Results", "🔗 Ledger"])
    
    with tab_host:
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
            
            if c1.button("🚀 Start Voting (Close Reg)"):
                config_data["reg_open"] = False
                config_data["vote_open"] = True
                save_config(config_data)
                st.rerun()
                
            if c2.button("🛑 End Election"):
                config_data["vote_open"] = False
                config_data["ended"] = True
                save_config(config_data)
                st.rerun()
                
            if c3.button("♻️ Reset All Data"):
                st.session_state.blockchain.reset_chain()
                st.session_state.voters_df = pd.DataFrame(columns=['name', 'dob', 'age', 'public_key', 'has_voted'])
                save_voters(st.session_state.voters_df, DB_PATH)
                new_config = {"reg_open": True, "vote_open": False, "ended": False, "candidates": ["Candidate A", "Candidate B"]}
                save_config(new_config)
                st.rerun()

            st.subheader("Candidate Settings")
            if not config_data["vote_open"] and not config_data["ended"]:
                c_text = st.text_area("Candidates (One per line)", "\n".join(config_data["candidates"]))
                if st.button("Save Candidates"):
                    config_data["candidates"] = [x.strip() for x in c_text.split("\n") if x.strip()]
                    save_config(config_data)
                    st.success("Candidates Saved!")
            else:
                st.info("Candidates cannot be modified during or after the election.")

            st.subheader("Voter Audit Log")
            st.dataframe(st.session_state.voters_df[['name', 'dob', 'age', 'public_key', 'has_voted']], use_container_width=True)

    with tab_res: show_results()
    with tab_ledg: show_ledger()

else: # Voter Portal
    st.title("🗳️ Public Voter Portal")
    tab_reg, tab_voter, tab_res, tab_ledg = st.tabs(["📝 Registration", "🗳️ Cast Vote", "📊 Results", "🔗 Ledger"])
    
    with tab_reg:
        if config_data["reg_open"]:
            with st.form("reg_form"):
                name = st.text_input("Full Name")
                dob = st.date_input("Date of Birth", min_value=date(1920,1,1), max_value=date.today())
                today = date.today()
                calc_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                st.info(f"Calculated Age: {calc_age}")
                
                if st.form_submit_button("Register"):
                    df = st.session_state.voters_df
                    is_dup = not df[(df['name'].str.lower() == name.lower()) & (df['dob'] == str(dob))].empty
                    if not name: st.error("Name required")
                    elif calc_age < 18: st.error("Must be 18+.")
                    elif is_dup: st.warning("Already registered.")
                    else:
                        priv, pub = generate_key_pair()
                        new_voter = pd.DataFrame([{'name':name,'dob':str(dob),'age':calc_age,'public_key':pub,'has_voted':False}])
                        st.session_state.voters_df = pd.concat([df, new_voter], ignore_index=True)
                        save_voters(st.session_state.voters_df, DB_PATH)
                        st.success("Registered Successfully!")
                        st.code(f"Private Key (SECRET): {priv}", language="text")
                        st.warning("Copy this key! It is not stored anywhere else.")
        else:
            st.info("Registration is currently closed.")

    with tab_voter:
        if config_data["vote_open"]:
            with st.form("vote_form"):
                v_name = st.text_input("Full Name")
                v_dob = st.date_input("Date of Birth", min_value=date(1920,1,1), key="v_dob")
                v_sk = st.text_input("Private Key", type="password")
                candidate = st.selectbox("Candidate", config_data["candidates"])
                
                if st.form_submit_button("Submit"):
                    df = st.session_state.voters_df
                    match = df[(df['name'].str.lower() == v_name.lower()) & (df['dob'] == str(v_dob))]
                    if match.empty: st.error("Voter not found.")
                    else:
                        voter_data = match.iloc[0]
                        v_pk = voter_data['public_key']
                        if voter_data['has_voted']: st.warning("Already voted.")
                        else:
                            msg = f"{v_pk}-{candidate}"
                            sig = sign_transaction(v_sk, msg)
                            if sig and verify_signature(v_pk, msg, sig):
                                st.session_state.blockchain.new_transaction(v_pk, candidate)
                                st.session_state.blockchain.mine_block()
                                update_voter_status(st.session_state.voters_df, v_pk)
                                save_voters(st.session_state.voters_df, DB_PATH)
                                st.success("Vote Recorded!")
                            else: st.error("Invalid Private Key.")
        else:
            st.warning("Voting is not currently open.")

    with tab_res: show_results()
    with tab_ledg: show_ledger()
