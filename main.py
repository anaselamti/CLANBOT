import discord
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import traceback

chromedriver_path = "/usr/local/bin/chromedriver"
chrome_binary_path = "/usr/local/chrome-linux/chrome"  # هذا هو المسار الصحيح للكروم بعد التعديل في Dockerfile
base_url = "https://ffs.gg/statistics.php"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

def extract_between(text, start, end):
    try:
        return text.split(start)[1].split(end)[0].strip()
    except IndexError:
        return "Not found"

def scrape_player(player_name):
    options = webdriver.ChromeOptions()
    options.binary_location = chrome_binary_path
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(base_url)
        search_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.searchField"))
        )
        search_field.send_keys(player_name)
        search_field.send_keys(Keys.RETURN)
        time.sleep(3)

        row = driver.find_element(By.CSS_SELECTOR, "table.stats tbody tr")
        profile_link = row.find_element(By.CSS_SELECTOR, "td a").get_attribute("href")

        if "member.php" in profile_link:
            user_id = profile_link.split("u=")[1].split("&")[0]
            profile_url = f"https://ffs.gg/members/{user_id}-{player_name}"
        else:
            profile_url = profile_link.replace("member.php", "members")

        driver.get(profile_url)
        time.sleep(5)

        try:
            clan_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//div[contains(@class,'ww_box') and contains(@class,'profileStats')]//div[contains(text(),'Clan')]/span/b/a"
                ))
            )
            clan = clan_element.text.strip()
        except:
            clan = "Unknown"

        #if clan != "Real Madrid FC":
         #   return "⚠️ Sorry, this player is not part of the clan Real Madrid FC. You must be a member of this clan to use the bot."

        body_text = driver.find_element(By.TAG_NAME, "body").text

        username = extract_between(body_text, "Member List", "Log in").split()[-1]
        nickname = extract_between(body_text, "Name", "Clan")
        join_date = extract_between(body_text, "last seen", "join date")
        country = extract_between(body_text, "Country", "Last Visit")
        carball_points = extract_between(body_text, "CarBall", "Won").split()[0]
        winning_games = extract_between(body_text, "Won:", "|").split()[0]
        scored_goals = extract_between(body_text, "Goals:", "|").split()[0]
        assists = extract_between(body_text, "Assists:", "Saves").split()[0]
        saved_gk = extract_between(body_text, "Saves:", "|").split()[0]

        result_text = (
            f"🎮 **Player Profile: {username}**\n"
            f"👥 Clan: {clan}\n"
            f"🌍 Country: {country}\n"
            f"📅 Join Date: {join_date}\n"
            f"🏆 CarBall Points: {carball_points}\n"
            f"🎯 Wins: {winning_games}\n"
            f"⚽ Goals: {scored_goals}\n"
            f"🎖 Assists: {assists}\n"
            f"🧤 Saves: {saved_gk}\n"
            f"🔗 [Full Profile]({profile_url})"
        )

        return result_text

    except Exception as e:
        print(traceback.format_exc())
        return f"❌ An error occurred: {str(e)}"

    finally:
        driver.quit()

@bot.command(name="ffs")
async def ffs(ctx, player_name: str = None, arena: str = None):
    if not player_name:
        await ctx.send("❌ Please provide the player name. Example: `!ffs anasmorocco cb`")
        return

    await ctx.send(f"🔍 Searching for player **{player_name}**... This may take a few seconds.")

    result = scrape_player(player_name)
    await ctx.send(result)

@bot.command(name="info")
async def info(ctx):
    await ctx.send("Use `!ffs <player_name> <mode>` to get player stats. Example: `!ffs anasmorocco cb`")

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
