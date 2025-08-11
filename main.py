import discord
from discord.ext import commands
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import asyncio
import time

# إعدادات Selenium
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"  # عدل حسب مسار كروم درايفر عندك
CHROME_BINARY_PATH = "/usr/local/chrome-linux/chrome"  # عدل حسب مسار كروم عندك
CLAN_URL = "https://ffs.gg/clans.php?clanid=2915"  # رابط الكلان

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
        time.sleep(7)  # انتظر تحميل الصفحة

        # استخراج البيانات
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

# إعدادات بوت الديسكورد مع intents
intents = discord.Intents.default()
intents.members = True  # إذا تحتاج معلومات الأعضاء

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ تم تسجيل الدخول كـ: {bot.user}")

# أمر !clan لجلب وعرض بيانات الكلان
@bot.command()
async def clan(ctx):
    await ctx.send("⏳ جارٍ جلب بيانات الكلان، الرجاء الانتظار...")
    loop = asyncio.get_event_loop()
    clan_data = await loop.run_in_executor(None, scrape_clan_status)  # تشغيل الدالة في Thread منفصل لأن Selenium blocking

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

    await ctx.send(embed=embed)

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ خطأ: لم يتم تعيين توكن البوت في متغير البيئة DISCORD_BOT_TOKEN")
    else:
        bot.run(token)
