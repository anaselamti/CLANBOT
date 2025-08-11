import discord
from discord.ext import commands, tasks
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import asyncio
import traceback
import os
import time
import aiosqlite
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import io

# --- إعدادات Chrome و Selenium ---
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
CHROME_BINARY_PATH = "/usr/local/chrome-linux/chrome"  
BASE_URL = "https://ffs.gg/statistics.php"

# --- إعدادات Discord ---
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
INTENTS = discord.Intents.default()
INTENTS.message_content = True
bot = commands.Bot(command_prefix="!", intents=INTENTS)

# --- إعداد قاعدة البيانات SQLite ---
DB_PATH = "ffs_bot_data.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS player_stats (
                player_name TEXT,
                date TEXT,
                points INTEGER,
                goals INTEGER,
                assists INTEGER,
                saves INTEGER,
                wins INTEGER,
                PRIMARY KEY(player_name, date)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS records (
                player_name TEXT PRIMARY KEY,
                max_goals INTEGER,
                max_points INTEGER
            )
        """)
        await db.commit()

# --- دالة لجلب بيانات اللاعب من الموقع باستخدام Selenium ---
def scrape_player(player_name):
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

    def extract_between(text, start, end):
        try:
            return text.split(start)[1].split(end)[0].strip()
        except IndexError:
            return "Not found"

    try:
        driver.get(BASE_URL)
        search_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.searchField"))
        )
        search_field.send_keys(player_name)
        search_field.send_keys(Keys.RETURN)
        time.sleep(10)

        row = driver.find_element(By.CSS_SELECTOR, "table.stats tbody tr")
        profile_link = row.find_element(By.CSS_SELECTOR, "td a").get_attribute("href")

        if "member.php" in profile_link:
            user_id = profile_link.split("u=")[1].split("&")[0]
            profile_url = f"https://ffs.gg/members/{user_id}-{player_name}"
        else:
            profile_url = profile_link.replace("member.php", "members")

        driver.get(profile_url)
        time.sleep(10)

        body_text = driver.find_element(By.TAG_NAME, "body").text

        username = extract_between(body_text, "Member List", "Log in").split()[-1]
        clan = "Unknown"
        try:
            clan_element = driver.find_element(By.XPATH, "//div[contains(@class,'ww_box') and contains(@class,'profileStats')]//div[contains(text(),'Clan')]/span/b/a")
            clan = clan_element.text.strip()
        except:
            pass

        country = extract_between(body_text, "Country", "Last Visit")
        carball_points = int(extract_between(body_text, "CarBall", "Won").split()[0])
        winning_games = int(extract_between(body_text, "Won:", "|").split()[0])
        scored_goals = int(extract_between(body_text, "Goals:", "|").split()[0])
        assists = int(extract_between(body_text, "Assists:", "Saves").split()[0])
        saved_gk = int(extract_between(body_text, "Saves:", "|").split()[0])

        return {
            "username": username,
            "clan": clan,
            "country": country,
            "points": carball_points,
            "wins": winning_games,
            "goals": scored_goals,
            "assists": assists,
            "saves": saved_gk,
            "profile_url": profile_url
        }
    except Exception as e:
        print(traceback.format_exc())
        return None
    finally:
        driver.quit()

# --- دالة لحفظ البيانات في قاعدة البيانات ---
async def save_player_stats(data):
    async with aiosqlite.connect(DB_PATH) as db:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        await db.execute("""
            INSERT OR REPLACE INTO player_stats (player_name, date, points, goals, assists, saves, wins)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (data["username"], today, data["points"], data["goals"], data["assists"], data["saves"], data["wins"]))
        await db.commit()

# --- دالة لتحليل التقدم الأسبوعي ---
async def get_weekly_progress(player_name):
    async with aiosqlite.connect(DB_PATH) as db:
        today = datetime.utcnow().date()
        this_week = today - timedelta(days=today.weekday())  # بداية الأسبوع الحالي (الاثنين)
        last_week = this_week - timedelta(days=7)

        async def get_stats(date):
            cursor = await db.execute("SELECT points, goals, assists, saves, wins FROM player_stats WHERE player_name=? AND date=?", (player_name, date.strftime("%Y-%m-%d")))
            row = await cursor.fetchone()
            return row

        current_stats = await get_stats(this_week)
        last_stats = await get_stats(last_week)

        if not current_stats or not last_stats:
            return None

        diff = tuple(c - l for c, l in zip(current_stats, last_stats))
        return {
            "points_diff": diff[0],
            "goals_diff": diff[1],
            "assists_diff": diff[2],
            "saves_diff": diff[3],
            "wins_diff": diff[4],
            "current": current_stats,
            "last": last_stats
        }

# --- دالة التحقق من الأرقام القياسية وإرسال تهنئة ---
async def check_records_and_congratulate(channel, data):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT max_goals, max_points FROM records WHERE player_name=?", (data["username"],))
        row = await cursor.fetchone()
        if row:
            max_goals, max_points = row
        else:
            max_goals, max_points = 0, 0

        congratulated = False
        if data["goals"] > max_goals:
            await db.execute("INSERT OR REPLACE INTO records (player_name, max_goals, max_points) VALUES (?, ?, ?)", (data["username"], data["goals"], max_points))
            congratulated = True
            await channel.send(f"🎉 تهانينا لـ **{data['username']}** لكسر الرقم القياسي لأكبر عدد أهداف: {data['goals']}!")

        if data["points"] > max_points:
            await db.execute("INSERT OR REPLACE INTO records (player_name, max_goals, max_points) VALUES (?, ?, ?)", (data["username"], max_goals, data["points"]))
            congratulated = True
            await channel.send(f"🏆 تهانينا لـ **{data['username']}** لكسر الرقم القياسي لأكبر نقاط CarBall: {data['points']}!")

        if congratulated:
            await db.commit()

# --- دالة إنشاء بطاقة صورة للاعب ---
def create_player_card(data):
    width, height = 600, 350
    background_color = (30, 30, 30)
    text_color = (255, 255, 255)
    accent_color = (218, 165, 32)  # ذهبي

    img = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(img)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # تأكد من توفر الخط أو عدله لمسار خط مناسب
    font_large = ImageFont.truetype(font_path, 30)
    font_medium = ImageFont.truetype(font_path, 20)
    font_small = ImageFont.truetype(font_path, 16)

    draw.text((20, 20), f"Player: {data['username']}", fill=accent_color, font=font_large)
    draw.text((20, 60), f"Clan: {data['clan']}", fill=text_color, font=font_medium)
    draw.text((20, 90), f"Country: {data['country']}", fill=text_color, font=font_medium)
    draw.text((20, 130), f"CarBall Points: {data['points']}", fill=accent_color, font=font_medium)
    draw.text((20, 160), f"Wins: {data['wins']}", fill=text_color, font=font_medium)
    draw.text((20, 190), f"Goals: {data['goals']}", fill=text_color, font=font_medium)
    draw.text((20, 220), f"Assists: {data['assists']}", fill=text_color, font=font_medium)
    draw.text((20, 250), f"Saves: {data['saves']}", fill=text_color, font=font_medium)

    # رابط البروفايل
    draw.text((20, 290), f"Profile: {data['profile_url']}", fill=accent_color, font=font_small)

    with io.BytesIO() as image_binary:
        img.save(image_binary, 'PNG')
        image_binary.seek(0)
        return image_binary

# --- أمر جلب بيانات اللاعب ---
@bot.command(name="ffs")
async def ffs(ctx, player_name: str = None):
    if not player_name:
        await ctx.send("❌ الرجاء إدخال اسم اللاعب. مثال: `!ffs anasmorocco`")
        return
    await ctx.send(f"🔍 جاري البحث عن اللاعب **{player_name}**... يرجى الانتظار.")
    data = await asyncio.to_thread(scrape_player, player_name)
    if not data:
        await ctx.send("❌ لم أتمكن من العثور على بيانات اللاعب أو حدث خطأ.")
        return
    # حفظ البيانات
    await save_player_stats(data)
    # التحقق من الأرقام القياسية
    await check_records_and_congratulate(ctx.channel, data)
    # إنشاء البطاقة وإرسالها
    image_binary = create_player_card(data)
    file = discord.File(fp=image_binary, filename="player_card.png")
    await ctx.send(file=file)

# --- أمر عرض أفضل اللاعبين ---
@bot.command(name="top")
async def top(ctx, stat: str = "points"):
    valid_stats = ["points", "goals", "assists", "saves", "wins"]
    if stat not in valid_stats:
        await ctx.send(f"❌ اختر إحصائية صحيحة من: {', '.join(valid_stats)}")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        # آخر تاريخ متوفر
        cursor = await db.execute("SELECT DISTINCT date FROM player_stats ORDER BY date DESC LIMIT 1")
        row = await cursor.fetchone()
        if not row:
            await ctx.send("❌ لا توجد بيانات حالياً.")
            return
        last_date = row[0]

        cursor = await db.execute(f"""
            SELECT player_name, {stat} FROM player_stats
            WHERE date=?
            ORDER BY {stat} DESC
            LIMIT 5
        """, (last_date,))
        rows = await cursor.fetchall()
        if not rows:
            await ctx.send("❌ لا توجد بيانات لعرضها.")
            return

        msg = f"🏆 أفضل 5 لاعبين حسب {stat} (تاريخ {last_date}):\n"
        for i, (player, value) in enumerate(rows, 1):
            msg += f"{i}. {player} - {value}\n"
        await ctx.send(msg)

# --- أمر تقرير التقدم الأسبوعي ---
@bot.command(name="progress")
async def progress(ctx, player_name: str = None):
    if not player_name:
        await ctx.send("❌ الرجاء إدخال اسم اللاعب. مثال: `!progress anasmorocco`")
        return
    progress = await get_weekly_progress(player_name)
    if not progress:
        await ctx.send("❌ لا توجد بيانات كافية لتقرير التقدم لهذا اللاعب.")
        return
    msg = (
        f"📊 تقرير التقدم الأسبوعي لـ **{player_name}**:\n"
        f"النقاط: +{progress['points_diff']}\n"
        f"الأهداف: +{progress['goals_diff']}\n"
        f"التمريرات الحاسمة: +{progress['assists_diff']}\n"
        f"التصديات: +{progress['saves_diff']}\n"
        f"الأنتصارات: +{progress['wins_diff']}"
    )
    await ctx.send(msg)

# --- أمر مقارنة بين لاعبين ---
@bot.command(name="compare")
async def compare(ctx, player1: str = None, player2: str = None):
    if not player1 or not player2:
        await ctx.send("❌ الرجاء إدخال اسمي لاعبين. مثال: `!compare Wassym Player`")
        return
    await ctx.send(f"🔍 جاري مقارنة **{player1}** و **{player2}** ...")
    data1 = await asyncio.to_thread(scrape_player, player1)
    data2 = await asyncio.to_thread(scrape_player, player2)
    if not data1 or not data2:
        await ctx.send("❌ لم أتمكن من جلب بيانات أحد اللاعبين.")
        return
    msg = (
        f"⚔️ مقارنة بين **{data1['username']}** و **{data2['username']}**:\n"
        f"النقاط: {data1['points']} - {data2['points']}\n"
        f"الأهداف: {data1['goals']} - {data2['goals']}\n"
        f"التمريرات الحاسمة: {data1['assists']} - {data2['assists']}\n"
        f"التصديات: {data1['saves']} - {data2['saves']}\n"
        f"الأنتصارات: {data1['wins']} - {data2['wins']}\n"
    )
    await ctx.send(msg)

# --- مهمة تحديث دورية لجلب بيانات يومية لأكثر اللاعبين استخدامًا (تطوير لاحق) ---
# يمكن تطويرها لتحديث بيانات الكلان مثلا

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await init_db()
    print("Database initialized.")
    # يمكنك هنا تشغيل مهام دورية إذا أردت، مثل تحديث الكلان
    # start_your_task.start()

bot.run(DISCORD_BOT_TOKEN)
