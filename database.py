import pandas as pd
import os

def load_voters(file_path):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return pd.DataFrame(columns=['name', 'dob', 'age', 'public_key', 'has_voted'])

def save_voters(df, file_path):
    df.to_csv(file_path, index=False)

def update_voter_status(df, public_key):
    df.loc[df['public_key'] == public_key, 'has_voted'] = True
