from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time,random

class BrowserController:
    def __init__(self):
        self.driver = None

    def start(self):
        if self.driver is None:
            options = Options()

            # 🔥 separate clean profile
            options.add_argument(r"user-data-dir=C:\astra-profile")

            self.driver = webdriver.Chrome(options=options)
            self.driver.maximize_window()

    def search_google(self, query):
        self.start()

        self.driver.get("https://www.google.com")

        search = self.driver.find_element(By.NAME, "q")
        search.clear()
        search.send_keys(query)
        search.submit()

        time.sleep(2)

    def open_first_result(self):
        if not self.driver:
            return False

        results = self.driver.find_elements(By.XPATH, "//h3")

        if results:
            results[0].click()
            return True

        return False

    def click_images(self):
        if not self.driver:
            return False

        try:
            images_btn = self.driver.find_element(By.LINK_TEXT, "Images")
            images_btn.click()
            return True
        except:
            print("Images button not found")
            return False

    def scroll_down(self):
        if not self.driver:
            return False

        for _ in range(random.randint(3, 6)):
            self.driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(random.uniform(0.4, 0.9))

        return True
    
    def scroll_up(self):
        if not self.driver:
            return False

        for _ in range(random.randint(3, 6)):
            self.driver.execute_script("window.scrollBy(0, -400);")
            time.sleep(random.uniform(0.4, 0.9))

        return True

    def click_first_image(self):
        if not self.driver:
            return False

        try:
            images = self.driver.find_elements(By.XPATH, "//img")

            for img in images:
                if img.is_displayed():
                    img.click()
                    return True

            return False
        except:
            print("No image found")
            return False

    def open_image(self):
        if not self.driver:
            return False

        try:
            big = self.driver.find_element(By.XPATH, "//img[contains(@class,'n3VNCb')]")
            big.click()
            return True
        except:
            print("Preview image not found")
            return False