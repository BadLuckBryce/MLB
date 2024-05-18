
#imports

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import date


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
    if team == "Diamondbacks":
        team = "D'Backs"
    elif team == "Red":
        team = "Red Sox"

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
    bins = np.array((range(nEntries)))*binSize

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
    accuracy_vector = correctPredictions/attemptedPredictions
    accuracy = np.array(np.zeros([len(accuracy_vector)+1 , 1]))
    accuracy[0] = 0.5
    for i in range(len(accuracy_vector)):
        accuracy[i+1] = accuracy_vector[i][0]

    return accuracy, bins


def interpolate(x0, xVec, yVec):

    power = 2
    M = np.ones([len(xVec), power])
    fx = np.ones([len(xVec), 1])
    x = np.ones([1, power+1])
    a0 = 0.5

    for i in range(len(xVec)):
        for j in range(1, power+1):
            M[i][j-1] = xVec[i]**j
        fx[i] = yVec[i][0] - a0

    for i in range(power+1):
        x[0][i] = x0**i

    a = np.matmul(np.linalg.pinv(M), fx)
    a = np.insert(a, 0, a0)
    y0 = np.matmul(x, a)[0]



    # if x0 <= xVec[0]:
    #     y0 = yVec[0][0]
    # elif x0 >= xVec[len(xVec)-1]:
    #     y0 = yVec[len(yVec)-1][0]
    # else:
    #     for i in range(1, len(yVec)):
    #         xa = xVec[i-1]
    #         xb = xVec[i]
    #         ya = yVec[i-1][0]
    #         yb = yVec[i][0]
    #         if not (x0 > xa and x0 < xb):
    #             continue
    #         r = xb - xa
    #
    #         y0 = (1/r)*((x0 - xa)*yb + (xb - x0)*ya)

    return y0


def findGames():
    url = f"https://sportsbook.draftkings.com/leagues/baseball/mlb"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    tableLabels = soup.find_all('th', {'class': "sportsbook-table__column-row"})
    tableRows = soup.find_all('td', {'class': "sportsbook-table__column-row"})

    sizeTableLabels = int(len(tableLabels)/2)
    sizeTable = len(tableRows)
    oddsList = []

    row = 0
    for i in range(sizeTableLabels):
        oddsList.append([[], [], [], []])

        teamString = tableLabels[i].text
        teamString = teamString.split(" ")[1]
        for j in range(10):
            teamString = teamString.split(str(j))[0]

        numcaps = 0
        for element in teamString:
            isCap = element.isupper()
            if isCap:
                numcaps = numcaps+1
                if numcaps > 1:
                    teamString = teamString.split(element)[0]
                    break


        if i % 2 == 0:
            oddsList[row][0] = teamString
        else:
            oddsList[row][1] = teamString
            row = row+1

    row = 0
    for i in range(2, sizeTable, 3):
        cellString = tableRows[i].find_all('div', {'class': "sportsbook-outcome-cell__element"})
        if len(cellString) == 0:
            teamOdds = "-50000000"
        else:
            teamOdds = cellString[1].contents[0].contents[0]
        if i % 2 == 0:
            oddsList[row][2] = int(teamOdds.replace('−', '-'))
        else:
            oddsList[row][3] = int(teamOdds.replace('−', '-'))
            row = row+1

    return oddsList


# pull data
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

# rank teams
damping = 0.85
ranking, teams = pageRank(df, damping, postSeason)

# report ranking
numTeams = len(teams)
print("\n\n")
for i in range(numTeams):
    print(str(i).rjust(2) + " | " + teams[i].ljust(21) + " | " + str(round(ranking[i], 3)).ljust(6, "0"))

# find accuracy
print("\n\n")
accuracy, bins = createOdds(teams, ranking, df, numTeams)

# Find good deals
betFinder = True
if betFinder and year == "2024":
    oddsList = findGames()
    lengthGames = len(oddsList)

    teamBets = []
    expectedValueBets = []
    matchupBets = []
    bestOdds = []
    runningTeams = []
    for i in range(lengthGames):
        killLoop = False
        for j in range(4):
            if not oddsList[i][j]:
                killLoop = True
                break
        if killLoop:
            break

        matchup = oddsList[i][0]+"v"+oddsList[i][1]

        team1 = oddsList[i][0]
        team2 = oddsList[i][1]
        if team1 == "Red":
            team1 = "Red Sox"
        if team2 == "Red":
            team2 = "Red Sox"

        if team1 in runningTeams or team2 in runningTeams:
            continue
        else:
            runningTeams.append(team1)
            runningTeams.append(team2)

        rank1 = getRank(team1, teams, ranking, numTeams)
        rank2 = getRank(team2, teams, ranking, numTeams)

        pointsDifference = np.abs(rank1 - rank2)
        confidence = interpolate(pointsDifference, bins, accuracy)

        bettingOdds = (round(100*(confidence)/(100-(confidence))))

        if rank1 > rank2:
            favorite = team1
            underdog = team2
            favoriteOdds = oddsList[i][2]
            underdogOdds = oddsList[i][3]
        else:
            favorite = team2
            underdog = team1
            favoriteOdds = oddsList[i][3]
            underdogOdds = oddsList[i][2]

        chosenBet = 100
        if favoriteOdds < 0:
            favoriteOdds = -100*chosenBet/favoriteOdds
        if underdogOdds < 0:
            underdogOdds = -100*chosenBet/underdogOdds

        favoriteExpectedValue = confidence*favoriteOdds - chosenBet*(1-confidence)
        underdogExpectedValue = (1-confidence)*underdogOdds - chosenBet*(confidence)

        if favoriteExpectedValue > underdogExpectedValue:
            maxExpectedValue = favoriteExpectedValue
            bestBet = favorite
            bestValueOdds = favoriteOdds/chosenBet
        else:
            maxExpectedValue = underdogExpectedValue
            bestBet = underdog
            bestValueOdds = underdogOdds/chosenBet

        teamBets.append(bestBet)
        expectedValueBets.append(maxExpectedValue*100/chosenBet)
        matchupBets.append(matchup)
        bestOdds.append(bestValueOdds)

    sortedData = sorted(zip(expectedValueBets, teamBets, matchupBets, bestOdds), reverse=True)
    expectedValueBets, teamBets, matchupBets, bestOdds = zip(*sortedData)

    # print("\n\n Best Bets \n\n")

    threshold = 10
    safeBets = []
    safeBetTeams = []
    safeBetMatchups =[]
    safeBetOdds =[]
    lengthGames = len(matchupBets)
    for i in range(lengthGames):
        if expectedValueBets[i] < threshold:
            continue
        # print(str(i).rjust(2) + " | " + teamBets[i].ljust(21) + " | " + str(round(expectedValueBets[i], 1)).ljust(6, "0"))
        safeBets.append(expectedValueBets[i])
        safeBetTeams.append(teamBets[i])
        safeBetMatchups.append(matchupBets[i])
        safeBetOdds.append(bestOdds[i])

    safeBets = np.array(safeBets)
    safeBetOdds = np.array(safeBetOdds)
    initialBets = safeBets

    safeBets = safeBets*chosenBet/sum(safeBets)
    safeBetOdds = safeBetOdds*(safeBets)

    print("\n\n Safe Bets \n\n")
    for i in range(lengthGames):
        if expectedValueBets[i] < threshold:
            continue
        print(str(i).rjust(2) + " | " + safeBetTeams[i].ljust(21) + " | " + str(round(safeBets[i], 1)).ljust(6, "0"))

    ## Log bets
    today = str(date.today())
    bookieFile = "Bookie_2024.xlsx"
    dfBookie = pd.read_excel(bookieFile)

    dateBookie = dfBookie.Date.tolist()
    gamesBookie = dfBookie.Game.tolist()
    betTeamBookie = dfBookie.Team_Bet.tolist()
    betAmountBookie = dfBookie.Amount_Bet.tolist()
    winningsBookie = dfBookie.Winning_Return.tolist()


    nLogs = len(dateBookie)
    for k in range(len(safeBets)):
        loggedgame = False
        for i in range(len(dateBookie)):
            if today == dateBookie[i] and gamesBookie[i] == safeBetMatchups[k]:
                loggedgame = True
                break

        if loggedgame:
            continue

        dateBookie.append(today)
        gamesBookie.append(safeBetMatchups[k])
        betTeamBookie.append(safeBetTeams[k])
        betAmountBookie.append(safeBets[k])
        winningsBookie.append(safeBetOdds[k])

    dataBookie = pd.DataFrame({'Date': dateBookie, 'Game': gamesBookie, 'Team_Bet': betTeamBookie, 'Amount_Bet': betAmountBookie, 'Winning_Return': winningsBookie})
    dataBookie.to_excel(bookieFile, index=True)

# manual comparisons
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
        confidence = interpolate(pointsDifference, bins, accuracy)*100

        bettingOdds = str(round(100*(confidence)/(100-(confidence))))

        payoutFavorite = "-"+bettingOdds
        payoutUnderdog = "+"+bettingOdds

        if rank1 > rank2:
            favorite = team1
            underdog = team2
        else:
            favorite = team2
            underdog = team1

        print("\n")
        print("FAVORITE: " + favorite + "   |   " + payoutFavorite + " | Confidence: " + str(round(confidence,2)))
        print("UNDERDOG: " + underdog + "   |   " + payoutUnderdog)
        print("\n")

