import bs4
import requests
import pandas as pd
import numpy as np
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Initialise the bet parameters
wins = [58.5,53.5,38.5,55.5, 43.5,44.5] 
ou = ["over", "under", "over", "over", "under","over"]

data_dict = {"Line": wins, "Over or Under?": ou, "Wins": np.nan, "Losses": np.nan, "Projected Wins": np.nan, "RAG": ""}

table = pd.DataFrame(
    data_dict,
    index = ['Boston Celtics', 'Philadelphia 76ers', 'Detroit Pistons', 'Houston Rockets', 'Minnesota Timberwolves', 'San Antonio Spurs'],
    columns = ['Line','Over or Under?', 'Wins', 'Losses', 'Projected Wins', 'RAG']
    )

# Get latest standings from ESPN
url = 'http://www.espn.com.au/nba/standings'

r = requests.get(url)
souped = bs4.BeautifulSoup(r.text)
souped_table = souped.find_all('table')
tbl_list = pd.read_html(str(souped_table))

# Rbind East & West Standings Tables
east_standings = tbl_list[3]
east_standings["Team"] = tbl_list[1][0].str.replace(r'\d{0,1}[A-Z]{2,3}(?=[A-Z]{1})', '')

west_standings = tbl_list[7]
west_standings["Team"] = tbl_list[5][0].str.replace(r'\d{0,1}[A-Z]{2,3}(?=[A-Z]{1})', '')

standings_table = pd.concat([east_standings,west_standings], ignore_index = True).rename(columns = {"Unnamed: 0":"Team"})

# Project wins, add status and fold back into output table
for irow in table.iterrows():
    team = irow[0]
    
    match_series = standings_table['Team'].str.contains(team)
    idx = match_series[match_series==True].index
    team_row = standings_table.ix[idx][['W','L']]
    
    projected_wins = team_row['W'] * 82 / (team_row['W'] + team_row['L'])
    table.set_value(team, 'Wins', team_row['W'].astype('int'))
    table.set_value(team, 'Losses', team_row['L'].astype('int'))
    table.set_value(team, 'Projected Wins', round(projected_wins,2))
    
    multiplier = np.where(irow[1][1]=='over', 1, -1)
    
    if all((projected_wins - irow[1][0]) * multiplier > 2):
        status = "Green"
    elif all((projected_wins - irow[1][0]) * multiplier > -4):
        status = "Amber"
    else:
        status = "Red"
            
    table.set_value(team, 'RAG', status)

table['Wins'] = table['Wins'].astype('int')
table['Losses'] = table['Losses'].astype('int')

# Email Update

# Credentials defines a single variable with my gmail password (included in the gitignore)
import credentials

fromaddr = "tomwbish@gmail.com"
recipients = ["tomwbish@gmail.com"]
msg = MIMEMultipart()
msg['From'] = fromaddr
msg['To'] =  ", ".join(recipients)
msg['Subject'] = "NBA Multi Status Update"
 
# Convert DF to HTML
body = table.to_html()

msg.attach(MIMEText(body,'html'))
 
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login(fromaddr, credentials.pwd)
text = msg.as_string()
server.sendmail(fromaddr, recipients, text)
server.quit()