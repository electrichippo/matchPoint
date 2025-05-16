import requests
import json
import time
from datetime import datetime

from datetime import datetime
import pytz

def format_player_name(name: str) -> str:
    """
    Removes the comma from a player name string and flips the first and last names.

    Args:
        name: The player name string in the format "LastName, FirstName".

    Returns:
        The player name string in the format "FirstName LastName".
        Returns the original string if no comma is found.
    """
    if "," in name:
        parts = name.split(",")
        last_name = parts[0].strip()
        first_name = parts[1].strip()
        return f"{first_name} {last_name}"
    else:
        return name

def convert_to_AEST(time):
    # Define the UTC timezone
    utc_timezone = pytz.utc

    # Localize the UTC datetime object
    utc_datetime = utc_timezone.localize(time)

    # Define the AEST timezone
    aest_timezone = pytz.timezone('Australia/Brisbane')  # Brisbane is in AEST

    # Convert the UTC datetime to AEST
    aest_datetime = utc_datetime.astimezone(aest_timezone)

    return aest_datetime.strftime("%Y-%m-%d %H:%M:%S")

def get_tennis_tournaments(api_url):
    """
    Fetches tennis tournament keys and names from the given API endpoint,
    excluding 'Futures Markets'.

    Args:
        api_url (str): The URL of the API endpoint.

    Returns:
        list: A list of dictionaries, where each dictionary contains the 'key' and
              'name' of a tennis tournament (excluding Futures Markets).
              Returns an empty list if no valid data is found or there's an error.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    all_tournaments = []
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()

        for locale in data.get('locales', []):
            locale_name = locale.get('name')
            if locale_name == "Futures Markets":
                continue  # Skip Futures Markets

            tournaments = locale.get('competitions', [])
            for tournament in tournaments:
                name = tournament.get("name")
                if "ITF" in name or "Doubles" in name or "Challenger" in name:
                    continue
                all_tournaments.append({
                    "key": tournament.get("key"),
                    "name": name
                })

        return all_tournaments

    except requests.exceptions.RequestException as e:
        print(f"Error fetching tournament data: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding tournament JSON: {e}")
        return []

def get_match_data_for_tournament(competition_id, tournamentName):
    """
    Loops through a list of tournaments and fetches relevant match data for each.

    Args:
        base_match_api_url (str): The base URL for the match data API endpoint,
                                    with '{competition_id}' as a placeholder.
        tournaments (list): A list of tournament dictionaries, each containing
                            a 'key' (competition ID).

    Returns:
        dict: A dictionary where keys are tournament keys and values are lists
              of simplified match data dictionaries for that tournament.
              Returns an empty dictionary if no match data is fetched or if
              there are errors.
    """
    base_match_api_url = "https://api.au.pointsbet.com/api/mes/v3/events/featured/competition/{competition_id}?page=1"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    all_match_data = []
    count = 0

    if competition_id:
        match_api_url = base_match_api_url.format(competition_id=competition_id)
        print(f"Fetching match data for: {tournamentName} (ID: {competition_id})")
        try:
            response = requests.get(match_api_url, headers=headers)
            response.raise_for_status()
            match_data_list = response.json().get('events', [])
            simplified_matches = []
            for match in match_data_list:
                if match.get("isLive"):
                    continue
                match_info = {
                    "round": None,
                    "tournamentName": tournamentName,
                    "startsAt": convert_to_AEST(datetime.strptime(match.get("startsAt"), "%Y-%m-%dT%H:%M:%SZ")),
                    "homeTeam": format_player_name(match.get("homeTeam")),
                    "awayTeam": format_player_name(match.get("awayTeam")),
                    "homeTeamPrice": None,
                    "awayTeamPrice": None,
                    "winner": None
                }
                for market in match.get("fixedOddsMarkets", []):
                    if market.get("eventName") == "Match Result":
                        i = 0
                        for outcome in market.get("outcomes", []):
                            if i == 0:
                                match_info["homeTeamPrice"] = outcome.get("price")
                                i+=1
                            else:
                                match_info["awayTeamPrice"] = outcome.get("price")
                            

                        break # Once "Match Result" is found, no need to check other markets

                simplified_matches.append(match_info)

            for match in simplified_matches:
                all_match_data.append(match)
            print(f"Successfully fetched {len(simplified_matches)} matches for {tournamentName}")
            # time.sleep(0.1) # Be respectful to the API by adding a small delay
            count+=1
        except requests.exceptions.RequestException as e:
            print(f"Error fetching match data for {tournamentName} (ID: {competition_id}): {e}")
        except json.JSONDecodeError as e:
            print(f"Error decoding match JSON for {tournamentName} (ID: {competition_id}): {e}")
    else:
        print(f"Warning: Tournament '{tournamentName}' has no competition key.")
    return all_match_data

def get_data(competition_id, tournamentName):

    all_matches = get_match_data_for_tournament(competition_id, tournamentName)
    return all_matches

def get_json_data(competition_id, tournamentName):

    all_matches = get_data(competition_id, tournamentName)

    import json
    with open("output.json", "w") as f:
        json.dump(all_matches, f, indent=4)

        
if __name__ == "__main__":
    all_matches = []
    all_ATP_matches = get_data(172136, "ATP Rome")
    all_WTA_matches = get_data(10747, "WTA Rome")

    for match in all_ATP_matches:
        all_matches.append(match)
    # for match in all_WTA_matches:
    #     all_matches.append(match)

    import csv
    import json
    with open("output.json", "w") as f:
        json.dump(all_matches, f, indent=4)

    filename = 'output.csv'

    with open(filename, 'w', newline='') as csvfile:
        fieldnames = all_matches[0].keys() if all_matches else []
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in all_matches:
            writer.writerow(row)

    print(all_matches)

