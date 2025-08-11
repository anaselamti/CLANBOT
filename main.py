import discord
from discord.ext import commands, tasks
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import os
import traceback
import asyncio
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from io import BytesIO
import random

# --- Discord Bot Settings ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Selenium Settings ---
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
CHROME_BINARY_PATH = "/usr/local/chrome-linux/chrome"
BASE_URL = "https://ffs.gg/statistics.php"
CLAN_URL = "https://ffs.gg/clans.php?clanid=2915"

# --- Database Simulation ---
player_stats_db = {}  # سيكون تخزين البيانات في الذاكرة، يمكن استبداله بقاعدة بيانات حقيقية
clan_challenges = {}
achievements = {}

# --- Helper Functions ---
def extract_between(text, start, end):
    try:
        return text.split(start)[1].split(end)[0].strip()
    except IndexError:
        return "Not found"

def setup_driver():
    options = webdriver.ChromeOptions()
    options.binary_location = CHROME_BINARY_PATH
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    service = Service(CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)

def create_stats_image(player_data):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    stats = {
        'Points': int(player_data['carball_points'].replace(',', '')),
        'Wins': int(player_data['winning_games'].replace(',', '')),
        'Goals': int(player_data['scored_goals'].replace(',', '')),
        'Assists': int(player_data['assists'].replace(',', '')),
        'Saves': int(player_data['saved_gk'].replace(',', ''))
    }
    
    colors = ['#FF5733', '#33FF57', '#3357FF', '#F333FF', '#FF33F3']
    bars = ax.bar(stats.keys(), stats.values(), color=colors)
    
    ax.set_title(f"{player_data['username']}'s Statistics", fontsize=16, pad=20)
    ax.set_ylabel('Count', fontsize=12)
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:,}',
                ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    plt.close()
    buf.seek(0)
    return buf

# --- Player Scraping Functions ---
def scrape_player(player_name):
    driver = setup_driver()
    
    try:
        driver.get(BASE_URL)
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

        # Store player stats for tracking
        today = datetime.now().date()
        if username not in player_stats_db:
            player_stats_db[username] = {
                'weekly_stats': {},
                'records': {
                    'goals_in_match': 0,
                    'saves_in_match': 0,
                    'highest_points': 0
                }
            }
        
        # Check for new records
        goals = int(scored_goals.replace(',', ''))
        saves = int(saved_gk.replace(',', ''))
        points = int(carball_points.replace(',', ''))
        
        if goals > player_stats_db[username]['records']['goals_in_match']:
            player_stats_db[username]['records']['goals_in_match'] = goals
            record_alert = f"🎉 New record! {username} achieved {goals} goals in a match!"
        else:
            record_alert = None
        
        # Store weekly stats
        if str(today) not in player_stats_db[username]['weekly_stats']:
            player_stats_db[username]['weekly_stats'][str(today)] = {
                'goals': goals,
                'wins': int(winning_games.replace(',', '')),
                'saves': saves,
                'points': points
            }

        result_data = {
            "username": username,
            "clan": clan,
            "country": country,
            "join_date": join_date,
            "carball_points": carball_points,
            "winning_games": winning_games,
            "scored_goals": scored_goals,
            "assists": assists,
            "saved_gk": saved_gk,
            "profile_url": profile_url,
            "record_alert": record_alert
        }

        return result_data

    except Exception as e:
        print(traceback.format_exc())
        return {"error": f"❌ An error occurred: {str(e)}"}

    finally:
        driver.quit()

def scrape_top_players(metric='points', limit=10):
    driver = setup_driver()
    
    try:
        driver.get(CLAN_URL)
        time.sleep(5)
        
        players = []
        rows = driver.find_elements(By.CSS_SELECTOR, "table.stats.clan tbody tr")
        
        for row in rows:
            try:
                name = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) a").text
                points = row.find_element(By.CSS_SELECTOR, "td:nth-child(3)").text
                wins = row.find_element(By.CSS_SELECTOR, "td:nth-child(4)").text
                goals = row.find_element(By.CSS_SELECTOR, "td:nth-child(5)").text
                assists = row.find_element(By.CSS_SELECTOR, "td:nth-child(6)").text
                saves = row.find_element(By.CSS_SELECTOR, "td:nth-child(7)").text
                
                players.append({
                    'name': name,
                    'points': int(points.replace(',', '')),
                    'wins': int(wins.replace(',', '')),
                    'goals': int(goals.replace(',', '')),
                    'assists': int(assists.replace(',', '')),
                    'saves': int(saves.replace(',', ''))
                })
            except:
                continue
        
        # Sort by selected metric
        if metric == 'points':
            players.sort(key=lambda x: x['points'], reverse=True)
        elif metric == 'goals':
            players.sort(key=lambda x: x['goals'], reverse=True)
        elif metric == 'saves':
            players.sort(key=lambda x: x['saves'], reverse=True)
        elif metric == 'wins':
            players.sort(key=lambda x: x['wins'], reverse=True)
        
        return players[:limit]
    
    finally:
        driver.quit()

# --- Clan Management Functions ---
def scrape_clan_status():
    driver = setup_driver()
    
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

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".wwClanInfo:nth-child(3) div b")))

        try:
            desc_element = driver.find_element(By.CSS_SELECTOR, "div[style*='color: rgba(255,255,255,0.5)']")
            clan_data["description"] = desc_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            members_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(3) div b")
            clan_data["members"] = members_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            wars_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(4) div b")
            clan_data["clan_wars"] = wars_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            ranked_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(5) div b")
            clan_data["ranked"] = ranked_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            unranked_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(6) div b")
            clan_data["unranked"] = unranked_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            win_ratio_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(7) div b")
            clan_data["win_ratio"] = win_ratio_element.text.strip()
        except NoSuchElementException:
            pass

        try:
            bank_element = driver.find_element(By.CSS_SELECTOR, ".wwClanInfo:nth-child(8) div b")
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
            pass

        return clan_data

    finally:
        driver.quit()

# --- Challenge System ---
def create_weekly_challenges():
    challenges = [
        {"name": "Goal Scorer", "target": 50, "metric": "goals", "reward": "🏆 Golden Boot"},
        {"name": "Wall of Defense", "target": 30, "metric": "saves", "reward": "🛡️ Defender Badge"},
        {"name": "Playmaker", "target": 25, "metric": "assists", "reward": "🎯 Playmaker Medal"},
        {"name": "Winner", "target": 15, "metric": "wins", "reward": "🏅 Winner Crown"}
    ]
    
    for challenge in challenges:
        clan_challenges[challenge['name']] = {
            "target": challenge['target'],
            "metric": challenge['metric'],
            "reward": challenge['reward'],
            "participants": {},
            "completed": []
        }

# --- Bot Commands ---
@bot.command(name="ffs")
async def ffs(ctx, player_name: str = None):
    if not player_name:
        await ctx.send("❌ Please provide the player name. Example: `!ffs anasmorocco`")
        return

    await ctx.send(f"🔍 Searching for player **{player_name}**... This may take a few seconds.")

    player_data = scrape_player(player_name)
    
    if "error" in player_data:
        await ctx.send(player_data["error"])
        return
    
    # Send graphical card
    image_buf = create_stats_image(player_data)
    file = discord.File(image_buf, filename="player_stats.png")
    
    embed = discord.Embed(
        title=f"🎮 {player_data['username']}'s Profile",
        color=0x00ff00
    )
    embed.add_field(name="👥 Clan", value=player_data['clan'], inline=True)
    embed.add_field(name="🌍 Country", value=player_data['country'], inline=True)
    embed.add_field(name="📅 Join Date", value=player_data['join_date'], inline=True)
    embed.add_field(name="🏆 CarBall Points", value=player_data['carball_points'], inline=True)
    embed.add_field(name="🎯 Wins", value=player_data['winning_games'], inline=True)
    embed.add_field(name="⚽ Goals", value=player_data['scored_goals'], inline=True)
    embed.add_field(name="🎖 Assists", value=player_data['assists'], inline=True)
    embed.add_field(name="🧤 Saves", value=player_data['saved_gk'], inline=True)
    embed.set_image(url="attachment://player_stats.png")
    embed.set_footer(text=f"🔗 Full Profile: {player_data['profile_url']}")
    
    await ctx.send(file=file, embed=embed)
    
    # Send record alert if any
    if player_data.get('record_alert'):
        await ctx.send(player_data['record_alert'])

@bot.command(name="top")
async def top_players(ctx, metric: str = "points"):
    valid_metrics = ['points', 'goals', 'saves', 'wins', 'assists']
    
    if metric not in valid_metrics:
        await ctx.send(f"❌ Invalid metric. Please use one of: {', '.join(valid_metrics)}")
        return
    
    await ctx.send(f"🏆 Fetching top 10 players by {metric}...")
    
    top_players = scrape_top_players(metric)
    
    if not top_players:
        await ctx.send("❌ Could not retrieve top players list.")
        return
    
    embed = discord.Embed(
        title=f"🏅 Top 10 Players by {metric.capitalize()}",
        color=0xffd700
    )
    
    for i, player in enumerate(top_players, 1):
        embed.add_field(
            name=f"{i}. {player['name']}",
            value=f"{metric.capitalize()}: {player[metric]:,}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name="compare")
async def compare_players(ctx, player1: str, player2: str):
    await ctx.send(f"⚖️ Comparing **{player1}** and **{player2}**...")
    
    p1_data = scrape_player(player1)
    p2_data = scrape_player(player2)
    
    if "error" in p1_data or "error" in p2_data:
        await ctx.send("❌ Could not retrieve data for one or both players.")
        return
    
    embed = discord.Embed(
        title=f"⚔️ {p1_data['username']} vs {p2_data['username']}",
        color=0x7289da
    )
    
    # Compare stats
    stats_to_compare = [
        ('carball_points', '🏆 Points'),
        ('winning_games', '🎯 Wins'),
        ('scored_goals', '⚽ Goals'),
        ('assists', '🎖 Assists'),
        ('saved_gk', '🧤 Saves')
    ]
    
    for stat, label in stats_to_compare:
        p1_val = int(p1_data[stat].replace(',', ''))
        p2_val = int(p2_data[stat].replace(',', ''))
        
        if p1_val > p2_val:
            winner = f"**{p1_data['username']}** leads"
        elif p2_val > p1_val:
            winner = f"**{p2_data['username']}** leads"
        else:
            winner = "Tie"
            
        embed.add_field(
            name=label,
            value=f"{p1_data['username']}: {p1_val:,}\n{p2_data['username']}: {p2_val:,}\n{winner}",
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command(name="progress")
async def player_progress(ctx, player_name: str = None):
    if not player_name:
        await ctx.send("❌ Please provide the player name. Example: `!progress anasmorocco`")
        return
    
    if player_name not in player_stats_db:
        await ctx.send("ℹ️ No historical data available for this player yet.")
        return
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    current_week = {k: v for k, v in player_stats_db[player_name]['weekly_stats'].items() 
                   if datetime.strptime(k, "%Y-%m-%d").date() >= week_ago}
    last_week = {k: v for k, v in player_stats_db[player_name]['weekly_stats'].items() 
                if datetime.strptime(k, "%Y-%m-%d").date() < week_ago 
                and datetime.strptime(k, "%Y-%m-%d").date() >= week_ago - timedelta(days=7)}
    
    if not current_week or not last_week:
        await ctx.send("ℹ️ Not enough data to show progress.")
        return
    
    # Calculate totals
    current_totals = {
        'goals': sum(day['goals'] for day in current_week.values()),
        'wins': sum(day['wins'] for day in current_week.values()),
        'saves': sum(day['saves'] for day in current_week.values()),
        'points': sum(day['points'] for day in current_week.values())
    }
    
    last_totals = {
        'goals': sum(day['goals'] for day in last_week.values()),
        'wins': sum(day['wins'] for day in last_week.values()),
        'saves': sum(day['saves'] for day in last_week.values()),
        'points': sum(day['points'] for day in last_week.values())
    }
    
    # Calculate progress
    progress = {
        'goals': current_totals['goals'] - last_totals['goals'],
        'wins': current_totals['wins'] - last_totals['wins'],
        'saves': current_totals['saves'] - last_totals['saves'],
        'points': current_totals['points'] - last_totals['points']
    }
    
    embed = discord.Embed(
        title=f"📈 {player_name}'s Weekly Progress",
        description="Comparison with last week",
        color=0x3498db
    )
    
    for stat in ['goals', 'wins', 'saves', 'points']:
        diff = progress[stat]
        if diff > 0:
            emoji = "📈"
            status = f"+{diff} (Improving)"
        elif diff < 0:
            emoji = "📉"
            status = f"{diff} (Declining)"
        else:
            emoji = "➖"
            status = "No change"
            
        embed.add_field(
            name=f"{emoji} {stat.capitalize()}",
            value=f"This week: {current_totals[stat]}\nLast week: {last_totals[stat]}\n{status}",
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command(name="challenges")
async def show_challenges(ctx):
    if not clan_challenges:
        create_weekly_challenges()
    
    embed = discord.Embed(
        title="🏅 Weekly Clan Challenges",
        description="Complete these challenges to earn rewards!",
        color=0xe67e22
    )
    
    for name, challenge in clan_challenges.items():
        embed.add_field(
            name=f"🎯 {name}",
            value=f"Target: {challenge['target']} {challenge['metric']}\nReward: {challenge['reward']}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name="join_challenge")
async def join_challenge(ctx, challenge_name: str = None):
    if not challenge_name:
        await ctx.send("❌ Please specify a challenge name. Use `!challenges` to see available challenges.")
        return
    
    if challenge_name not in clan_challenges:
        await ctx.send("❌ Challenge not found. Use `!challenges` to see available challenges.")
        return
    
    player_name = ctx.author.name
    clan_challenges[challenge_name]['participants'][player_name] = 0
    await ctx.send(f"✅ {player_name} has joined the {challenge_name} challenge!")

@bot.command(name="clan")
async def clan_status(ctx):
    clan_data = scrape_clan_status()
    
    online_count = len(clan_data["online_players"])
    members_count = clan_data["members"]
    online_list = ", ".join(clan_data["online_players"]) if online_count > 0 else "No players online"
    
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
        name=f"👤 Online Members ({online_count}/{members_count})",
        value=online_list,
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name="records")
async def player_records(ctx, player_name: str = None):
    if not player_name:
        player_name = ctx.author.name
    
    if player_name not in player_stats_db:
        await ctx.send("ℹ️ No records found for this player.")
        return
    
    records = player_stats_db[player_name]['records']
    
    embed = discord.Embed(
        title=f"🏆 {player_name}'s Records",
        color=0x9b59b6
    )
    embed.add_field(name="⚽ Most Goals in a Match", value=records['goals_in_match'], inline=True)
    embed.add_field(name="🧤 Most Saves in a Match", value=records['saves_in_match'], inline=True)
    embed.add_field(name="🏅 Highest Points", value=records['highest_points'], inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="help_bot")
async def help_command(ctx):
    embed = discord.Embed(
        title="🤖 FFS.gg Bot Help",
        description="Here are all available commands:",
        color=0x3498db
    )
    
    commands = [
        ("!ffs [player]", "Get player statistics with graphical card"),
        ("!top [metric]", "Show top players by points/goals/saves/wins"),
        ("!compare [player1] [player2]", "Compare two players' stats"),
        ("!progress [player]", "Show weekly progress compared to last week"),
        ("!challenges", "Show current weekly challenges"),
        ("!join_challenge [name]", "Join a weekly challenge"),
        ("!clan", "Show clan status and online members"),
        ("!records [player]", "Show player records"),
        ("!help_bot", "Show this help message")
    ]
    
    for cmd, desc in commands:
        embed.add_field(name=cmd, value=desc, inline=False)
    
    await ctx.send(embed=embed)

# --- Background Tasks ---
@tasks.loop(hours=12)
async def update_clan_status():
    channel = bot.get_channel(1404474899564597308)  # Your clan channel ID
    if channel:
        clan_data = scrape_clan_status()
        
        online_count = len(clan_data["online_players"])
        members_count = clan_data["members"]
        online_list = ", ".join(clan_data["online_players"]) if online_count > 0 else "No players online"
        
        embed = discord.Embed(
            title=f"🛡️ {clan_data['name']} [{clan_data['tag']}] Status Update",
            color=0xdaa520
        )
        embed.add_field(name="👥 Members Online", value=f"{online_count}/{members_count}", inline=True)
        embed.add_field(name="💰 Clan Bank", value=clan_data["bank"], inline=True)
        embed.add_field(name="🏆 Ranked Record", value=clan_data["ranked"], inline=True)
        embed.add_field(name="🌐 Online Players", value=online_list, inline=False)
        
        await channel.send(embed=embed)

@tasks.loop(hours=24)
async def check_challenge_progress():
    # This would check player progress in challenges and update accordingly
    pass

@tasks.loop(hours=168)  # Weekly
async def reset_challenges():
    create_weekly_challenges()
    channel = bot.get_channel(1404474899564597308)  # Your clan channel ID
    if channel:
        await channel.send("🔄 Weekly challenges have been reset! Use `!challenges` to see the new challenges.")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    
    # Start background tasks
    update_clan_status.start()
    check_challenge_progress.start()
    reset_challenges.start()
    
    # Create initial challenges if none exist
    if not clan_challenges:
        create_weekly_challenges()

# Run the bot
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
