import discord
from discord.ext import commands, tasks
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import os
import time

# -- إعدادات Selenium --
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"  # عدل حسب بيئتك
CHROME_BINARY_PATH = "/usr/local/chrome-linux/chrome"  # عدل حسب بيئتك
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

        # بيانات الكلان من الصفحة
        try:
            clan_data["name"] = driver.find_element(By.CSS_SELECTOR, "div[style*='font-size: 20px'] > b").text.strip()
        except NoSuchElementException:
            pass

        try:
            clan_data["description"] = driver.find_element(By.CSS_SELECTOR, "div[style*='color: rgba(255,255,255,0.5)']").text.strip()
        except NoSuchElementException:
            pass

        try:
            clan_data["tag"] = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(2) div b span").text.strip()
        except NoSuchElementException:
            pass

        try:
            clan_data["members"] = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(3) div b").text.strip()
        except NoSuchElementException:
            pass

        try:
            clan_data["clan_wars"] = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(4) div b").text.strip()
        except NoSuchElementException:
            pass

        try:
            clan_data["ranked"] = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(5) div b").text.strip()
        except NoSuchElementException:
            pass

        try:
            clan_data["unranked"] = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(6) div b").text.strip()
        except NoSuchElementException:
            pass

        try:
            clan_data["win_ratio"] = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(7) div b").text.strip()
        except NoSuchElementException:
            pass

        try:
            clan_data["bank"] = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(8) div b").text.strip()
        except NoSuchElementException:
            pass

        # اللاعبين الأونلاين
        try:
            player_rows = driver.find_elements(By.CSS_SELECTOR, "table.fullwidth.dark.stats.clan tbody tr:not(.spacer)")
            online_players = []
            for row in player_rows:
                try:
                    username = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) a span").text.strip()
                    server_status = row.find_element(By.CSS_SELECTOR, "td:nth-child(5)").text.strip()
                    if "Online" in server_status:
                        online_players.append(username)
                except NoSuchElementException:
                    continue
            clan_data["online_players"] = online_players
        except NoSuchElementException:
            pass

        clan_data["members"] = str(len(player_rows))  # تحديث عدد الأعضاء حسب عدد الصفوف

        return clan_data

    finally:
        driver.quit()


# -- بوت ديسكورد --

intents = discord.Intents.default()
intents.message_content = True  # ضروري لقراءة الأوامر

bot = commands.Bot(command_prefix="!", intents=intents)

CHANNEL_ID = 1404443185048064011  # رقم الروم الذي تريد إرسال الرسالة فيه

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print("لم أستطع العثور على الروم.")
        return

    # جلب بيانات الكلان في thread
    try:
        clan_data = await asyncio.to_thread(scrape_clan_status)

        online_count = len(clan_data["online_players"])
        members_count = clan_data["members"]

        online_list = ", ".join(clan_data["online_players"]) if online_count > 0 else "لا يوجد لاعبون أونلاين حالياً."

        embed = discord.Embed(title=f"🛡️ {clan_data['name']} [{clan_data['tag']}]", description=clan_data["description"], color=0xdaa520)
        embed.add_field(name="📊 إحصائيات الكلان", value=(
            f"👥 الأعضاء: {members_count}\n"
            f"⚔️ حروب الكلان: {clan_data['clan_wars']}\n"
            f"🏆 الرانكد: {clan_data['ranked']}\n"
            f"🔓 الأنرانكد: {clan_data['unranked']}\n"
            f"📈 نسبة الفوز: {clan_data['win_ratio']}\n"
            f"💰 رصيد البنك: {clan_data['bank']}"
        ), inline=False)
        embed.add_field(name=f"👤 حالة الأعضاء ({online_count}/{members_count})", value=online_list, inline=False)

        await channel.send(embed=embed)
        print("تم إرسال رسالة الكلان في الروم بنجاح.")

    except Exception as e:
        print(f"حدث خطأ أثناء جلب أو إرسال بيانات الكلان: {e}")



if __name__ == "__main__":
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not DISCORD_BOT_TOKEN:
        print("يرجى تعيين متغير البيئة DISCORD_BOT_TOKEN مع توكن البوت.")
    else:
        bot.run(DISCORD_BOT_TOKEN)
