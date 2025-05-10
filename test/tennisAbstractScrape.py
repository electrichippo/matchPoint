from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

url = "https://www.tennisabstract.com/current/2025ATPRome.html"

try:
    # Set up Chrome WebDriver using webdriver-manager
    driver = webdriver.Chrome(ChromeDriverManager().install())

    driver.get(url)

    # Wait for either "Upcoming Matches" or "Completed Matches" heading to be visible
    wait = WebDriverWait(driver, 20)
    wait.until(EC.visibility_of_element_located((By.XPATH, "//h2[text()='Upcoming Matches'] | //h2[text()='Completed Matches']")))

    # Get the entire HTML source after waiting
    full_html = driver.page_source
    print(full_html)

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    driver.quit()