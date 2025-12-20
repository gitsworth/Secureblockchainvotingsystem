def initialize_voters_df():
    """Creates the initial, empty DataFrame structure."""
    return pd.DataFrame(columns=[
        'id',
        'name', 
        'dob', # Added
        'age', # Added
        'public_key',
        'private_key', 
        'has_voted',
        'registration_date'
    ])
