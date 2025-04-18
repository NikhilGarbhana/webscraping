###------------------ IMPORT SECTION ------------------###

# Import required libraries
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import UnexpectedAlertPresentException, TimeoutException
from selenium.webdriver.common.alert import Alert

import pandas as pd
import time
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

###------------------ CONFIGURATION SECTION ------------------###


# Setup Chrome WebDriver - Configure Selenium to use Chrome
options = Options()
options.add_argument("--headless=new")  # Correct syntax for headless
options.add_argument("--disable-popup-blocking")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--start-maximized")
options.add_argument("user-agent=Mozilla/5.0")

# Optional: Disable image loading (better done via prefs)
# prefs = {"profile.managed_default_content_settings.images": 2}
# options.add_experimental_option("prefs", prefs)

prefs = {
  "profile.managed_default_content_settings.images": 2,
  "profile.default_content_setting_values.notifications": 2,
  "profile.default_content_setting_values.geolocation": 2
}
options.add_experimental_option("prefs", prefs)

###------------------ VARIABLES SECTION ------------------###

today = datetime.today().strftime("%d-%m-%Y")

url = "https://www.honda2wheelersindia.com/network/dealerLocator"

# Store showroom data"
data = []
state_cities = {}

# Constants
MAX_RETRIES = 2  # Number of retries per pincode
RESTART_BROWSER_AFTER = 10  # Restart Chrome every N pincodes
WAIT_TIME = 10  # Increased explicit wait time
DATA_SAVE_INTERVAL = 10  # Save every N pincodes

###------------------ PROCESS SECTION ------------------###

# Funtion to start a browser
def start_browser():
    """Starts a new browser session."""
    driver = webdriver.Chrome(service=Service(), options=options)
    driver.maximize_window()
    wait = WebDriverWait(driver, WAIT_TIME, poll_frequency=0.5)

    driver.get(url)
    time.sleep(2)  # Initial load wait
    
    return driver, wait

# Function to scrape the showrooms from particular city
def scrape_dealers(driver, wait, state, city):
    dealers = []
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, "html.parser")
    
    container = soup.find("div", class_="col-md-12 col-xs-12 col-sm-12")
    showroom_list = soup.find_all("div", class_="repeat-dealor")
    for showroom in showroom_list:
        values = showroom.find_all("div")
        name = values[0].find("span").text.strip()
        address = values[0].find("p").text.strip()
        
        phone_icon = values[1].find("i", class_="fa fa-phone")
        mobile_icon = values[1].find("i", class_="fa fa-mobile")
        # email_icon = values[1].find("i", class_="fa fa-envelope")
        
        phone = phone_icon.next_sibling.text.replace('"','').strip()
        mobile = mobile_icon.next_sibling.text.replace('"','').strip()
        email = values[1].find("a").text.strip()
        
        dealers.append([name if name else "", address if address else "", phone if phone else "", mobile if mobile else "", email if email else "", city, state])
        print([name if name else "", address if address else "", phone if phone else "", mobile if mobile else "", email if email else "", city, state])
    return dealers
    
# Function to select state and city
def select_state_city(driver, wait):

    # # Wait until the dropdown is present
    # wait.until(EC.presence_of_element_located((By.ID, "StateID")))
    
    # Get the Select object from the state dropdown
    state_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "StateID"))))
    for index in range(len(state_dropdown.options)):
        retry_count = 0
        # Re-fetch the dropdown and its options on every iteration
        state_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "StateID"))))

        state_option = state_dropdown.options[index]
        state_value = state_option.text

        state = state_option.get_attribute("value")

        if not state:
            continue
        print("Selecting state:", state_value)
        state_dropdown.select_by_value(state)

        # wait or do actions here (like triggering city loading, etc.)
        time.sleep(2)  # Or use a better WebDriverWait

        # Get the Select object from the city dropdown
        city_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "CityID"))))
        for index in range(len(city_dropdown.options)):
            retry_count = 0
            # Re-fetch the dropdown and its options on every iteration
            city_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "CityID"))))
    
            city_option = city_dropdown.options[index]
            city_value = city_option.text
    
            city = city_option.get_attribute("value")
    
            if not city:
                continue
            print("Selecting city:", city_value)
            city_dropdown.select_by_value(city)
    
            # wait or do actions here
            time.sleep(2)  # Or use a better WebDriverWait
            submit = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="divDealer"]/form/div/div/div/div[4]/button[1]')))
            submit.click()
            time.sleep(3)

            dealers = scrape_dealers(driver, wait, state_value, city_value)
            data.extend(dealers)
    
# Function to run the process step by step
def main():
    driver, wait = start_browser()
    select_state_city(driver, wait)
    driver.quit()

if __name__ == "__main__":
    main()
    df = pd.DataFrame(data, columns=["Showroom Name", "Address", "Phone", "Mobile", "Email", "City", "State"]).drop_duplicates()
        
    # Save updated file
    filename = f"honda_showrooms_{today}.csv"
    df.to_csv(filename, index=False)
    print(f"Done! ✅ Updated DataFrame saved as {filename}")
