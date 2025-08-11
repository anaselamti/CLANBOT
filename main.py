import os
import asyncio
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time

# إعدادات ChromeDriver وChrome (عدّل المسارات حسب بيئتك)
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
CHROME_BINARY_PATH = "/usr/local/chrome-linux/chrome"
CLAN_URL = "https://ffs.gg/clans.php?clanid=2915"

# دالة سكراب الكلان
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

        try:
            clan_data["name"] = driver.find_element(By.CSS_SELECTOR, "div[style*='font-size: 20px'] > b").text.strip()
        except NoSuchElementException:
            pass

        try:
            desc_element = driver.find_element(By.CSS_SELECTOR, "div[style*='color: rgba(255,255,255,0.5)']")
            clan_data["description"] = desc_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            tag_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(2) div b span")
            clan_data["tag"] = tag_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            members_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(3) div b")
            clan_data["members"] = members_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            wars_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(4) div b")
            clan_data["clan_wars"] = wars_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            ranked_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(5) div b")
            clan_data["ranked"] = ranked_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            unranked_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(6) div b")
            clan_data["unranked"] = unranked_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            win_ratio_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(7) div b")
            clan_data["win_ratio"] = win_ratio_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            bank_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(8) div b")
            clan_data["bank"] = bank_element.text.strip()
        except NoSuchElementException:
            pass

        # استخراج اللاعبين الأونلاين من الجدول
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

        clan_data["members"] = str(len(player_rows))

        return clan_data

    finally:
        driver.quit()

# إعداد بوت الديسكورد
intents = commands.Intents.default()
intents.message_content = True  # ضروري لقراءة الرسائل
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')

@bot.command()
async def clan(ctx):
    await ctx.send("جارِ جلب بيانات الكلان، يرجى الانتظار...")
    clan_data = await asyncio.to_thread(scrape_clan_status)

    online_count = len(clan_data["online_players"])
    members_count = clan_data["members"]

    online_players = ", ".join(clan_data["online_players"]) if online_count > 0 else "لا يوجد لاعبون أونلاين حالياً."

    message = (
        f"**🛡️ اسم الكلان:** {clan_data['name']}\n"
        f"**📜 الوصف:**\n{clan_data['description']}\n"
        f"**🏷️ التاج:** {clan_data['tag']}\n"
        f"**👥 الأعضاء:** {members_count}\n"
        f"**⚔️ حروب الكلان:** {clan_data['clan_wars']}\n"
        f"**🏆 الرانكد:** {clan_data['ranked']}\n"
        f"**🔓 الأنرانكد:** {clan_data['unranked']}\n"
        f"**📈 نسبة الفوز:** {clan_data['win_ratio']}\n"
        f"**💰 رصيد البنك:** {clan_data['bank']}\n"
        f"**👤 حالة الأعضاء ({online_count}/{members_count}):**\n{online_players}"
    )

    await ctx.send(message)

# شغل البوت مع توكن من متغير بيئي
bot_token = os.getenv("DISCORD_BOT_TOKEN")
if not bot_token:
    print("ERROR: Please set the DISCORD_BOT_TOKEN environment variable.")
else:
    bot.run(bot_token)
