from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import schedule
import json
import os
from datetime import datetime
from app.data_fetch import data_to_json

# --- Configuration ---
# UPLOAD_URL = "https://matchpoints.pythonanywhere.com/upload"
UPLOAD_URL = "http://192.168.1.146:5000/upload"
UPLOAD_FREQUENCY_HOURS = 0.1
UPLOAD_FREQUENCY_SECONDS = UPLOAD_FREQUENCY_HOURS * 60 * 60  # 12 hours in seconds
JSON_FILE_PATH = "output.json"  # Path to the JSON file you want to upload

# --- Helper Functions ---
def refresh_json(competitionDetails):
    """Creates a dummy JSON file for testing if it doesn't exist."""

    data_to_json(competitionDetails)
    
    

def upload_json(url, filepath):
    """Opens the browser, uploads the specified JSON file, and submits the form."""
    try:
        # Initialize WebDriver (you might need to adjust the path to your webdriver)
        driver = webdriver.Chrome()  # Or webdriver.Firefox(), etc.
        driver.get(url)
        print(f"Opened URL: {url}")

        # Find the file input element
        file_input = driver.find_element(By.NAME, "file")

        # Send the path of the JSON file to the input element
        file_input.send_keys(os.path.abspath(filepath))
        print(f"Selected file: {os.path.abspath(filepath)}")

        # Find and click the submit button
        submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")
        submit_button.click()
        print("Clicked 'Upload' button.")

        # Optionally, you can add code here to wait for a success message or check the page content
        time.sleep(5)  # Wait for the upload to complete

    except Exception as e:
        print(f"An error occurred during upload: {e}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()
            print("Browser closed.")

def job():
    """The function that will be executed every 12 hours."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting JSON upload...")
    try:
        refresh_json([[11481, "French Open Men's"], [11480, "French Open Women's"]])  # Ensure the JSON file exists
        upload_json(UPLOAD_URL, JSON_FILE_PATH)
        print(f"upload complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except:
        print(f"upload failed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# --- Scheduling ---
if __name__ == "__main__":
    print(f"Selenium script started. Uploading JSON every {UPLOAD_FREQUENCY_HOURS}  hours...")
    schedule.every(UPLOAD_FREQUENCY_SECONDS).seconds.do(job)

    while True:
        schedule.run_pending()
        time.sleep(10)