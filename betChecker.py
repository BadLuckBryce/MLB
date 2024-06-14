
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import date
import smtplib
from email.message import EmailMessage


def getData(year, df):
    away_team_list = []
    home_team_list = []
    winning_team_list = []
    netProfit = 0

    url = f"https://www.baseball-reference.com/leagues/MLB/{year}-schedule.shtml"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    game_sections = soup.find_all('p', {'class': "game"})


    datesData = df.Date
    gameData = df.Game
    betTeamData = df.Team_Bet
    betAmountData = df.Amount_Bet
    returnsData = df.Winning_Return
    nData = len(datesData)

    for section in game_sections:
        section_text = section.text.strip()
        section_split = section_text.split('\n')




        away_team = section_split[0]
        home_team = section_split[3]

        away_score_string = section_split[1]
        home_score_string = section_split[4]
        away_score_length = len(away_score_string)
        home_score_length = len(home_score_string)
        if away_score_length > 5 or home_score_length > 5:
            continue

        away_score = int(away_score_string.split('(')[1].split(')')[0])
        home_score = int(home_score_string.split('(')[1].split(')')[0])

        if away_score > home_score:
            winning_team = away_team
        else:
            winning_team = home_team

#
        gameDateHTMLString = str(section.contents[5].next)
        gameDateHTMLString = gameDateHTMLString.split("/")[3]
        gameDateStringArray = ["", "", ""]



        for i in range(3, 11):
            if i <= 6:
                j = 0
            elif i <= 8:
                j = 1
            else:
                j = 2
            gameDateStringArray[j] = gameDateStringArray[j]+gameDateHTMLString[i]

        gameDate = gameDateStringArray[0]+"-"+gameDateStringArray[1]+"-"+gameDateStringArray[2]

        for k in range(1, nData):
            dateK = datesData[k]._date_repr
            if not dateK == gameDate:
                continue
            matchup = gameData[k]
            teamA = matchup.split("v")[0]
            teamB = matchup.split("v")[-1]

            if teamA == "Red":
                teamA = "Red Sox"
            elif teamA == "Diamondbacks":
                teamA = "D\'Backs"
            if teamB == "Red":
                teamB = "Red Sox"
            elif teamB == "Diamondbacks":
                teamB = "D\'Backs"
            elif teamB == "es":
                teamB = "Braves"

            betGame = False
            if teamA in home_team and teamB in away_team:
                betGame = True
            elif teamA in away_team and teamB in home_team:
                betGame = True

            if not betGame:
                continue

            activeBet = betTeamData[k]
            if activeBet == "Red":
                activeBet = "Red Sox"
            elif activeBet == "Diamondbacks":
                activeBet = "D\'Backs"

            if activeBet in winning_team:
                netProfit = netProfit + returnsData[k]
            else:
                netProfit = netProfit - betAmountData[k]




    return netProfit

def todaysPicks(df, today):
    datesData = df.Date
    gameData = df.Game
    betTeamData = df.Team_Bet
    betAmountData = df.Amount_Bet
    returnsData = df.Winning_Return
    nData = len(datesData)

    betVector = [["Match", "Bet on:", "Bet Value:", "Potential Winnings:"]]

    for i in range(1, nData):
        dateK = datesData[i]._date_repr
        if dateK == today:
            betVector.append([gameData[i], betTeamData[i], round(betAmountData[i], 2), round(returnsData[i], 2)])

    return betVector


year = "2024"
bookieFile = "C:\\Users\\david borders\\PycharmProjects\\Mafia\\Bookie_2024.xlsx"
df = pd.read_excel(bookieFile)
netProfits = getData(year, df)

netProfits = round(netProfits, 2)

today = str(date.today())
bets = todaysPicks(df, today)

print("Date: "+today)
print("Total Profits $"+str(netProfits))

for i in range(len(bets)):
    print(str(i).rjust(2) + " | " + str(bets[i][0]).ljust(21) + " | " + str(bets[i][1]).ljust(21) + " | " + str(bets[i][2]).ljust(21) + " | " + str(bets[i][3]).ljust(6, "0"))


file = open("C:\\Users\\david borders\\PycharmProjects\\Mafia\\todays picks.txt", 'w')
file.write("Date: "+today+"\n")
file.write("Total Profits $"+str(netProfits)+"\n")
for i in range(len(bets)):
    file.write(str(i).rjust(2) + " | " + str(bets[i][0]).ljust(21) + " | " + str(bets[i][1]).ljust(21) + " | " + str(bets[i][2]).ljust(21) + " | " + str(bets[i][3]).ljust(6, "0")+"\n")
file.close()



# Create an EmailMessage object
fileName = "C:\\Users\\david borders\\PycharmProjects\\Mafia\\MLB_emailList.xlsx"
df = pd.read_excel(fileName)
emails = df.Emails

toLine = emails[0]
for i in range(1, len(emails)):
    activeAddress = str(emails[i])
    if len(activeAddress.split("@")) < 2:
        continue
    toLine = toLine+", "+emails[i]

msg = EmailMessage()
sendStr = "Total Profits $"+str(netProfits)+"\n"

for i in range(len(bets)):
    sendStr = sendStr+(str(i).rjust(2) + " | " + str(bets[i][0]).ljust(21) + " | " + str(bets[i][1]).ljust(21) + " | " + str(bets[i][2]).ljust(21) + " | " + str(bets[i][3]).ljust(6, "0")+"\n")

msg.set_content(sendStr)
# Set the sender and recipient
msg["Subject"] = f"MLB Robot Status Update - Date: "+today
msg["From"] = "botb70082@gmail.com"
msg["To"] = toLine

# Connect to the SMTP server (Gmail in this case)
with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login("botb70082@gmail.com", "ttmu jxvm wcax gsom")
    server.send_message(msg)