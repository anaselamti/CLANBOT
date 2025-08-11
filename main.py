import discord
from discord.ext import commands, tasks
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import os
import time

# ===== إعداداتك =====
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # ضع التوكن في متغير بيئة
TARGET_CHANNEL_ID = 1404443185048064011  # الروم اللي حيعرض فيه البوت الحالة
CLAN_URL = "https://ffs.gg/clans.php?clanid=2915"

# مسارات الكروم (لو بتستخدم Docker أو استضافة لازم تحددها)
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
CHROME_BINARY_PATH = "/usr/local/chrome-linux/chrome"

# ===== إعداد البوت =====
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

status_message = None  # لتخزين الرسالة التي سيتم تعديلها

# ===== دالة جلب اللاعبين الأونلاين =====
def get_online_members():
    options = webdriver.ChromeOptions()
    options.binary_location = CHROME_BINARY_PATH
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    online_players = []

    try:
        driver.get(CLAN_URL)
        time.sleep(3)

        rows = driver.find_elements(By.CSS_SELECTOR, "table.stats tbody tr")
        for row in rows:
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) > 4:
                    username = cols[0].text.strip()
                    status = cols[4].text.strip()
                    if status.lower() == "online":
                        online_players.append(username)
            except:
                continue

    finally:
        driver.quit()

    return online_players

# ===== مهمة التحديث التلقائي =====
@tasks.loop(minutes=2)
async def update_clan_status():
    global status_message

    online_players = get_online_members()

    if online_players:
        embed = discord.Embed(
            title="📡 حالة الكلان",
            description=f"عدد اللاعبين الأونلاين: **{len(online_players)}**",
            color=discord.Color.green()
        )
        embed.add_field(name="اللاعبين:", value="\n".join(online_players), inline=False)
    else:
        embed = discord.Embed(
            title="📡 حالة الكلان",
            description="لا يوجد أي لاعب أونلاين حالياً.",
            color=discord.Color.red()
        )

    if status_message:
        await status_message.edit(embed=embed)
    else:
        channel = bot.get_channel(TARGET_CHANNEL_ID)
        if channel:
            status_message = await channel.send(embed=embed)

# ===== عند تشغيل البوت =====
@bot.event
async def on_ready():
    global status_message
    print(f"✅ Logged in as {bot.user}")
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel:
        status_message = await channel.send("⏳ جاري تحميل حالة الكلان...")
    update_clan_status.start()

# ===== تشغيل البوت =====
bot.run(DISCORD_TOKEN)
