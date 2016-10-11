import bs4
import requests
import pandas as pd
import numpy as np
import smtplib

# Initialise the bet parameters
wins = [46.5,37.5,25.5,44.5,20.5,57.5,35.5] 
ou = ["over","under","under","over","under","over","under"]

data_dict = {"ou_wins": wins, "over_under": ou, "current_wins": np.nan, "current_losses": np.nan, "projected_wins": np.nan, "rag_status": ""}

table = pd.DataFrame(
    data_dict,
    index = ['Utah Jazz', 'Milwaukee Bucks', 'Los Angeles Lakers', 'Atlanta Hawks', 'Brooklyn Nets', 'San Antonio Spurs','Miami Heat'],
    columns = ['ou_wins','over_under', 'current_wins', 'current_losses', 'projected_wins', 'rag_status?']
    )


# Get latest standings from ESPN
url = 'http://www.espn.com.au/nba/standings'

r = requests.get(url)
souped = bs4.BeautifulSoup(r.text)
souped_table = souped.find_all('table')
tbl_list = pd.read_html(str(souped_table))

# Rbind East & West Standings Tables
standings_table = pd.concat([tbl_list[0],tbl_list[1]], ignore_index = True).rename(columns = {"Unnamed: 0":"Team"})


# Project wins, add status and fold back into output table
for irow in table.iterrows():
    team = irow[0]
    match_series = standings_table['Team'].str.contains(team)
    idx = match_series[match_series==True].index
    team_row = standings_table.ix[idx][['W','L']]
    
    projected_wins = team_row['W'] * 82 / (team_row['W'] + team_row['L'])
    table.set_value(team, 'current_wins', team_row['W'])
    table.set_value(team, 'current_losses', team_row['L'])
    table.set_value(team, 'projected_wins', projected_wins)
    
    multiplier = np.where(irow[1][1]=='over', 1, -1)
    
    if all((projected_wins - irow[1][0]) * multiplier > 2):
        status = "Green"
    elif all((projected_wins - irow[1][0]) * multiplier > -4):
        status = "Amber"
    else:
        status = "Red"
            
    table.set_value(team, 'rag_status', status)

# Email Update
