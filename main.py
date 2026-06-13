import os
import discord
from discord.ext import commands, tasks
import db

# ---------------- CONFIG ----------------

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "<YOUR_DISCORD_BOT_TOKEN>")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "1491435881733558374"))

ROLE_MAP = {
    1: 1515290650000000000,  # Visitor
    2: 1515290700000000000,  # Newcomer
    3: 1509940190725279834,  # Member
    4: 1515290501878775909,  # Regular
    5: 1515290564541550733,  # Veteran
    6: 1515290613812166727,  # Elite
}

# ---------------- DISCORD SETUP ----------------

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

db.init_db()

# ---------------- LOGIC ----------------

async def sync_member_roles(member: discord.Member, new_level: int):
    guild = member.guild

    new_role_id = ROLE_MAP.get(new_level)
    if not new_role_id:
        return

    new_role = guild.get_role(new_role_id)
    if not new_role:
        return

    if new_role in member.roles:
        return

    for role_id in ROLE_MAP.values():
        role = guild.get_role(role_id)
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason="XP progression sync")
            except discord.Forbidden:
                pass

    try:
        await member.add_roles(new_role, reason="XP progression sync")
    except discord.Forbidden:
        pass


@tasks.loop(minutes=10)
async def sync_roles():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    data = db.get_all_xp()

    for user_id, xp in data:
        try:
            member = guild.get_member(int(user_id))
            if member is None:
                member = await guild.fetch_member(int(user_id))

            level = db.get_tier(xp)
            await sync_member_roles(member, level)
            print(f"{member} -> XP {xp} -> Level {level}")

        except discord.NotFound:
            continue
        except discord.Forbidden:
            print(f"No permission for {user_id}")
        except Exception as e:
            print(f"Error {user_id}: {e}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    sync_roles.start()


bot.run(TOKEN)
