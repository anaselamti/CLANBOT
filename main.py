import discord
from discord.ext import commands, tasks
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import asyncio
import os

# --- Discord Bot Settings ---
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # ضع توكن البوت هنا أو متغير بيئة
CHANNEL_ID = 1404474899564597308  # ID القناة التي سترسل فيها الرسائل

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Selenium Settings ---
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"  # عدل حسب مسار chromedriver عندك
CHROME_BINARY_PATH = "/usr/local/chrome-linux/chrome"  # عدل حسب مسار كروم عندك
CLAN_URL = "https://ffs.gg/clans.php?clanid=2915"  # رابط صفحة الكلان

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
        "name": "Goalacticos",
        "description": "No description available",
        "tag": "Gs_",
        "members": "0",
        "clan_wars": "0",
        "ranked": "0 - 0W - 0L",
        "unranked": "0",
        "win_ratio": "0%",
        "bank": "$0",
        "online_players": []
    }

    try:
        driver.get(CLAN_URL)

        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[style*='color: rgba(255,255,255,0.5)']")))

        try:
            desc_element = driver.find_element(By.CSS_SELECTOR, "div[style*='color: rgba(255,255,255,0.5)']")
            if desc_element.text.strip():
                clan_data["description"] = desc_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            wars_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(4) div b")
            if wars_element.text.strip():
                clan_data["clan_wars"] = wars_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            ranked_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(5) div b")
            if ranked_element.text.strip():
                clan_data["ranked"] = ranked_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            unranked_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(6) div b")
            if unranked_element.text.strip():
                clan_data["unranked"] = unranked_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            win_ratio_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(7) div b")
            if win_ratio_element.text.strip():
                clan_data["win_ratio"] = win_ratio_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            bank_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(8) div b")
            if bank_element.text.strip():
                clan_data["bank"] = bank_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            player_rows = driver.find_elements(By.CSS_SELECTOR, "table.fullwidth.dark.stats.clan tbody tr:not(.spacer)")
            clan_data["online_players"] = []
            for row in player_rows:
                try:
                    username = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) a span").text.strip()
                    server_status = row.find_element(By.CSS_SELECTOR, "td:nth-child(5)").text.strip()
                    if "Online" in server_status:
                        clan_data["online_players"].append(username)
                except NoSuchElementException:
                    continue
            clan_data["members"] = str(len(player_rows))
        except NoSuchElementException:
            clan_data["online_players"] = []
            clan_data["members"] = "0"

        return clan_data

    finally:
        driver.quit()

last_message = None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    send_clan_update.start()

@tasks.loop(seconds=45)
async def send_clan_update():
    global last_message
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print("Could not find the channel.")
        return

    try:
        clan_data = await asyncio.to_thread(scrape_clan_status)

        online_count = len(clan_data["online_players"])
        members_count = clan_data["members"]
        online_list = ", ".join(clan_data["online_players"]) if online_count > 0 else "No players are currently online."

        embed = discord.Embed(
            title=f"🛡️ {clan_data['name']} [{clan_data['tag']}]",
            description=clan_data["description"],
            color=0xdaa520
        )
        embed.add_field(
            name="📊 Clan Statistics",
            value=(
                f"👥 Members: {members_count}\n"
                f"⚔️ Clan Wars: {clan_data['clan_wars']}\n"
                f"🏆 Ranked: {clan_data['ranked']}\n"
                f"🔓 Unranked: {clan_data['unranked']}\n"
                f"📈 Win Ratio: {clan_data['win_ratio']}\n"
                f"💰 Bank Balance: {clan_data['bank']}"
            ),
            inline=False
        )
        embed.add_field(
            name=f"👤 Members Status ({online_count}/{members_count})",
            value=online_list,
            inline=False
        )

        if last_message is None:
            last_message = await channel.send(embed=embed)
        else:
            await last_message.edit(embed=embed)

        print("Clan status updated.")

    except Exception as e:
        print(f"Error while updating clan data: {e}")

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
