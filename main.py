import discord
from discord.ext import commands, tasks
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import os

# إعدادات مسارات كروم وكروم درايفر (مطابق Dockerfile)
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
CHROME_BINARY_PATH = "/usr/local/chrome-linux/chrome"

CLAN_URL = "https://ffs.gg/clans.php?clanid=2915"
TARGET_CHANNEL_ID = 1404443185048064011  # غيره برقم الروم عندك

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

status_message = None

def scrape_clan_status():
    options = webdriver.ChromeOptions()
    options.binary_location = CHROME_BINARY_PATH
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(CLAN_URL)
        time.sleep(4)  # انتظر تحميل الصفحة

        # اجلب كل صفوف جدول اللاعبين
        rows = driver.find_elements(By.CSS_SELECTOR, "table.stats tbody tr")
        total_members = len(rows)

        online_players = []

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 5:
                username = cols[0].text.strip()
                status = cols[4].text.strip().lower()
                # نفحص حالة اللاعب هل هو أونلاين (مثلاً: "online" أو "in-game")
                if "online" in status or "in-game" in status:
                    online_players.append(username)

        return total_members, online_players

    finally:
        driver.quit()

@tasks.loop(minutes=2)
async def update_clan_status():
    global status_message

    total_members, online_players = scrape_clan_status()

    description = f"عدد أعضاء الكلان: **{total_members}**\n"
    description += f"عدد اللاعبين أونلاين: **{len(online_players)}**\n\n"
    if online_players:
        description += "**اللاعبين الأونلاين:**\n" + "\n".join(online_players)
    else:
        description += "لا يوجد لاعبين أونلاين حالياً."

    embed = discord.Embed(
        title="📡 حالة الكلان",
        description=description,
        color=discord.Color.blue()
    )

    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if not channel:
        print("❌ لم أجد الروم المحدد")
        return

    if status_message:
        await status_message.edit(embed=embed)
    else:
        status_message = await channel.send(embed=embed)

@bot.event
async def on_ready():
    global status_message
    print(f"✅ Logged in as {bot.user}")
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel:
        status_message = await channel.send("⏳ جاري تحميل حالة الكلان...")
    update_clan_status.start()

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
