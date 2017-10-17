import bs4
import requests
import pandas as pd
import numpy as np
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Initialise the bet parameters
wins = [40.5,32.5,38.5,54.5] 
ou = ["under","under","over","under"]

data_dict = {"ou_wins": wins, "over_under": ou, "current_wins": np.nan, "current_losses": np.nan, "projected_wins": np.nan, "rag_status": ""}

table = pd.DataFrame(
    data_dict,
    index = ['Philadelphia 76ers', 'Los Angeles Lakers', 'Detroit Pistons', 'Boston Celtics'],
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