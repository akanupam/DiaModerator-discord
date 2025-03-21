import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import json

# Load environment variables
load_dotenv()

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create bot instance
bot = commands.Bot(command_prefix='!', intents=intents)

# Load bad words and initialize warning counter
with open('bad_words.json', 'r') as f:
    BAD_WORDS = json.load(f)

# Dictionary to store warning counts
warning_counts = {}

# Add these policy responses after the imports
POLICY_RESPONSES = {
    "rules": "Server Rules:\n1. No inappropriate language\n2. Be respectful to others\n3. 3 warnings will result in a ban",
    "warning": "Warning System:\n- Bad words = automatic warning\n- 3 warnings = automatic ban\n- Admins can clear warnings",
    "commands": "Available Commands:\n!warnings - Check warning count\n!clearwarnings - Reset warnings (admin only)\n!warn - Warn a user (mod only)\n!ban - Ban a user (admin only)",
    "help": "You can ask me about:\n- rules\n- warning system\n- commands\n- policies",
    "policies": "Chat Policies:\n1. Messages are monitored for bad words\n2. Warning system is automated\n3. Moderators can issue manual warnings\n4. Administrators can clear warnings"
}

@bot.event
async def on_message(message):
    """
    Event handler for processing incoming messages.
    - Handles bot mentions and responses
    - Checks for bad words and manages warnings
    - Processes bot commands
    """
    if message.author == bot.user:
        return

    # Check if bot is mentioned
    if bot.user in message.mentions:
        # Check if bot has already replied to this message
        already_replied = False
        async for reply in message.channel.history(limit=20):
            # Check both direct replies and regular messages that might be responses
            if reply.author == bot.user and (
                (reply.reference and reply.reference.message_id == message.id) or
                (reply.content.startswith(f'{message.author.mention} has') and reply.created_at > message.created_at)
            ):
                already_replied = True
                break
        
        if not already_replied:
            content = message.content.lower()
            response = "Type help to learn what you can ask about!"
            
            for key in POLICY_RESPONSES:
                if key in content:
                    response = POLICY_RESPONSES[key]
                    break
            
            await message.reply(response)
        return

    try:
        content = message.content.lower()
        if any(word.lower() in content for word in BAD_WORDS):
            await message.delete()
            
            # Update warning count
            user_id = str(message.author.id)
            warning_counts[user_id] = warning_counts.get(user_id, 0) + 1
            
            if warning_counts[user_id] > 3:
                await message.author.ban(reason="Exceeded maximum warnings (3)")
                await message.channel.send(f'{message.author.mention} has been banned for exceeding 3 warnings!')
            else:
                await message.channel.send(f'{message.author.mention}, please watch your language! Warning {warning_counts[user_id]}/3')
    except discord.errors.Forbidden:
        print(f"Missing permissions in {message.channel.name}")
    except Exception as e:
        print(f"Error processing message: {e}")

    await bot.process_commands(message)

@bot.command()
async def warnings(ctx, member: discord.Member = None):
    """
    Command to check warning count for a user.
    Usage: !warnings [member]
    - Shows warnings for mentioned member or command author if no member specified
    - Accessible by all users
    """
    member = member or ctx.author
    user_id = str(member.id)
    count = warning_counts.get(user_id, 0)
    await ctx.send(f'{member.mention} has {count} warning(s).')

@bot.command()
@commands.has_permissions(administrator=True)
async def clearwarnings(ctx, member: discord.Member):
    """
    Command to reset warnings for a user.
    Usage: !clearwarnings <member>
    - Resets warning count to zero
    - Requires administrator permissions
    """
    user_id = str(member.id)
    if user_id in warning_counts:
        warning_counts[user_id] = 0
        await ctx.send(f'Warnings cleared for {member.mention}')
    else:
        await ctx.send(f'{member.mention} has no warnings to clear.')

@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason=None):
    """
    Command to manually warn a user.
    Usage: !warn <member> [reason]
    - Issues a warning with optional reason
    - Requires kick member permissions
    """
    await ctx.send(f'{member.mention} has been warned by {ctx.author.mention}!\nReason: {reason if reason else "No reason provided"}')

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    """
    Command to ban a user from the server.
    Usage: !ban <member> [reason]
    - Permanently bans the member
    - Requires ban member permissions
    """
    await member.ban(reason=reason)
    await ctx.send(f'{member.mention} has been banned by {ctx.author.mention}!')

@bot.event
async def on_ready():
    """
    Event handler for when bot successfully connects.
    - Initializes bot state
    - Processes message history for all servers
    - Sets up warning system and command handling
    """
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} servers')
    print('Checking message history...')
    
    # Track processed message IDs to avoid duplicates
    processed_messages = set()
    
    for guild in bot.guilds:
        for channel in guild.text_channels:
            try:
                # Process messages in batches to avoid timeouts
                async for message in channel.history(limit=100):
                    if message.author == bot.user or message.id in processed_messages:
                        continue
                    
                    processed_messages.add(message.id)
                    
                    # Check for commands and mentions
                    if message.content.startswith('!'):
                        # More thorough check for existing responses
                        already_replied = False
                        async for reply in channel.history(limit=20, after=message):
                            if reply.author == bot.user and (
                                (hasattr(reply, 'reference') and reply.reference and reply.reference.message_id == message.id) or
                                (reply.content and message.author.mention in reply.content)
                            ):
                                already_replied = True
                                break
                        
                        if not already_replied:
                            try:
                                ctx = await bot.get_context(message)
                                if ctx.valid:
                                    await bot.invoke(ctx)
                            except Exception as e:
                                print(f"Error processing command: {e}")
                    
                    # Check for mentions with improved duplicate detection
                    elif bot.user in message.mentions:
                        already_replied = False
                        async for reply in channel.history(limit=20, after=message):
                            if reply.author == bot.user and (
                                (hasattr(reply, 'reference') and reply.reference and reply.reference.message_id == message.id) or
                                (reply.content and message.author.mention in reply.content)
                            ):
                                already_replied = True
                                break
                        
                        if not already_replied:
                            try:
                                content = message.content.lower()
                                response = "Type help to learn what you can ask about!"
                                for key in POLICY_RESPONSES:
                                    if key in content:
                                        response = POLICY_RESPONSES[key]
                                        break
                                await message.reply(response)
                            except Exception as e:
                                print(f"Error responding to mention: {e}")
                    
                    # Existing bad word check
                    content = message.content.lower()
                    if any(word.lower() in content for word in BAD_WORDS):
                        user_id = str(message.author.id)
                        warning_counts[user_id] = warning_counts.get(user_id, 0) + 1
                        
                        if warning_counts[user_id] > 3:
                            try:
                                await message.author.ban(reason="Exceeded maximum warnings (3)")
                                await channel.send(f'{message.author.mention} has been banned for exceeding 3 warnings!')
                            except discord.errors.Forbidden:
                                print(f"Cannot ban user in {guild.name}")
                        await message.delete()
            except discord.errors.Forbidden:
                print(f"No access to channel: {channel.name} in {guild.name}")
            except Exception as e:
                print(f"Error checking channel {channel.name}: {e}")
    
    print('Finished checking message history!')
    print('------')

@bot.event
async def on_guild_join(guild):
    """
    Event handler for when bot joins a new server.
    - Processes server message history
    - Checks for bad words in existing messages
    - Updates warning counts accordingly
    """
    print(f'Joined new server: {guild.name}')
    print('Checking message history...')
    
    for channel in guild.text_channels:
        try:
            async for message in channel.history(limit=1000):
                if message.author == bot.user:
                    continue
                
                content = message.content.lower()
                if any(word.lower() in content for word in BAD_WORDS):
                    user_id = str(message.author.id)
                    warning_counts[user_id] = warning_counts.get(user_id, 0) + 1
                    await message.delete()
        except:
            print(f"Cannot access channel: {channel.name}")
    
    print('Finished checking new server history!')

@bot.event
async def on_connect():
    """
    Event handler for initial connection to Discord.
    - Logs connection status
    """
    print('Bot has connected to Discord!')

@bot.event
async def on_disconnect():
    """
    Event handler for Discord disconnection.
    - Logs disconnection status
    """
    print('Bot has disconnected from Discord!')

@bot.event
async def on_error(event, *args, **kwargs):
    """
    Event handler for bot errors.
    - Logs error details with traceback
    - Helps in debugging issues
    """
    print(f'Error in {event}:')
    import traceback
    traceback.print_exc()

# Run the bot with token from environment variable
bot.run(os.getenv('DISCORD_TOKEN'))