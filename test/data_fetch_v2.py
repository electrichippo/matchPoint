from selenium import webdriver
from bs4 import BeautifulSoup
import time
from webdriver_manager.chrome import ChromeDriverManager
import re

def get_current_tournaments(lines):
    tag = "Tournaments"
    tag1 = "Charting Project"
    count = 0
    for line in lines:
        if tag in line:
            flag1 = count
        if tag1 in line:
            flag2 = count
        count+=1
    
    lines = lines[flag1+1:flag2]
    cleaned_list = [item for item in lines if item.strip() != '']

    return cleaned_list           


def get_raw_matches(lines, tag="Completed Matches"):
    count = 0
    for line in lines:
        if tag in line:
            compMatches = count
            break
        count+=1

    text = lines[compMatches]

    index = text.index(tag)
    text = text[index + len(tag):]
    text=text.replace("\xa0", " ")

    delimiters = r"(F:|SF:|QF:|R4:|R3:|R2:|R1:|Q2:|Q1:)"
    split_list = re.split(delimiters, text)
    matches = []
    current_match = ""
    for item in split_list:
        item = item.strip()
        if item in ["F:", "SF:", "QF:", "R4:", "R3:", "R2:", "R1:", "Q2:", "Q1:"]:
            if current_match:
                matches.append(current_match)
            current_match = item
        elif item:
            current_match += " " + item
    if current_match:
        matches.append(current_match.strip())
    return([match.strip() for match in matches if match.strip()])

def get_lines_from_url(url):
    driver = webdriver.Chrome()
    # Navigate to the web page
    driver.get(url)
    # Wait for the JavaScript to execute and load content
    time.sleep(2)  # Be cautious with time.sleep; it's usually better to use explicit waits
    # Get the page source after the JavaScript execution
    html = driver.page_source
    # Quit the WebDriver
    driver.quit()
    # Use Beautiful Soup to parse the HTML content
    soup = BeautifulSoup(html, 'html.parser')
    textRaw = soup.text
    completed_matches = []
    lines = textRaw.split('\n')
    return lines

lines = get_lines_from_url("https://www.tennisabstract.com/")
print(lines)

currentTournaments = get_current_tournaments(lines)

lines = get_lines_from_url("https://www.tennisabstract.com/current/2025ATPBarcelona.html")
upcomingMatchesRaw = get_raw_matches(lines)

results = []

for match_str in upcomingMatchesRaw:

    pattern = re.compile(
        r"^(?P<round>[A-Z0-9]+): "  # Round (e.g., F, SF, R16)
        r"(?P<winner>.+?) "         # Winner's name (non-greedy)
        r"d\. "                     # " d. " separator
        r"(?P<loser>.+?) "          # Loser's name (non-greedy)
        r"(?P<score>[\d\s\(\)]+)$"  # Score (digits, spaces, parentheses at the end)
    )
    match = pattern.match(match_str)
    if match:
        dict =  {
            "round": match.group("round"),
            "winner": match.group("winner").strip(),
            "loser": match.group("loser").strip(),
            "score": match.group("score").strip(),
        }
        results.append(dict)
    
    
print(results)
