import asyncio
import datetime
from datetime import timezone, timedelta
import asyncpg
import requests
from discord import option
import discord

discord.http.API_VERSION = 10
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

d = {}
tk = ''

with open('tk.json', 'r+') as f:
    contents = eval(f.read())
    info = contents['db']
    for key in list(info.keys()):
        d[key] = info[key]

    tk += contents['token']

    f.close()

jason = 'jason_gali'
helpers = ['ruoshui', 'arya', 'krishiv', 'parents', 'qi', 'bever', 'a bunch of coding discord servers']


async def connections():
    global connection
    connection = await asyncpg.create_pool(host=d['host'], port=d['port'], user=d['user'],
                                           password=d['pwd'], database=d['db'])


def leave(guild):
    requests.delete(f'https://discord.com/api/users/@me/guilds/{guild}', headers={'Authorization': f'Bot {tk}'}, )


intents = discord.Intents.all()
intents.auto_moderation_configuration = False
intents.auto_moderation_execution = False
intents.typing = False
intents.reactions = False
intents.polls = False
intents.scheduled_events = False


bot = discord.Bot(intents=intents, help_command=None, strip_after_prefix=True)
cmds = {'warn': ['Give a member warning points', '/warn <member> <amount> [reason]', 'kick members, ban members'],
        'unwarn': ['Remove warning points from a member', '/warn <member> <amount>', 'kick members, ban members'],
        'warns': ["Check a member's warning points.", '/warns [member]', 'none'],
        'mute': ['Timeout/mute a member', '/mute <member> <duration> [reason]', 'moderate/mute members'],
        'unmute': ['Un-timeout/unmute a member', '/unmute <member>', 'moderate/mute members'],
        'kick': ['Kick a member', '/kick <member> [reason]', 'kick members'],
        'tempban': ['Temporarily ban a member', '/tempban <member> <duration> [reason]', 'ban members'],
        'ban': ['Ban a member', '/ban <member> [reason]>', 'ban members'],
        'unban': ['Unban a member', '/unban <member>', 'ban members'],
        'amsettings': ['Check dashboard configuration settings for a certain type of setting', '/amsettings [table]',
                       'none'],
        'purge': ['Bulk delete up to 500 messages at a time', '/purge <amount>', 'manage messages'],
        'infractions': ["Check all of a member's infractions", '/infractions <member> [page]', 'none'],
        'feedback': ["Provide feedback for AMGX!", '/feedback <title> <feedback>', 'none']
        }

detailed_cmds = {'warn': ['Give a member warning points with an optional reason.', '/warn [member] [amount] <reason>',
                          '`kick members`, `ban members`', '`/warn @user 6 spam`\n`/warn @user 9`'],
                 'unwarn': ['Remove warning points from a member. ', '/warn [member] [amount]',
                            '`kick members`, `ban members`', '`/unwarn @user 8`\n`/unwarn @user 0`'],
                 'warns': [
                     "Check a member's warning points. \nIf no member argument is passed, check the warning points of the user entering the command.",
                     '/warns [member]', 'no special permissions required', '`/warns @user`\n`/warns`'],
                 'mute': ['Timeout a member for a duration in seconds with an optional reason.',
                          '/mute <member> <duration> [reason]', '`moderate/mute members`',
                          '`/mute @user 7200 being insulting`\n`/mute @user 259200`'],
                 'unmute': ["Remove a member's timeout.", '/unmute <member>', '`moderate/mute members`',
                            '`/unmute @user`'],
                 'kick': ['Kick a member with an optional reason.', '/kick <member> [reason]', '`kick members`',
                          '`/kick @user persistent disobedience`\n`/kick @user`'],
                 'tempban': ['Temporarily ban a member for a duration in seconds with an optional reason.',
                             '/tempban <member> <duration> [reason]', '`ban members`',
                             '`/tempban @user 2592000 NSFW`\n`/tempban @user 172800`'],
                 'ban': ['Ban a member with an optional reason.', '/ban <member> [reason]', '`ban members`',
                         '`/ban @user death threats`\n`/ban @user`'],
                 'unban': ['Unban a member', '/unban <member>', '`ban members`', '`/unban @user`'],
                 'amsettings': ['Check dashboard configuration settings for a certain type of setting.',
                                '/amsettings [table]', 'no special permissions required',
                                '`/amsettings messagespam`\n`/amsettings badwords`'],
                 'purge': [
                     'Purge a specified number of messages\nEntering an amount above 500 will not purge for technical reasons.',
                     '/purge <amount>', 'manage messages', '`/purge 500`'],
                 'infractions': [
                     "Check a member's complete infraction history(e.g., mutes, unmutes, warns, unwarns, kicks, tempbans, bans, unbans). The infraction history is split into 'pages' of up to 10 records each.\nInputting no member or page argument shows the first infraction page of the user entering the command. Inputting a member argument but no page argument shows the first infraction page of the member being checked.",
                     '/infractions <member> [page]', 'no special permissions required',
                     '`/infractions @user 3`\n`/infractions @user`\n`/infractions`'],
                'feedback': [
                     "Provide feedback for AMGX! Your ideas are invaluable to us.",
                     '/feedback <title> <feedback>', 'no special permissions required',
                     '`/infractions "New bug" "The warning function does not work."`']
                }




logger = logging.getLogger('discord')
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)



@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("/help"))
    print("SCARBO")

    await asyncio.sleep(3)
    await bot.sync_commands()


bot.load_extension('features.automod')
bot.load_extension('features.cmds')
bot.load_extension('features.modlogging')
bot.load_extension('features.autokickban')

@bot.slash_command(description='See a list of commands')
@option("command", description="The command to get detailed info about", choices=cmds.keys())
async def help(ctx, command=None):
    if command is None:
        e = discord.Embed(title="AMGX Commands", color=0x40fc0c)
        for cmd in list(cmds.keys()):
            c = cmds[cmd]
            e.add_field(name=cmd,
                        value=f"**Description:** {c[0].lower()}\n**Usage:** `{c[1]}`\n**Permissions required:** {c[2]}\n",
                        inline=False)
        e.add_field(name="Dashboard link", value='https://www.amgx-bot.com')
        e.set_footer(
            text="Arguments surrounded by greater/less than signs are required. \nArguments surrounded by brackets are optional. \nAny duration arguments have to be inputted in seconds. \nFor the 'unwarn' command, enter 0 as the argument to remove all infraction points.")
        await ctx.respond(embed=e)
    else:
        if command in detailed_cmds:
            e = discord.Embed(title=command, description=detailed_cmds[command][0] + '\n', color=0x40fc0c)
            e.add_field(name='Usage', value=f"`{detailed_cmds[command][1]}`      \n")
            e.add_field(name='Permissions Required', value=detailed_cmds[command][2], inline=True)
            e.add_field(name='Examples', value=detailed_cmds[command][3], inline=False)
            await ctx.respond(embed=e)
        else:
            await ctx.respond(embed=discord.Embed(title='',
                                                  description=f"<:amgx_error:1045162027737415751> No command named '{command}'.",
                                                  color=0xff2300))


@bot.event
async def on_connect():
    if not hasattr(bot, 'conn'):
        bot.conn = await asyncpg.create_pool(
            user=d['user'],
            password=d['pwd'],
            database=d['db'],
            host=d['host'],
            port=d['port']
        )


bot.run(tk)
