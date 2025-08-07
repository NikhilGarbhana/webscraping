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

cities_url = "https://www.bikewale.com/dealer-showrooms/tvs/"
url = "https://www.tvsmotor.com/tvs-dealer-locator/tvs-2-wheeler"

# Store showroom data"
data = []
state_cities = {}

finished_places = []

# Constants
MAX_RETRIES = 2  # Number of retries per pincode
RESTART_BROWSER_AFTER = 10  # Restart Chrome every N pincodes
WAIT_TIME = 10  # Increased explicit wait time
DATA_SAVE_INTERVAL = 10  # Save every N pincodes

# Function to pull cities
def cities():
    # Pull states and cities data from url
    page_source = requests.get(cities_url)
    cities_soup = BeautifulSoup(page_source.content, "html.parser")
    container = cities_soup.find("div", class_="o-em o-gf")
    states_list = container.find_all("li", class_="o-m1 o-mo o-mO")

    for i in states_list:
        state = i.find_all("div")[0].text
        # print(state)
        cities_list = i.find_all("li")
        temp = []
        for j in cities_list:
            # print(j.text.split(" ")[0])
            cleaned_text = re.sub(r"\s*\(\d+\)", "", j.text)
            cleaned_text = re.sub(r"\s*\(.*?\)", "", cleaned_text)
            temp.append(cleaned_text)
        
        state_cities[state] = temp
    
# Funtion to start a browser
def start_browser():
    """Starts a new browser session."""
    driver = webdriver.Chrome(service=Service(), options=options)
    driver.maximize_window()
    wait = WebDriverWait(driver, WAIT_TIME, poll_frequency=0.5)

    driver.get(url)
    time.sleep(2)  # Initial load wait
    
    return driver, wait

# Function to search city
def search(wait, option_city):
    search_box = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="controlHeaderInput"]')))
    search_box.send_keys(Keys.CONTROL + "a")
    search_box.send_keys(Keys.DELETE)
    # time.sleep(3)
    search_box.send_keys(option_city)
    time.sleep(3)

# Function to scrape dealer details
def scrape_dealers(driver, city, state):
    """Extracts dealer details from the page source."""
    soup = BeautifulSoup(driver.page_source, "html.parser")
    dealers = []
    
    showroom_list = soup.find("section", class_="latlong-leaflet-autocomplete-list")
    if showroom_list:
        showrooms = showroom_list.find_all("div", class_="latlong-leaflet-autocomplete-datalist")
        for showroom in showrooms:
            name = showroom.find("div", class_="storeName")
            address = showroom.find("p", class_=lambda x: x and "storeaddress" in x)
            phone = showroom.find("div", class_="latlong-list-phonenumber")
            email = showroom.find("div", class_="email-contact")
            
            dealers.append([name.text.strip() if name else "", address.text.strip() if address else "", phone.text.strip() if phone else "", email.text.strip() if email else "", city, state])
    
    # if not dealers:
    #     print("[WARNING] No dealers found, might be a loading issue.")
    # print(dealers)
    return dealers

def main():
    cities()
    driver, wait = start_browser()
    for option_state in list(state_cities.keys())[33:35]:
        for k,option_city in enumerate(state_cities[option_state]):
        # for k,option_city in list(enumerate(state_cities[option_state]))[:2]:
            retry_count_city = 0
            while retry_count_city < MAX_RETRIES:
                try:
                    search(wait, option_city)
                    list_items = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'latlong-leaflet-autocomplete-li')))
                    temp = [li.text for li in list_items]
                    # print(temp)
                    for j in range(len(temp)):
                        retry_count_place = 0
                        if temp[j] not in finished_places:
                            while retry_count_place < MAX_RETRIES:
                                try:
                                    search(wait, temp[j])
                                    ele = driver.find_element(By.CLASS_NAME, 'latlong-leaflet-autocomplete-li')
                                    ele.click()
                                    time.sleep(2)
                                    # Scrape dealers (you may want to call the scrape_dealers function here)
                                    dealers = scrape_dealers(driver, option_city, option_state)
                                    data.extend(dealers)
                                    finished_places.append(temp[j])
                                    break
                                except:
                                    # break
                                    retry_count_place += 1
                                    driver.refresh()
                                    time.sleep(3)
                                    if retry_count_place == MAX_RETRIES:
                                        # print(f"⏩ Skipping {option_city} due to multiple failures.")
                                        break
                    break
                except:
                    # break
                    retry_count_city += 1
                    driver.refresh()
                    time.sleep(3)
                    if retry_count_city == MAX_RETRIES:
                        # print(f"⏩ Skipping {option_city} due to multiple failures.")
                        break

if __name__ == "__main__":
    main()
    ###------------------ DATA SAVING SECTION ------------------###
    df = pd.DataFrame(data, columns=["Showroom Name", "Address", "Phone", "Mail", "City", "State"]).drop_duplicates()
    filename = f"tvs_showrooms_4_{today}.csv"
    df.to_csv(filename, index=False)
