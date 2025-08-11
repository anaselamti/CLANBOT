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

        # استخراج معلومات الكلان العامة
        clan_name_element = driver.find_element(By.CSS_SELECTOR, "div[style*='font-size: 20px; color: rgb(185,164,94)'] b")
        clan_name = clan_name_element.text.strip()
        
        members_count_element = driver.find_element(By.XPATH, "//div[contains(@class, 'wwClanInfo') and contains(., 'members')]/div/b")
        total_members = members_count_element.text.strip()
        
        # استخراج معلومات الأعضاء
        rows = driver.find_elements(By.CSS_SELECTOR, "table.stats tbody tr:not(.spacer)")
        online_players = []

        for row in rows:
            try:
                # استخراج اسم اللاعب
                username_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) a span")
                username = username_element.text.strip()
                
                # استخراج حالة السيرفر (أونلاين أو آخر ظهور)
                server_status_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(5)")
                server_status = server_status_element.text.strip()
                
                # استخراج حالة المنتدى (أونلاين أو آخر ظهور)
                forum_status_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(4)")
                forum_status = forum_status_element.text.strip()
                
                # إذا كان أونلاين في السيرفر أو المنتدى
                if "Online" in server_status or "Online" in forum_status:
                    online_players.append(username)
                    
                    # إضافة حالة المنتدى إذا كان أونلاين هناك فقط
                    if "Online" in forum_status and "Online" not in server_status:
                        online_players[-1] += " (في المنتدى)"
                    
            except Exception as e:
                print(f"حدث خطأ أثناء معالجة صف: {e}")
                continue

        return clan_name, total_members, online_players

    finally:
        driver.quit()

@tasks.loop(minutes=2)
async def update_clan_status():
    global status_message

    clan_name, total_members, online_players = scrape_clan_status()

    description = f"اسم الكلان: **{clan_name}**\n"
    description += f"عدد أعضاء الكلان: **{total_members}**\n"
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
