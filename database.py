import pandas as pd
import os

def load_voters(db_path):
    if os.path.exists(db_path):
        try:
            df = pd.read_csv(db_path)
            # Private keys are NO LONGER in this file for security
            df['public_key'] = df['public_key'].astype(str)
            return df
        except:
            return initialize_voters_df()
    return initialize_voters_df()

def initialize_voters_df():
    # Removed private_key from storage schema
    return pd.DataFrame(columns=[
        'name', 'dob', 'age', 'public_key', 'has_voted'
    ])

def save_voters(df, db_path):
    df.to_csv(db_path, index=False)

def update_voter_status(df, public_key):
    mask = df['public_key'].astype(str) == str(public_key)
    if mask.any():
        df.loc[mask, 'has_voted'] = True
        return True
    return False
