import discord
import os
import json
from discord.ext import commands
from discord.ext.commands import check
from dotenv import load_dotenv
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_LOG_FILE = os.path.join(BASE_DIR, "audit.log")
PARENT_DIR = os.path.dirname(BASE_DIR)
dotenv_path = os.path.join(PARENT_DIR, ".env")
load_dotenv(dotenv_path)

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not DISCORD_BOT_TOKEN:
    raise ValueError("❌ DISCORD_BOT_TOKEN not found in .env. Check your .env file.")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

INVENTORY_FILE = os.path.join(BASE_DIR, "inventory.json")
SCHOOL_FILE = os.path.join(BASE_DIR, "school.json")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

inventory = {}
school = {}

### === ADMIN CHECK === ###

def is_admin():
    def predicate(ctx):
        return ctx.author.id == ADMIN_ID
    return check(predicate)

### === ERROR CONTROL === ###

def clean_input(s: str) -> str:
    return s.strip('"').strip("'").title()

@bot.event
async def on_command_error(ctx, error):
    from discord.ext.commands import CommandNotFound

    if isinstance(error, CommandNotFound):
        return  # silently ignore unknown commands
    await ctx.send(f"⚠️ Error: {str(error)}")

### === LOAD AND SAVE FUNCTIONS === ###

def save_data():
    with open(INVENTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=4)
    with open(SCHOOL_FILE, "w", encoding="utf-8") as f:
        json.dump(school, f, indent=4)

def load_data():
    global inventory, school
    if os.path.exists(INVENTORY_FILE):
        with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
            inventory = json.load(f)
    if os.path.exists(SCHOOL_FILE):
        with open(SCHOOL_FILE, "r", encoding="utf-8") as f:
            school = json.load(f)

@bot.event
async def on_ready():
    load_data()
    print(f'🧙 Bot ready as {bot.user}')

### === AUDIT FUNCTIONS === ###

def log_audit(action: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {action}\n")

@bot.command()
@is_admin()
async def showaudit(ctx, lines: int = 10):
    if not os.path.exists(AUDIT_LOG_FILE):
        await ctx.send("📭 No audit log found.")
        return

    with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
        all_lines = f.readlines()

    if not all_lines:
        await ctx.send("📭 Audit log is empty.")
        return

    last_lines = all_lines[-lines:]
    await ctx.send("📜 Last audit entries:\n" + "".join(last_lines))

### === INVENTORY COMMANDS === ###

@bot.command()
async def setitem(ctx, character: str, slot: str, *, item: str):
    character = character.strip('"').title()
    slot = slot.strip('"').title()
    if character not in inventory:
        inventory[character] = {}
    inventory[character][slot] = item
    save_data()
    log_audit(f"{ctx.author.name} set {slot} for {character} to '{item}'")
    await ctx.send(f"✅ Set item in **{slot}** for **{character}**: {item}")

@bot.command()
async def getitem(ctx, character: str, slot: str):
    character = character.strip('"').title()
    slot = slot.strip('"').title()
    item = inventory.get(character, {}).get(slot)
    if item:
        await ctx.send(f"🎒 **{character}** has **{item}** in **{slot}**.")
    else:
        await ctx.send(f"❌ No item in **{slot}** for **{character}**.")

@bot.command()
async def removeitem(ctx, character: str, slot: str):
    character = character.strip('"').title()
    slot = slot.strip('"').title()

    if character not in inventory or slot not in inventory[character]:
        await ctx.send(f"❌ No item found in **{slot}** for **{character}**.")
        return

    removed_item = inventory[character].pop(slot)
    # Clean up character if inventory is now empty
    if not inventory[character]:
        del inventory[character]
    save_data()
    log_audit(f"{ctx.author.name} removed '{removed_item}' from {slot} of {character}")
    await ctx.send(f"🗑️ Removed **{removed_item}** from **{slot}** of **{character}**.")


@bot.command()
async def showinventory(ctx, character: str):
    character = character.strip('"').title()
    inv = inventory.get(character)
    if not inv:
        await ctx.send(f"📭 No inventory found for **{character}**.")
        return
    embed = discord.Embed(title=f"{character}'s Inventory", color=0x3498db)
    for slot, item in inv.items():
        embed.add_field(name=slot, value=item, inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def showallinventories(ctx):
    if not inventory:
        await ctx.send("📦 No characters have inventory yet.")
        return
    for character in sorted(inventory.keys()):
        inv = inventory[character]
        embed = discord.Embed(title=f"{character}'s Inventory", color=0x95a5a6)
        for slot, item in inv.items():
            embed.add_field(name=slot, value=item, inline=False)
        await ctx.send(embed=embed)

### === ACADEMY REGISTRY COMMANDS === ###

VALID_ROLES = ["Initiate", "Attendant", "Conversant", "Lore-Speaker", "Learned One", "Service"]
VALID_BRANCHES = [
    "Cascade Bearers", "Emerald Boughs", "Rain-Scribes",
    "Tempest-Sun Mages", "Uzunjati", "Magaambya"
]

@bot.command()
async def addperson(ctx, name: str, role: str, *, branch: str):
    name = name.strip('"').title()
    role = role.strip('"').title()
    branch = branch.strip('"').title()

    if role not in VALID_ROLES:
        await ctx.send("❌ Invalid role. Choose from:\n" + ", ".join(VALID_ROLES))
        return

    if branch not in VALID_BRANCHES:
        await ctx.send("❌ Invalid branch. Choose from:\n" + ", ".join(VALID_BRANCHES))
        return

    if name in school:
        await ctx.send(f"⚠️ {name} already exists as a {school[name]['role']} in {school[name]['branch']}.")
        return

    school[name] = {"role": role, "branch": branch}
    save_data()
    log_audit(f"{ctx.author.name} added {role} {name} to {branch}")
    await ctx.send(f"✅ Added **{role} {name}** to **{branch}**.")

@bot.command()
async def removeperson(ctx, name: str):
    name = name.strip('"').title()
    if name in school:
        removed = school.pop(name)
        save_data()
        log_audit(f"{ctx.author.name} removed {name} from {removed['branch']}")
        await ctx.send(f"🗑️ Removed **{name}** ({removed['role']}) from **{removed['branch']}**.")
    else:
        save_data()
        await ctx.send(f"❌ No record found for **{name}**.")

@bot.command()
async def getperson(ctx, name: str):
    name = name.strip('"').title()
    info = school.get(name)
    if not info:
        await ctx.send(f"❌ No record found for **{name}**.")
    else:
        await ctx.send(f"📘 **{name}** is a **{info['role']}** in **{info['branch']}** branch.")

@bot.command()
async def getbranch(ctx, branch: str):
    branch = branch.strip('"').title()
    people = {name: data["role"] for name, data in school.items() if data["branch"] == branch}
    if not people:
        await ctx.send(f"❌ No people found in **{branch}** branch.")
    else:
        lines = [f"- {name} ({role})" for name, role in sorted(people.items())]
        await ctx.send(f"🏫 People in **{branch}**:\n" + "\n".join(lines))

@bot.command()
async def movebranch(ctx, name: str, *, new_branch: str):
    name = name.strip('"').title()
    new_branch = new_branch.strip('"').title()

    if new_branch not in VALID_BRANCHES:
        await ctx.send("❌ Invalid branch. Choose from:\n" + ", ".join(VALID_BRANCHES))
        return

    if name not in school:
        await ctx.send(f"❌ No record found for **{name}**.")
        return

    old_branch = school[name]["branch"]
    school[name]["branch"] = new_branch
    save_data()
    log_audit(f"{ctx.author.name} moved {name} from {old_branch} to {new_branch}")
    await ctx.send(f"🔄 Moved **{name}** from **{old_branch}** to **{new_branch}**.")

@bot.command()
async def showacademy(ctx):
    if not school:
        await ctx.send("📭 No entries in the Magaambya yet.")
        return

    embed = discord.Embed(title="🏰 Magaambya Roster", color=0x9b59b6)
    branches = {}

    for name, data in school.items():
        branch = data["branch"]
        role = data["role"]
        branches.setdefault(branch, []).append(f"{name} ({role})")

    for branch, members in sorted(branches.items()):
        embed.add_field(name=branch, value="\n".join(sorted(members)), inline=False)

    await ctx.send(embed=embed)

### === RELOAD COMMAND === ###

@bot.command()
@is_admin()
async def reload(ctx):
    load_data()
    log_audit(f"{ctx.author.name} reloaded data from disk")
    await ctx.send("🔄 Reloaded data from disk.")

### === HELP COMMAND === ###

@bot.command(name="helpbot")
async def helpbot(ctx):
    embed = discord.Embed(title="📘 DnD Strength of Thousands Bot Command Help", color=0x00bcd4)

    # Inventory Commands
    embed.add_field(
        name="Inventory Commands",
        value=(
            "`!setitem \"Character\" \"Slot\" \"Item\"` - Set item in a slot\n"
            "`!getitem \"Character\" \"Slot\"` - Get item in a slot\n"
            "`!removeitem \"Character\" \"Slot\"` - Remove item from a slot\n"
            "`!showinventory \"Character\"` - Show inventory of a character\n"
            "`!showallinventories` - Show inventories of all characters"
        ),
        inline=False
    )

    # Magic Academy Commands
    embed.add_field(
        name="Magic Academy Registry",
        value=(
            "`!addperson \"Name\" \"Role\" \"Branch\"` - Add a student or teacher to a branch\n"
            "`!getperson \"Name\"` - Show a person’s role and branch\n"
            "`!getbranch \"Branch\"` - List everyone in a branch\n"
            "`!removeperson \"Name\"` - Remove a person from the academy\n"
            "`!movebranch \"Name\" \"New Branch\"` - Move a person to another branch\n"
            "`!showacademy` - Show all people in the academy grouped by branch"
        ),
        inline=False
    )

    embed.add_field(name="Allowed Roles", value=", ".join(VALID_ROLES), inline=False)
    embed.add_field(name="Allowed Branches", value=", ".join(VALID_BRANCHES), inline=False)

    # Admin Commands (admin only)
    embed.add_field(
        name="Admin Commands (Admin Only)",
        value=(
            "`!showaudit [lines]` - Show last audit log entries (default 10 lines)\n"
            "`!reload` - Reload data from disk\n"
        ),
        inline=False
    )

    # Help
    embed.add_field(name="Other", value="`!helpbot` - Show this help message", inline=False)

    await ctx.send(embed=embed)

### === RUN THE BOT === ###

bot.run(DISCORD_BOT_TOKEN)
