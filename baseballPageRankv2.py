
#imports

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

def pullIndex(team, teamList, nTeams):

    for i in range(nTeams):
        if team.strip() == teamList[i]:
            index = i
            break
    return index

def getData(year):
    away_team_list = []
    home_team_list = []
    winning_team_list = []

    url = f"https://www.baseball-reference.com/leagues/MLB/{year}-schedule.shtml"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    game_sections = soup.find_all('p', {'class': "game"})

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

        away_team_list.append(away_team)
        home_team_list.append(home_team)
        winning_team_list.append(winning_team)

    data = pd.DataFrame({'Away': away_team_list, 'Home': home_team_list, 'Winning': winning_team_list})
    return data

def save_to_excel(data, year):
    if data is not None:
        filename = f'mlb_season_{year}.xlsx'
        data.to_excel(filename, index=True)
        print(f"Data saved to {filename}")

def buildNetwork(df, postSeason):

    awayTeamList = df['Away']
    nGames = len(awayTeamList)

    teams = []
    for i in range(nGames):
        if awayTeamList[i] in teams:
            continue
        else:
            teams.append(awayTeamList[i])

    numTeams = len(teams)
    networkMatrix = np.zeros([numTeams, numTeams])

    for i in range(nGames - postSeason):
        awayTeam = df.iloc[i][1]
        homeTeam = df.iloc[i][2]
        winningTeam = df.iloc[i][3]

        awayIndex = pullIndex(awayTeam, teams, numTeams)
        homeIndex = pullIndex(homeTeam, teams, numTeams)
        winningIndex = pullIndex(winningTeam, teams, numTeams)
        if awayTeam == winningTeam:
            losingIndex = homeIndex
        else:
            losingIndex = awayIndex

        networkMatrix[winningIndex][losingIndex] = networkMatrix[winningIndex][losingIndex] + 1.0

    sumVector = np.sum(networkMatrix, axis=0)
    for i in range(len(sumVector)):
        if sumVector[i] == 0:
            sumVector[i] = 1

    for i in range(numTeams):
        for j in range(numTeams):
            networkMatrix[i][j] = networkMatrix[i][j]/sumVector[j]

    return networkMatrix, teams, numTeams

def iterativeMarkov(M,d, alpha ,nTeams):
    e = 0.0001
    Ri = np.zeros([nTeams, 1])/nTeams
    R = np.ones([nTeams, 1])/nTeams
    dR = np.ones([nTeams, 1])*10
    while max(dR) > e:
        Ri = R
        R = d + alpha*np.matmul(M,Ri)
        dR = abs(R - Ri)

    return e, R

def pageRank(M, damping, postSeason):

    M, teams, nTeams = buildNetwork(df,postSeason)
    dampingvector = np.ones([nTeams, 1]) * (1 - damping)/nTeams
    if damping == 1:
        eigenvalues,eigenvectors = np.linalg.eig(M)
    else:
        eigenvalues, eigenvectors = iterativeMarkov(M, dampingvector, damping, nTeams)

    ranking = np.zeros([nTeams,1])
    for i in range(nTeams):
        ranking[i]= abs(np.real(eigenvectors[i][0]))

    ranking = ranking * 100 / max(ranking)
    rankingList = []
    for i in range(nTeams):
        rankingList.append(ranking[i][0])

    sortedData = sorted(zip(rankingList, teams), reverse=True)
    sorted_rankings, sorted_teams = zip(*sortedData)

    return sorted_rankings, sorted_teams

def completeTeam(team, teamsList):
    for current in teamsList:
        if team.strip() in current:
            teamOutput = current
            break
    return teamOutput

def getRank(team, teamsList, ranking, nTeams):


    fullTeam = completeTeam(team, teamsList)
    index = pullIndex(fullTeam, teamsList, nTeams)
    rank = ranking[index]
    return rank

def createOdds(teams, ranking, df, numTeams):
    awayTeamList = df['Away']
    homeTeamList = df['Home']
    winningTeamList = df['Winning']

    nEntries = 6
    rankingRange = max(ranking) - min(ranking)
    binSize = rankingRange/nEntries

    nGames = len(awayTeamList)

    correctPredictions = np.zeros([nEntries-1, 1])
    attemptedPredictions = np.zeros([nEntries-1, 1])

    for i in range(nGames):
        rank1 = getRank(awayTeamList[i], teams, ranking, numTeams)
        rank2 = getRank(homeTeamList[i], teams, ranking, numTeams)
        if rank1 > rank2:
            predictedWinner = awayTeamList[i]
        else:
            predictedWinner = homeTeamList[i]
        pointDifference = np.abs(rank1 - rank2)
        a = predictedWinner
        b = winningTeamList[i]
        for j in range(nEntries-2, -1, -1):
            if pointDifference > j*binSize:
                attemptedPredictions[j] = attemptedPredictions[j]+1
                if predictedWinner.strip() == winningTeamList[i].strip():
                    correctPredictions[j] = correctPredictions[j] + 1
                    break
    accuracy = correctPredictions/attemptedPredictions
    return accuracy


year = input("Enter the year for MLB season data: ")
fileName = f'mlb_season_{year}.xlsx'

if year == "2024":
    postSeason = 0
else:
    postSeason = 30

try:
    int(year)
except ValueError:
    print("Please enter a valid year.")

data = getData(year)
save_to_excel(data, year)
df = pd.read_excel(fileName)

damping = 0.85
ranking, teams = pageRank(df, damping, postSeason)

numTeams = len(teams)
print("\n\n")
for i in range(numTeams):
    print(teams[i]+":    "+str(ranking[i]))


print("\n\n")
accuracy = createOdds(teams, ranking, df, numTeams)
print(accuracy)


matchMake = True
while matchMake:
    matchup = input("Enter Match Up [a v b]: ")
    if matchup == "kill":
        break
    else:
        team1 = matchup.split(" v ")[0]
        team2 = matchup.split(" v ")[1]

        rank1 = getRank(team1, teams, ranking, numTeams)
        rank2 = getRank(team2, teams, ranking, numTeams)

        pointsDifference = np.abs(rank1 - rank2)
        confidence = ">="+str(accuracy[4]*100)
        for j in range(1, 6):
            if pointsDifference < 10*j:
                confidence = str(accuracy[j-1]*100)
                break

        if rank1 > rank2:
            print(team1+":  "+str(rank1 - rank2)+" pts difference | Confidence: "+confidence)
        else:
            print(team2+":  "+str(rank2 - rank1)+" pts difference| Confidence: "+confidence)





