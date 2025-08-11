import discord
from discord.ext import commands, tasks
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
import os

CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
CHROME_BINARY_PATH = "/usr/local/chrome-linux/chrome"

CLAN_URL = "https://ffs.gg/clans.php?clanid=2915"
TARGET_CHANNEL_ID = 1404443185048064011

intents = discord.Intents.default()
intents.message_content = True  # مهم تفعيل هذا لكي يستطيع البوت قراءة الرسائل إذا احتاج

bot = commands.Bot(command_prefix="!", intents=intents)

status_message = None  # لتعريفها على مستوى الملف

def scrape_clan_status():
    options = webdriver.ChromeOptions()
    options.binary_location = CHROME_BINARY_PATH
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(CLAN_URL)
        time.sleep(5)  # زيادة الوقت أحياناً ضروري لصفحات ثقيلة

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

        # بعض العناصر قد لا تظهر دائماً لذا نستخدم try-except

        try:
            clan_name_element = driver.find_element(By.XPATH, "//span[contains(@style,'color: rgb(185,164,94)') and contains(@style,'font-size: 20px')]/b")
            clan_data["name"] = clan_name_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            description_element = driver.find_element(By.XPATH, "//span[contains(@style,'color: rgba(255,255,255,0.5)')]")
            clan_data["description"] = description_element.text.strip()
            # البحث عن رابط ديسكورد في الوصف
            if "discord.gg/" in clan_data["description"]:
                start = clan_data["description"].find("https://discord.gg/")
                if start != -1:
                    end = clan_data["description"].find(" ", start)
                    clan_data["discord"] = clan_data["description"][start:end if end != -1 else None].strip()
        except NoSuchElementException:
            pass

        try:
            clan_tag_element = driver.find_element(By.XPATH, "//span[contains(@style,'color: rgb(185,164,94)') and contains(@style,'text-shadow')]")
            clan_data["tag"] = clan_tag_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            members_element = driver.find_element(By.XPATH, "//div[contains(text(),'members')]/div/b")
            clan_data["members"] = members_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            wars_element = driver.find_element(By.XPATH, "//div[contains(text(),'clan wars')]/div/b")
            clan_data["clan_wars"] = wars_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            ranked_element = driver.find_element(By.XPATH, "//div[contains(text(),'ranked')]/div/b")
            clan_data["ranked"] = ranked_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            unranked_element = driver.find_element(By.XPATH, "//div[contains(text(),'unranked')]/div/b")
            clan_data["unranked"] = unranked_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            win_ratio_element = driver.find_element(By.XPATH, "//div[contains(text(),'win ratio')]/div/b")
            clan_data["win_ratio"] = win_ratio_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            bank_element = driver.find_element(By.XPATH, "//div[contains(text(),'bank')]/div/b")
            clan_data["bank"] = bank_element.text.strip()
        except NoSuchElementException:
            pass

        # استخراج اللاعبين الأونلاين
        try:
            rows = driver.find_elements(By.CSS_SELECTOR, "table.stats tbody tr:not(.spacer)")
            for row in rows:
                try:
                    username_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) a span")
                    username = username_element.text.strip()
                    server_status_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(5)")
                    server_status = server_status_element.text.strip().lower()
                    if "online" in server_status or "in-game" in server_status:
                        clan_data["online_players"].append(username)
                except Exception:
                    continue
        except NoSuchElementException:
            pass

        return clan_data
    except Exception as e:
        print(f"❌ خطأ في جلب بيانات الكلان: {e}")
        return None
    finally:
        driver.quit()

@tasks.loop(minutes=2)
async def update_clan_status():
    global status_message
    clan_data = scrape_clan_status()
    if not clan_data:
        print("❌ لم أتمكن من جلب بيانات الكلان.")
        return

    embed = discord.Embed(
        title=f"🛡️ {clan_data['name']} [{clan_data['tag']}]",
        description=f"📜 **الوصف:**\n{clan_data['description']}\n\n"
                    f"🔗 **رابط الديسكورد:** {clan_data['discord']}",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="📊 إحصائيات الكلان",
        value=(
            f"👥 **الأعضاء:** {clan_data['members']}\n"
            f"⚔️ **حروب الكلان:** {clan_data['clan_wars']}\n"
            f"🏆 **الرانكد:** {clan_data['ranked']}\n"
            f"🔓 **الأنرانكد:** {clan_data['unranked']}\n"
            f"📈 **نسبة الفوز:** {clan_data['win_ratio']}\n"
            f"💰 **رصيد البنك:** {clan_data['bank']}"
        ),
        inline=True
    )

    online_count = len(clan_data['online_players'])
    total_members = clan_data['members']

    embed.add_field(
        name=f"👤 حالة الأعضاء ({online_count}/{total_members})",
        value="\n".join(f"- {player}" for player in clan_data['online_players']) if online_count > 0 else "لا يوجد لاعبون أونلاين حالياً.",
        inline=False
    )

    embed.set_thumbnail(url="https://i.imgur.com/J1wY8Kp.png")

    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if not channel:
        print("❌ لم أتمكن من العثور على الروم المحدد.")
        return

    try:
        if status_message:
            await status_message.edit(embed=embed)
        else:
            status_message = await channel.send(embed=embed)
    except discord.NotFound:
        # في حالة تم حذف الرسالة القديمة، نرسل رسالة جديدة
        status_message = await channel.send(embed=embed)

@bot.event
async def on_ready():
    global status_message
    print(f"✅ تم تسجيل الدخول باسم {bot.user}")
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel:
        status_message = await channel.send("⏳ جاري تحميل بيانات الكلان...")
    update_clan_status.start()

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
