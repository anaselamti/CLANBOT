import discord
from discord.ext import commands, tasks
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
import os

# إعدادات مسارات كروم وكروم درايفر
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
CHROME_BINARY_PATH = "/usr/local/chrome-linux/chrome"

CLAN_URL = "https://ffs.gg/clans.php?clanid=2915"
TARGET_CHANNEL_ID = 1404443185048064011

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
    options.add_argument("--window-size=1920,1080")
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(CLAN_URL)
        time.sleep(5)  # زيادة وقت الانتظار لتحميل الصفحة

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
            # استخراج اسم الكلان
            clan_name_element = driver.find_element(By.XPATH, "//span[contains(@style, 'color: rgb(185,164,94)') and contains(@style, 'font-size: 20px')]/b")
            clan_data["name"] = clan_name_element.text.strip()
        except NoSuchElementException:
            print("⚠️ لم يتم العثور على اسم الكلان")

        try:
            # استخراج وصف الكلان
            description_element = driver.find_element(By.XPATH, "//span[contains(@style, 'color: rgba(255,255,255,0.5)')]")
            clan_data["description"] = description_element.text.strip()
            
            # استخراج رابط الديسكورد من الوصف إذا وجد
            if "discord.gg/" in clan_data["description"]:
                start = clan_data["description"].find("https://discord.gg/")
                if start != -1:
                    end = clan_data["description"].find(" ", start)
                    clan_data["discord"] = clan_data["description"][start:end if end != -1 else None].strip()
        except NoSuchElementException:
            print("⚠️ لم يتم العثور على وصف الكلان")

        try:
            # استخراج تاج الكلان
            clan_tag_element = driver.find_element(By.XPATH, "//span[contains(@style, 'color: rgb(185,164,94)') and contains(@style, 'text-shadow')]")
            clan_data["tag"] = clan_tag_element.text.strip()
        except NoSuchElementException:
            print("⚠️ لم يتم العثور على تاج الكلان")

        try:
            # استخراج عدد الأعضاء
            members_element = driver.find_element(By.XPATH, "//div[contains(., 'members')]/div/b")
            clan_data["members"] = members_element.text.strip()
        except NoSuchElementException:
            print("⚠️ لم يتم العثور على عدد الأعضاء")

        try:
            # استخراج عدد حروب الكلان
            wars_element = driver.find_element(By.XPATH, "//div[contains(., 'clan wars')]/div/b")
            clan_data["clan_wars"] = wars_element.text.strip()
        except NoSuchElementException:
            print("⚠️ لم يتم العثور على عدد حروب الكلان")

        try:
            # استخراج حالة الرانكد
            ranked_element = driver.find_element(By.XPATH, "//div[contains(., 'ranked')]/div/b")
            clan_data["ranked"] = ranked_element.text.strip()
        except NoSuchElementException:
            print("⚠️ لم يتم العثور على حالة الرانكد")

        try:
            # استخراج حالة الأنرانكد
            unranked_element = driver.find_element(By.XPATH, "//div[contains(., 'unranked')]/div/b")
            clan_data["unranked"] = unranked_element.text.strip()
        except NoSuchElementException:
            print("⚠️ لم يتم العثور على حالة الأنرانكد")

        try:
            # استخراج نسبة الفوز
            win_ratio_element = driver.find_element(By.XPATH, "//div[contains(., 'win ratio')]/div/b")
            clan_data["win_ratio"] = win_ratio_element.text.strip()
        except NoSuchElementException:
            print("⚠️ لم يتم العثور على نسبة الفوز")

        try:
            # استخراج رصيد البنك
            bank_element = driver.find_element(By.XPATH, "//div[contains(., 'bank')]/div/b")
            clan_data["bank"] = bank_element.text.strip()
        except NoSuchElementException:
            print("⚠️ لم يتم العثور على رصيد البنك")

        try:
            # استخراج معلومات الأعضاء من الجدول
            rows = driver.find_elements(By.CSS_SELECTOR, "table.stats tbody tr:not(.spacer)")
            
            for row in rows:
                try:
                    # استخراج اسم اللاعب
                    username_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) a span")
                    username = username_element.text.strip()
                    
                    # استخراج حالة السيرفر
                    server_status_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(5)")
                    server_status = server_status_element.text.strip()
                    
                    # التحقق من حالة الأونلاين
                    if "Online" in server_status:
                        clan_data["online_players"].append(username)
                        
                except NoSuchElementException:
                    continue
                except Exception as e:
                    print(f"⚠️ خطأ في معالجة صف اللاعب: {e}")
                    continue
                    
        except NoSuchElementException:
            print("⚠️ لم يتم العثور على جدول الأعضاء")

        return clan_data

    except Exception as e:
        print(f"❌ حدث خطأ جسيم أثناء جلب البيانات: {e}")
        return {
            "name": "خطأ في جلب البيانات",
            "description": "N/A",
            "tag": "N/A",
            "members": "0",
            "clan_wars": "0",
            "ranked": "N/A",
            "unranked": "0",
            "win_ratio": "0%",
            "bank": "$0",
            "discord": "N/A",
            "online_players": []
        }
    finally:
        driver.quit()

@tasks.loop(minutes=2)
async def update_clan_status():
    global status_message

    try:
        clan_data = scrape_clan_status()

        # إنشاء وصف الرسالة
        embed = discord.Embed(
            title=f"🛡️ {clan_data['name']} [{clan_data['tag']}]",
            description=f"📜 **الوصف:**\n{clan_data['description']}\n\n"
                      f"🔗 **رابط الديسكورد:** {clan_data['discord']}",
            color=discord.Color.gold()
        )
        
        # إضافة معلومات الكلان
        embed.add_field(
            name="📊 إحصائيات الكلان",
            value=f"👥 **الأعضاء:** {clan_data['members']}\n"
                 f"⚔️ **حروب الكلان:** {clan_data['clan_wars']}\n"
                 f"🏆 **الرانكد:** {clan_data['ranked']}\n"
                 f"🔓 **الأنرانكد:** {clan_data['unranked']}\n"
                 f"📈 **نسبة الفوز:** {clan_data['win_ratio']}\n"
                 f"💰 **رصيد البنك:** {clan_data['bank']}",
            inline=True
        )
        
        # إضافة اللاعبين الأونلاين
        online_status = "🟢 **اللاعبون الأونلاين:**\n"
        if clan_data['online_players']:
            online_status += "\n".join(f"- {player}" for player in clan_data['online_players'])
        else:
            online_status += "لا يوجد لاعبون أونلاين حالياً."
            
        embed.add_field(
            name=f"👤 حالة الأعضاء ({len(clan_data['online_players']}/{clan_data['members']})",
            value=online_status,
            inline=True
        )

        # إضافة صورة مصغرة إذا وجدت
        embed.set_thumbnail(url="https://i.imgur.com/J1wY8Kp.png")

        channel = bot.get_channel(TARGET_CHANNEL_ID)
        if not channel:
            print("❌ لم يتم العثور على الروم المحدد")
            return

        if status_message:
            try:
                await status_message.edit(embed=embed)
            except discord.NotFound:
                status_message = await channel.send(embed=embed)
        else:
            status_message = await channel.send(embed=embed)

    except Exception as e:
        print(f"❌ حدث خطأ أثناء تحديث الحالة: {e}")

@bot.event
async def on_ready():
    global status_message
    print(f"✅ تم تسجيل الدخول باسم {bot.user}")
    
    # إضافة intent لقراءة محتوى الرسائل
    intents.message_content = True
    
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel:
        try:
            status_message = await channel.send("⏳ جاري تحميل بيانات الكلان...")
            update_clan_status.start()
        except Exception as e:
            print(f"❌ حدث خطأ أثناء الإرسال الأولي: {e}")

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
