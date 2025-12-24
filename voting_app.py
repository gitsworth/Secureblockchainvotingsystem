import streamlit as st
import pandas as pd
import json
import os
import time
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
                data = json.load(f)
                defaults = {"reg_open": True, "vote_open": False, "ended": False, "candidates": ["Candidate A", "Candidate B"]}
                for key, val in defaults.items():
                    if key not in data:
                        data[key] = val
                return data
        except:
            pass
    return {"reg_open": True, "vote_open": False, "ended": False, "candidates": ["Candidate A", "Candidate B"]}

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f)

# --- INITIALIZATION & GLOBAL SYNC ---
config_data = load_config()

if 'blockchain' not in st.session_state:
    st.session_state.blockchain = Blockchain(BC_PATH)
    st.session_state.admin_authenticated = False
    st.session_state.config_cache = config_data

# FORCE REFRESH
st.session_state.voters_df = load_voters(DB_PATH)
st.session_state.blockchain.load_chain()

st.set_page_config(layout="wide", page_title="Secure Blockchain Voting")

# --- LIVE SYNC MECHANISM ---
@st.fragment(run_every=3)
def live_sync():
    current_config = load_config()
    if st.session_state.config_cache != current_config:
        st.session_state.config_cache = current_config
        st.rerun()

live_sync()

query_params = st.query_params
current_page = query_params.get("page", "voter")

# --- UI COMPONENTS ---
def show_results():
    st.header("📊 Election Results")
    if config_data.get("ended"):
        results_tally = {c: 0 for c in config_data["candidates"]}
        st.session_state.blockchain.load_chain()
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
            st.metric("Total Votes Cast", int(results_df['Votes'].sum()))
        with col2:
            st.subheader("Visual Representation")
            st.bar_chart(results_df.set_index('Candidate'))
    else:
        st.info("🕒 The election is still in progress. Results will be published by the Host once voting ends.")

def show_ledger():
    st.header("🔗 Blockchain Ledger")
    st.info("Privacy Masking Enabled: Voter IDs are hashed using SHA-256.")
    for block in reversed(st.session_state.blockchain.chain):
        with st.expander(f"Block #{block.index} - Hash: {block.hash[:15]}..."):
            st.json(block.to_dict())

# --- PAGE ROUTING ---
if current_page == "host":
    st.title("🛡️ Host Administration Portal")
    tab_host, tab_res, tab_ledg = st.tabs(["⚙️ Controls", "📊 Results", "🔗 Ledger"])
    
    with tab_host:
        if not st.session_state.admin_authenticated:
            st.subheader("Admin Login")
            pwd_input = st.text_input("Enter Admin Password", type="password")
            if st.button("Unlock Portal"):
                if pwd_input == ADMIN_PASSWORD:
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect Password")
        else:
            st.success("Authenticated as Administrator")
            
            # Election Control Buttons
            st.subheader("Election Lifecycle")
            c1, c2, c3 = st.columns(3)
            if c1.button("🚀 Start Voting", disabled=config_data["vote_open"] or config_data["ended"], use_container_width=True):
                config_data["reg_open"] = False
                config_data["vote_open"] = True
                save_config(config_data)
                st.rerun()
            if c2.button("🛑 End Election", disabled=not config_data["vote_open"] or config_data["ended"], use_container_width=True):
                config_data["vote_open"] = False
                config_data["ended"] = True
                save_config(config_data)
                st.rerun()
            if c3.button("♻️ Reset All Data", use_container_width=True):
                st.session_state.blockchain.reset_chain()
                st.session_state.voters_df = pd.DataFrame(columns=['name', 'dob', 'age', 'public_key', 'has_voted'])
                save_voters(st.session_state.voters_df, DB_PATH)
                save_config({"reg_open": True, "vote_open": False, "ended": False, "candidates": ["Candidate A", "Candidate B"]})
                st.rerun()

            st.divider()
            
            # --- CANDIDATE MANAGEMENT (STRICT VALIDATION) ---
            st.subheader("📝 Candidate Management")
            is_locked = config_data["vote_open"] or config_data["ended"]
            
            if not is_locked:
                st.info("Enter candidates (one per line). Duplicates are automatically removed (case-insensitive).")
                current_cands_str = "\n".join(config_data["candidates"])
                new_cands_input = st.text_area("Candidate Registry", value=current_cands_str, height=150)
                
                if st.button("Save Candidate List"):
                    # Process lines: strip whitespace and ignore empty lines
                    lines = [line.strip() for line in new_cands_input.split("\n") if line.strip()]
                    
                    # Duplicate check logic (ignore case)
                    seen = set()
                    unique_list = []
                    for name in lines:
                        if name.lower() not in seen:
                            seen.add(name.lower())
                            unique_list.append(name)
                    
                    if not unique_list:
                        st.error("Error: At least one candidate name is required.")
                    elif len(unique_list) < len(lines):
                        st.warning("Duplicate candidates detected and merged.")
                        config_data["candidates"] = unique_list
                        save_config(config_data)
                        st.rerun()
                    else:
                        config_data["candidates"] = unique_list
                        save_config(config_data)
                        st.success("Candidate list saved successfully.")
                        st.rerun()
            else:
                st.warning("⚠️ Candidate registration is LOCKED. Changes are not permitted after voting has started.")
                st.write("**Registered Candidates:**")
                for c in config_data["candidates"]:
                    st.write(f"- {c}")

            st.divider()
            st.subheader("👥 Live Voter Registry Audit")
            st.dataframe(st.session_state.voters_df, width='stretch')

    with tab_res: show_results()
    with tab_ledg: show_ledger()

else: # Voter Portal
    st.title("🗳️ Public Voter Portal")
    t_reg, t_vote, t_res, t_ledg = st.tabs(["📝 Registration", "🗳️ Cast Vote", "📊 Results", "🔗 Ledger"])
    
    with t_reg:
        if config_data["reg_open"]:
            st.subheader("Voter Registration Form")
            with st.form("reg_form"):
                name = st.text_input("Full Name")
                dob = st.date_input("Date of Birth", min_value=date(1920,1,1), max_value=date.today())
                today = date.today()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                
                if st.form_submit_button("Register"):
                    df = st.session_state.voters_df
                    is_duplicate = not df[(df['name'].str.lower() == name.lower()) & (df['dob'] == str(dob))].empty
                    
                    if not name:
                        st.error("Please enter your name.")
                    elif age < 18:
                        st.error(f"Ineligible: Age {age}. Must be 18+.")
                    elif is_duplicate:
                        st.warning("You are already registered.")
                    else:
                        priv, pub = generate_key_pair()
                        new_voter = pd.DataFrame([{'name': name, 'dob': str(dob), 'age': age, 'public_key': pub, 'has_voted': False}])
                        save_voters(pd.concat([df, new_voter], ignore_index=True), DB_PATH)
                        st.success("Registration Successful!")
                        st.warning("COPY THIS PRIVATE KEY:")
                        st.code(priv)
        else:
            st.info("📝 Registration is closed. Voting phase is active.")

    with t_vote:
        if config_data["vote_open"]:
            st.subheader("Secure Voting Form")
            with st.form("vote_form"):
                v_name = st.text_input("Registered Full Name")
                v_sk = st.text_input("Your Private Key", type="password")
                choice = st.selectbox("Select Candidate", config_data["candidates"])
                if st.form_submit_button("Cast Ballot"):
                    df = st.session_state.voters_df
                    match = df[df['name'].str.lower() == v_name.lower()]
                    if match.empty:
                        st.error("Name not found.")
                    elif match.iloc[0]['has_voted']:
                        st.warning("Already voted.")
                    else:
                        v_pk = match.iloc[0]['public_key']
                        msg = f"{v_pk}-{choice}"
                        if verify_signature(v_pk, msg, sign_transaction(v_sk, msg)):
                            st.session_state.blockchain.new_transaction(v_pk, choice)
                            st.session_state.blockchain.mine_block()
                            update_voter_status(df, v_pk)
                            save_voters(df, DB_PATH)
                            st.success("Vote securely recorded!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Invalid Private Key.")
        elif config_data["ended"]:
            st.error("🏁 The election has ended.")
        else:
            st.info("🕒 Voting has not started yet. Please register.")

    with t_res: show_results()
    with t_ledg: show_ledger()
