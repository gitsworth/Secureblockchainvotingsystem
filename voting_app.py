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

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"reg_open": True, "vote_open": False, "ended": False, "candidates": ["Candidate A", "Candidate B"]}

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f)

config_data = load_config()

if 'blockchain' not in st.session_state:
    st.session_state.voters_df = load_voters(DB_PATH)
    st.session_state.blockchain = Blockchain(BC_PATH)
    st.session_state.admin_authenticated = False

st.set_page_config(layout="wide", page_title="Secure Blockchain Voting")

query_params = st.query_params
current_page = query_params.get("page", "voter")

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
        col1, col2 = st.columns(2)
        with col1:
            st.table(results_df.set_index('Candidate'))
        with col2:
            st.bar_chart(results_df.set_index('Candidate'))
    else:
        st.info("Results are hidden until the Host ends the election.")

def show_ledger():
    st.header("🔗 Blockchain Ledger")
    st.info("Privacy Masking Enabled: Voter IDs are hashed.")
    for block in reversed(st.session_state.blockchain.chain):
        st.json(block.to_dict())

if current_page == "host":
    st.title("🛡️ Host Administration Portal")
    t1, t2, t3 = st.tabs(["⚙️ Controls", "📊 Results", "🔗 Ledger"])
    with t1:
        if not st.session_state.admin_authenticated:
            pwd = st.text_input("Admin Password", type="password")
            if st.button("Login"):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.admin_authenticated = True
                    st.rerun()
        else:
            c1, c2, c3 = st.columns(3)
            if c1.button("Start Voting"):
                config_data.update({"reg_open": False, "vote_open": True})
                save_config(config_data); st.rerun()
            if c2.button("End Election"):
                config_data.update({"vote_open": False, "ended": True})
                save_config(config_data); st.rerun()
            if c3.button("Reset All Data"):
                st.session_state.blockchain.reset_chain()
                st.session_state.voters_df = pd.DataFrame(columns=['name', 'dob', 'age', 'public_key', 'has_voted'])
                save_voters(st.session_state.voters_df, DB_PATH)
                save_config({"reg_open": True, "vote_open": False, "ended": False, "candidates": ["A", "B"]})
                st.rerun()
            st.dataframe(st.session_state.voters_df, width='stretch')
    with t2: show_results()
    with t3: show_ledger()
else:
    st.title("🗳️ Public Voter Portal")
    t1, t2, t3, t4 = st.tabs(["📝 Register", "🗳️ Vote", "📊 Results", "🔗 Ledger"])
    with t1:
        if config_data["reg_open"]:
            with st.form("reg"):
                name = st.text_input("Name")
                dob = st.date_input("DOB")
                if st.form_submit_button("Register"):
                    priv, pub = generate_key_pair()
                    new_v = pd.DataFrame([{'name':name,'dob':str(dob),'age':20,'public_key':pub,'has_voted':False}])
                    st.session_state.voters_df = pd.concat([st.session_state.voters_df, new_v], ignore_index=True)
                    save_voters(st.session_state.voters_df, DB_PATH)
                    st.success("Registered!")
                    st.code(priv)
    with t2:
        if config_data["vote_open"]:
            with st.form("vote"):
                v_name = st.text_input("Name")
                v_sk = st.text_input("Private Key", type="password")
                cand = st.selectbox("Candidate", config_data["candidates"])
                if st.form_submit_button("Submit Vote"):
                    df = st.session_state.voters_df
                    match = df[df['name'] == v_name]
                    if not match.empty:
                        v_pk = match.iloc[0]['public_key']
                        msg = f"{v_pk}-{cand}"
                        if verify_signature(v_pk, msg, sign_transaction(v_sk, msg)):
                            st.session_state.blockchain.new_transaction(v_pk, cand)
                            st.session_state.blockchain.mine_block()
                            update_voter_status(st.session_state.voters_df, v_pk)
                            save_voters(st.session_state.voters_df, DB_PATH)
                            st.success("Vote Cast!")
    with t3: show_results()
    with t4: show_ledger()
