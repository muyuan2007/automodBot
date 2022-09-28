import asyncio
import asyncpg
from discord.ext import commands, tasks
import discord
discord.http.API_VERSION = 9

d = {}
tk = ''

with open('tk.json','r+') as f:
    info = eval(f.read())['db']
    for key in list(info.keys()):
        d[key] = info[key]


async def connections():
    global connection
    connection = await asyncpg.create_pool(host=d['host'], port=d['port'], user=d['user'],
                              password=d['pwd'], database=d['db'])


async def get_prefix(client, message):
    global p
    p = 'a!'
    info = await connection.fetchrow('SELECT * FROM bot_settings WHERE guild_id=$1', message.guild.id)
    if info is not None:
        p = dict(info)['bot_prefix']
    return p


bot = commands.Bot(command_prefix=get_prefix, case_insensitive=True, intents=discord.Intents.all(), max_messages=100000000, help_command=None, strip_after_prefix=True)
cmds = {'warn': ['Give a member warning points', 'a!warn <member> <amount> [reason]','kick members, ban members'],
        'unwarn': ['Remove warning points from a member', 'a!warn <member> <amount>','kick members, ban members'],
        'warns': ["Check a member's warning points.", 'a!warns [member]', 'none'],
        'mute': ['Timeout/mute a member', 'a!mute <member> <duration> [reason]', 'moderate/mute members'],
        'unmute': ['Un-timeout/unmute a member', 'a!unmute <member>', 'moderate/mute members'],
        'kick': ['Kick a member', 'a!kick <member> [reason]', 'kick members'],
        'tempban': ['Temporarily ban a member', 'a!tempban <member> <duration> [reason]', 'ban members'],
        'ban': ['Ban a member', 'a!ban <member> [reason]>', 'ban members'],
        'unban': ['Unban a member', 'a!unban <member>', 'ban members'],
        'amsettings': ['Check dashboard configuration settings for a certain type of setting', 'a!amsettings [table]', 'none'],
        'purge': ['Purge up to 500 messages at a time', 'a!purge <amount>', 'manage messages'],
        'prefix': ['Check the current command prefix', 'a!prefix', 'none'],
        'changeprefix': ['Change the command prefix', 'a!changeprefix <prefix>', 'manage server'],
        'infractions': ["Check all of a member's infractions", 'a!infractions <member> [page]', 'none']
        }

detailed_cmds = {'warn': ['Give a member warning points with an optional reason.', 'a!warn [member] [amount] <reason>','`kick members`, `ban members`', '`a!warn @user 6 spam`\n`a!warn @user 9`'],
        'unwarn': ['Remove warning points from a member. ', 'a!warn [member] [amount]', '`kick members`, `ban members`', '`a!unwarn @user 8`\n`a!unwarn @user 0`'],
        'warns': ["Check a member's warning points. \nIf no member argument is passed, check the warning points of the user entering the command.", 'a!warns [member]', 'no special permissions required', '`a!warns @user`\n`a!warns`'],
        'mute': ['Timeout a member for a duration in seconds with an optional reason.', 'a!mute <member> <duration> [reason]', '`moderate/mute members`', '`a!mute @user 7200 being insulting`\n`a!mute @user 259200`'],
        'unmute': ["Remove a member's timeout.", 'a!unmute <member>', '`moderate/mute members`', '`a!unmute @user`'],
        'kick': ['Kick a member with an optional reason.', 'a!kick <member> [reason]', '`kick members`', '`a!kick @user persistent disobedience`\n`a!kick @user`'],
        'tempban': ['Temporarily ban a member for a duration in seconds with an optional reason.', 'a!tempban <member> <duration> [reason]', '`ban members`', '`a!tempban @user 2592000 NSFW`\n`a!tempban @user 172800`'],
        'ban': ['Ban a member with an optional reason.', 'a!ban <member> [reason]', '`ban members`','`a!ban @user death threats`\n`a!ban @user`'],
        'unban': ['Unban a member', 'a!unban <member>', '`ban members`', '`a!unban @user`'],
        'amsettings': ['Check dashboard configuration settings for a certain type of setting.', 'a!amsettings [table]', 'no special permissions required', '`a!amsettings messagespam`\n`a!amsettings badwords`'],
        'purge': ['Purge a specified number of messages\nEntering an amount above 500 will not purge for technical reasons.', 'a!purge <amount>', 'manage messages', '`a!purge 500`'],
        'prefix': ['Check the current command prefix.', 'a!prefix', 'no special permissions required', '`a!prefix`'],
        'changeprefix': ['Change the command prefix to a specified prefix.', 'a!changeprefix <prefix>', 'manage server', '`a!prefix $`'],
        'infractions': ["Check a member's complete infraction history(e.g., mutes, unmutes, warns, unwarns, kicks, tempbans, bans, unbans). The infraction history is split into 'pages' of up to 10 records each.\nInputting no member or page argument shows the first infraction page of the user entering the command. Inputting a member argument but no page argument shows the first infraction page of the member being checked.", 'a!infractions <member> [page]', 'no special permissions required', '`a!infractions @user 3`\n`a!infractions @user`\n`a!infractions`']
        }


bot.load_extension('features.automod')
bot.load_extension('features.cmds')
bot.load_extension('features.modlogging')
bot.load_extension('features.autokickban')


@bot.event
async def on_ready():
    print('ready')
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("a!help"))

@bot.event
async def on_command_error(ctx, exception):
    if isinstance(exception, discord.ext.commands.errors.CommandNotFound):
        await ctx.send(f"No command called '{ctx.invoked_with}'.")


@bot.command()
async def help(ctx, command=None):
    if command is None:
        e = discord.Embed(title="AMGX Commands", color=0x40fc0c)
        for cmd in list(cmds.keys()):
            c = cmds[cmd]
            e.add_field(name=cmd, value=f"**Description:** {c[0].lower()}\n**Usage:** `{c[1]}`\n**Permissions required:** {c[2]}\n",
                        inline=False)
        e.add_field(name="Dashboard link", value='https://www.amgx-bot.com')
        e.set_footer(
            text="Arguments surrounded by greater/less than signs are required. \nArguments surrounded by brackets are optional. \nAny duration arguments have to be inputted in seconds. \nThe 'table' argument must be one of 'modlogs', 'messagespam', 'emojispam', 'mentionspam', 'stickerspam', 'attachmentspam', 'linkspam', 'duplicatecharacters', 'duplicatemessages', 'linebreaks', 'toomanycaps', 'invites', 'selfbot', 'nsfwcontent', 'hatespeech', 'badwords', 'badlinks', 'badnicks', 'badnames', 'badstatuses', 'nsfwpfp', 'autopunish', 'autokickban', or 'automodgeneral'. \nFor the 'unwarn' command, enter 0 as the argument to remove all infraction points.")
        await ctx.send(embed=e)
    else:
        if command in detailed_cmds:
            e = discord.Embed(title=command, description=detailed_cmds[command][0]+'\n', color=0x40fc0c)
            e.add_field(name='Usage', value=f"`{detailed_cmds[command][1]}`      \n")
            e.add_field(name='Permissions Required', value=detailed_cmds[command][2], inline=True)
            e.add_field(name='Examples', value=detailed_cmds[command][3], inline=False)
            await ctx.send(embed=e)
        else:
            await ctx.send(embed=discord.Embed(title='', description=f"<:xmark:1009919995297415190> No command named '{command}'.", color=0xff2300))


with open('tk.json', 'r+') as f:
    token = eval(f.read())['token']
    tk += token

asyncio.get_event_loop().run_until_complete(connections())
bot.run(tk)

