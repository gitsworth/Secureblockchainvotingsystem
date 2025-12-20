import pandas as pd
import os

# --- DATABASE MANAGEMENT ---

def load_voters(db_path):
    """
    Loads the voters list from a CSV file.
    Initializes an empty DataFrame if the file does not exist.
    """
    if os.path.exists(db_path):
        try:
            voters_df = pd.read_csv(db_path)
            # Ensure keys are strings to prevent formatting errors
            if not voters_df.empty:
                voters_df['public_key'] = voters_df['public_key'].astype(str)
                voters_df['private_key'] = voters_df['private_key'].astype(str)
            return voters_df
        except Exception:
            return initialize_voters_df()
    else:
        return initialize_voters_df()

def initialize_voters_df():
    """Creates the initial, empty DataFrame structure."""
    return pd.DataFrame(columns=[
        'id',
        'name', 
        'dob',
        'age',
        'public_key',
        'private_key', 
        'has_voted',
        'registration_date'
    ])

def save_voters(voters_df, db_path):
    """Saves the current voters DataFrame to the CSV file."""
    voters_df.to_csv(db_path, index=False)

def update_voter_status(voters_df, public_key):
    """Marks a specific voter as 'True' for having voted."""
    # Ensure we are comparing strings
    mask = voters_df['public_key'].astype(str) == str(public_key)
    
    if mask.any():
        voters_df.loc[mask, 'has_voted'] = True
        return True
        
    return False
