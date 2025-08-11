from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time

CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
CHROME_BINARY_PATH = "/usr/local/chrome-linux/chrome"
CLAN_URL = "https://ffs.gg/clans.php?clanid=2915"

def scrape_clan_status():
    options = webdriver.ChromeOptions()
    options.binary_location = CHROME_BINARY_PATH
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    clan_data = {
        "name": "غير معروف",
        "description": "لا يوجد وصف",
        "tag": "غير معروف",
        "members": "0",
        "clan_wars": "0",
        "ranked": "0 - 0W - 0L",
        "unranked": "0",
        "win_ratio": "0%",
        "bank": "$0",
        "discord": "لا يوجد رابط",
        "online_players": []
    }

    try:
        driver.get(CLAN_URL)
        time.sleep(7)

        # استخراج اسم الكلان
        try:
            clan_data["name"] = driver.find_element(By.CSS_SELECTOR, "div[style*='font-size: 20px'] > b").text.strip()
        except NoSuchElementException:
            pass

        # استخراج الوصف
        try:
            desc_element = driver.find_element(By.CSS_SELECTOR, "div[style*='color: rgba(255,255,255,0.5)']")
            clan_data["description"] = desc_element.text.strip()
        except NoSuchElementException:
            pass

        # استخراج التاج
        try:
            tag_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(2) div b span")
            clan_data["tag"] = tag_element.text.strip()
        except NoSuchElementException:
            pass

        # استخراج الأعضاء
        try:
            members_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(3) div b")
            clan_data["members"] = members_element.text.strip()
        except NoSuchElementException:
            pass

        # استخراج حروب الكلان
        try:
            wars_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(4) div b")
            clan_data["clan_wars"] = wars_element.text.strip()
        except NoSuchElementException:
            pass

        # استخراج الرانكد
        try:
            ranked_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(5) div b")
            clan_data["ranked"] = ranked_element.text.strip()
        except NoSuchElementException:
            pass

        # استخراج الأنرانكد
        try:
            unranked_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(6) div b")
            clan_data["unranked"] = unranked_element.text.strip()
        except NoSuchElementException:
            pass

        # استخراج نسبة الفوز
        try:
            win_ratio_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(7) div b")
            clan_data["win_ratio"] = win_ratio_element.text.strip()
        except NoSuchElementException:
            pass

        # استخراج البنك
        try:
            bank_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(8) div b")
            clan_data["bank"] = bank_element.text.strip()
        except NoSuchElementException:
            pass

        # استخراج اللاعبين وأونلاين منهم (من الجدول كما سبق)
        try:
            player_rows = driver.find_elements(By.CSS_SELECTOR, "table.fullwidth.dark.stats.clan tbody tr:not(.spacer)")
            for row in player_rows:
                try:
                    username = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) a span").text.strip()
                    server_status = row.find_element(By.CSS_SELECTOR, "td:nth-child(5)").text.strip()
                    if "Online" in server_status:
                        clan_data["online_players"].append(username)
                except NoSuchElementException:
                    continue
        except NoSuchElementException:
            pass

        # تحديث عدد الأعضاء بدقة حسب عدد الصفوف (يمكنك تعديلها)
        clan_data["members"] = str(len(player_rows))

        return clan_data

    finally:
        driver.quit()


# للتجربة فقط:
if __name__ == "__main__":
    data = scrape_clan_status()
    print(data)
