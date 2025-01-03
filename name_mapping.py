import pandas as pd
import json
from helpers.utils import normalize_name


with open('utils/name_map_odds.json', 'r') as f:
    name_map = json.load(f)


odds = pd.read_csv('data/odds_first_basket.csv')[['name']].drop_duplicates().sort_values('name').reset_index(drop = True)
metadata = pd.read_csv('data/player_metadata.csv')
odds['name_norm'] = odds['name'].apply(normalize_name)
odds['player_id'] = odds['name'].map(name_map)
assert odds['name_norm'].value_counts().max() == 1, 'Normalized name duplicate in odds'
assert odds['player_id'].value_counts().max() == 1, 'Dupplicate player_id on odds'
# Subset of players needing to be mapped
odds_ = odds.copy()[odds['player_id'].isna()]


merged = pd.merge(
    odds_[['name', 'name_norm']],
    metadata[['name_norm', 'player_id']],
    on = 'name_norm',
    how = 'left'
    )

merged_check = merged.copy()[merged['player_id'].notna()]
assert odds['name_norm'].value_counts().max() == 1, 'Normalized name duplicate in merged_check'
assert odds['player_id'].value_counts().max() == 1, 'Duplicated player_id in merged_check'

name_map_add = dict(zip(merged_check['name'], merged_check['player_id']))


with open('utils/name_map_odds.json', 'w') as f:
    json.dump(name_map | name_map_add, f, indent = 4)


merged_need = merged.copy()[merged['player_id'].isna()]
if merged_need.shape[0] > 0:

    players_need_id = merged_need['name'].to_list()

    import smtplib
    from email.mime.text import MIMEText
    import os

    # Specify the email contents
    player_list = '\n\t'.join(players_need_id)
    indent = '\n\n\t'

    mail = MIMEText(
    f"""
    {len(players_need_id)} players could not be matched to a Basketball Reference ID:
    {indent}{player_list}
    """
    )

    # Set my email address and the password key
    my_mail = 'martinbog19@gmail.com'
    if os.getenv("GITHUB_ACTIONS") == "true" :
        app_password = os.getenv('GMAIL_APP_KEY')
    else :
        with open('secrets/gmail_app_key.txt') as f:
            app_password = f.read()
    # Set the subject of the email
    mail['Subject'] = '[LeFirstBasket] Manual name-ID matching required (ODDS)'

    # Send the email using Gmail's SMTP server
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()  # Upgrade connection to secure
        server.login(my_mail, app_password)  # Login with app password
        server.sendmail(my_mail, ['martinbog19@gmail.com'], mail.as_string())
    print("Email sent successfully!")