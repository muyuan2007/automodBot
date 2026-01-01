import gc
import json
from datetime import datetime, timezone

import psutil
from discord.ext import commands, tasks
import re
import discord
from features.punishing import log_ban
import asyncpg
import asyncio
from features.spellchecking import remove_ignored, check_for_word


async def handle_send(member, embed):
    try:
        await member.send(embed=embed)
    except:
        pass


async def connections():
    global conn
    conn = await asyncpg.create_pool(host=d['host'], port=d['port'], user=d['user'], password=d['pwd'],
                                     database=d['db'])


async def get_time_in_seconds(time, unit):
    if unit == 'seconds':
        return time
    if unit == 'minutes':
        return 60 * time
    if unit == 'hours':
        return 3600 * time
    if unit == 'days':
        return 86400 * time


async def not_sub(text, target): # done
    text_lower = text.lower()
    target_lower = target.lower()
    return f" {text_lower} " in target_lower or target_lower.strip() == text_lower or target_lower.strip().endswith(
        f" {text_lower}") or target_lower.strip().startswith(f"{text_lower} ")


emoj = re.compile("["
                  u"\U0001F600-\U0001F64F"  # emoticons
                  u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                  u"\U0001F680-\U0001F6FF"  # transport & map symbols
                  u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                  u"\U000024C2-\U0001F251"
                  u"\U0001f926-\U0001f937"
                  u"\U00010000-\U0010ffff"
                  u"\u2600-\u2B55"
                  u"\u200d"
                  u"\u23cf"
                  u"\u23e9"
                  u"\u231a"
                  u"\ufe0f"  # dingbats
                  u"\u3030"
                  "]+", re.UNICODE)


async def remove_emoji(data):
    return re.sub(emoj, '', data)


async def no_punc(string):
    return string.translate(str.maketrans('', '', '"#$%&*+,:;<=>?@[\\]^_`{|}~'))


async def remove_emojis(text):
    s = re.sub('<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>', '', await remove_emoji(text))
    return s


d = {}

with open('tk.json', 'r') as f:
    info = json.load(f)['db']
    d.update(info)
    f.close()

loop = asyncio.get_event_loop()


async def status(member):
    a = [activity for activity in member.activities if
         isinstance(activity, discord.CustomActivity)]
    if len(a) > 0:
        if a[0].name is not None:
            return a[0].name
        else:
            return None
    else:
        stats = []
        for guild in member.mutual_guilds:
            act = [activity for activity in guild.get_member(member.id).activities if
                   isinstance(activity, discord.CustomActivity)]
            if len(act) == 0:
                stats.append('')
            else:
                if act[0].name is not None:
                    stats.append(act[0].name)
                else:
                    stats.append('')
        stats.sort()
        return stats[-1]


async def clean(s):
    remove_zalgo = lambda s: re.sub("(?i)([aeiouy]̈)|[̀-ͯ҉]", "\\1", s)
    return (await remove_emojis(await no_punc(remove_zalgo(s)))) \
        .replace("\u200b", "").casefold().strip().lower().replace("…", "...")

async def autokb(bot, member, custom_status):
    print("autokb start handle")

    global r
    r = ''
    guild_id = member.guild.id
    g = member.guild
    ukrainian = guild_id == 1030173379447246978
    bot_user = f'{bot.user.name}#{bot.user.discriminator}'
    rules = await bot.conn.fetchrow('SELECT * FROM autokickban WHERE guild_id=$1', guild_id)
    general_settings = await bot.conn.fetchrow('SELECT automodgeneral FROM msg_automod WHERE guild_id=$1', guild_id)
    if general_settings is None:
        ignored_words = []
    else:
        if "ignored_words" not in dict(general_settings)['automodgeneral']:
            ignored_words = []
        else:
            ignored_words = eval(dict(general_settings)['automodgeneral'])['ignored_words']

    username = await clean(re.sub(r'https?:\/\/.*[\r\n]*', '', await remove_ignored(member.name.lower(), ignored_words)))

    dispname = await clean(re.sub(r'https?:\/\/.*[\r\n]*', '', await remove_ignored(member.display_name.lower(), ignored_words)))

    regular_status = await clean(re.sub(r'https?:\/\/.*[\r\n]*', '', await remove_ignored(custom_status, ignored_words)))



    if rules is not None:
        ban_rules = dict(rules)['banrules']
        kick_rules = dict(rules)['kickrules']
    else:
        bad_profiles_sub = ['hitler', 'nazi', 'adolf', 'holocaust', 'auschwitz', 'rapist', 'porn', 'molest', 'traffick', 'pedo', 'paedo']
        bad_profiles_nosub = ['rape', 'raping', 'sex']

        ban_rules = [str({"type": "username", "timeVal": 24, "timeUnit": "hours", "usernames": bad_profiles_sub,
                    "statuses": [], 'substring': 1}),
                str({"type": "username", "timeVal": 24, "timeUnit": "hours", "usernames": bad_profiles_nosub,
                    "statuses": [], 'substring': 0}),
                str({"type": "status", "timeVal": 24, "timeUnit": "hours", "usernames": [],
                    "statuses": bad_profiles_sub, 'substring': 1}),
                str({"type": "status", "timeVal": 24, "timeUnit": "hours", "usernames": [],
                    "statuses": bad_profiles_nosub, 'substring': 0})]
        kick_rules = []

    global alr_gone
    alr_gone = False
    if isinstance(ban_rules, list):
        for rl in ban_rules:
            rule = eval(rl)
            if rule['type'] == 'accountAge' and not alr_gone and not ukrainian:
                ban_threshold = await get_time_in_seconds(rule['timeVal'], rule['timeUnit'])
                if (member.joined_at - member.created_at).total_seconds() <= ban_threshold:
                    r = f"Auto ban function: account too young, account age is {(member.joined_at - member.created_at).total_seconds()} seconds old, minimum account age is {ban_threshold} seconds"
                    await member.ban(reason=r)
                    await log_ban(bot, member.guild, member, r, bot, bot.conn)
                    await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                                description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                                                                color=0xf54254))
                    alr_gone = True

            if rule['type'] == 'promoName' and not alr_gone:
                r = f"Auto ban function: invite link in name/status"
                if bool(re.findall(r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?', member.name)) or\
                    bool(re.findall(r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?', member.display_name)):
                    await member.ban(reason=r)
                    await log_ban(bot, member.guild, member, r, bot, bot.conn)
                    await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                                description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                                                                color=0xf54254))
                    alr_gone = True

                if bool(re.findall(r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?', regular_status)):
                    await member.ban(reason=r)
                    await log_ban(bot, member.guild, member, r, bot, bot.conn)
                    await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                                description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                                                                color=0xf54254))
                    alr_gone = True

            if rule['type'] == 'username':

                if rule['substring'] == 1:
                    for name in rule['usernames']:
                        if await check_for_word(f"{username}, {dispname}", name, 1) and not alr_gone:
                            print([f"{username}, {dispname}", name])
                            r = f"Auto ban function: blacklisted word in name: {name}"
                            await member.ban(reason=r)
                            await log_ban(bot, member.guild, member, r, bot, bot.conn)
                            alr_gone = True
                            await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                                        description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                                                                        color=0xf54254))
                else:
                    for name in rule['usernames']:
                        if await check_for_word(f"{username}, {dispname}", name, 0) and not alr_gone:
                            r = f"Auto ban function: blacklisted word in name: {name}"
                            await member.ban(reason=r)
                            await log_ban(bot, member.guild, member, r, bot, bot.conn)
                            alr_gone = True
                            await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                                        description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                                                                        color=0xf54254))

                    # if (name.lower() in display_name or name.lower() in corrected_dispname) and not alr_gone:
                    #     r = f"Auto ban function: blacklisted word in name: {name}"
                    #     await member.ban(reason=r)
                    #     await log_ban(bot, member.guild, member, r, bot, conn)
                    #     alr_gone = True
                    #     await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                    #                                                   description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                    #                                                   color=0xf54254))

            if rule['type'] == 'status':
                if rule['substring'] == 1:
                    for stt in rule['statuses']:
                        if await check_for_word(regular_status, stt, 1) and not alr_gone:
                            r = f"Auto ban function: blacklisted word in status: {stt}"
                            await member.ban(reason=r)
                            await log_ban(bot, member.guild, member, r, bot, bot.conn)
                            alr_gone = True
                            await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                                        description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                                                                        color=0xf54254))
                else:
                    for stt in rule['statuses']:
                        if await check_for_word(regular_status, stt, 0) and not alr_gone:
                            r = f"Auto ban function: blacklisted word in status: {stt}"
                            await member.ban(reason=r)

                            await log_ban(bot, member.guild, member, r, bot, bot.conn)
                            alr_gone = True
                            await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                                        description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                                                                        color=0xf54254))


    r = ''
    g = member.guild
    alr_gone = False
    if isinstance(kick_rules, list):
        for rl in kick_rules:
            rule = eval(rl)
            if rule['type'] == 'accountAge' and not alr_gone and not ukrainian:
                kick_threshold = await get_time_in_seconds(rule['timeVal'], rule['timeUnit'])
                if (member.joined_at - member.created_at).total_seconds() <= kick_threshold:
                    print(member.created_at, member.joined_at)
                    r = f"Auto kick function: account too young, account age is {(member.joined_at - member.created_at).total_seconds()} seconds old, minimum account age is {kick_threshold} seconds"
                    await member.kick(reason=r)
                    await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                                description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                                                                color=0xf54254))
                    alr_gone = True

            if rule['type'] == 'promoName' and not alr_gone:
                r = f"Auto kick function: invite link in name/status"
                if bool(re.findall(r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?', username)) or \
                        bool(re.findall(r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?',
                                        member.display_name)):
                    await member.kick(reason=r)
                    await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                                description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                                                                color=0xf54254))
                    alr_gone = True

                if bool(re.findall(r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?', regular_status)):
                    await member.kick(reason=r)
                    await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                                description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                                                                color=0xf54254))
                    alr_gone = True

            if rule['type'] == 'status' and not alr_gone:
                if rule['substring'] == 1:
                    for stt in rule['statuses']:
                        if await check_for_word(regular_status, stt, 1) and not alr_gone:
                            r = f"Auto kick function: blacklisted word in status: {stt}"
                            await member.kick(reason=r)

                            alr_gone = True
                            await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                                        description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                                                                        color=0xf54254))
                else:
                    for stt in rule['statuses']:
                        if await check_for_word(regular_status, stt, 0) and not alr_gone:
                            r = f"Auto kick function: blacklisted word in status: {stt}"
                            await member.kick(reason=r)
                            alr_gone = True
                            await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                                        description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                                                                        color=0xf54254))

            if rule['type'] == 'username':
                if rule['substring'] == 1:
                    for name in rule['usernames']:
                        if await check_for_word(f"{username}, {dispname}", name, 1) and not alr_gone:
                            r = f"Auto kick function: blacklisted word in name: {name}"
                            await member.kick(reason=r)
                            alr_gone = True
                            await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                                        description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                                                                        color=0xf54254))
                else:
                    for name in rule['usernames']:
                        if await check_for_word(f"{username}, {dispname}", name, 0) and not alr_gone:

                            r = f"Auto kick function: blacklisted word in name: {name}"
                            await member.kick(reason=r)
                            await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                                        description=f"**Reason: **{r}\n**Moderator: **{bot_user}",
                                                                        color=0xf54254))
                            alr_gone = True

    print("autokb end handle")

conn_thing = {'conn_count': 0}

class AutoKickBan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.run_garbage_collection.start()

    @commands.Cog.listener('on_presence_update')
    async def autokickban(self, before, after):
        if (datetime.now(tz=timezone.utc) - after.joined_at).total_seconds() <= 1 and not after.bot:
            await autokb(self.bot, after.guild.get_member(after.id), await status(after.guild.get_member(after.id)))

    @commands.Cog.listener()
    async def on_disconnect(self):

        self.bot._connection._messages.clear()
        self.bot._connection._stickers.clear()
        self.bot._connection._polls.clear()

        gc.collect()

    #
    # @commands.Cog.listener()
    # async def on_ready(self):
    #     conn_thing['conn_count'] += 1
    #     if conn_thing['conn_count'] == 1:
    #         task = asyncio.create_task(connections())
    #         await task
    #
    # @commands.Cog.listener()
    # async def on_resumed(self):
    #     conn_thing['conn_count'] += 1
    #     if conn_thing['conn_count'] == 1:
    #         task = asyncio.create_task(connections())
    #         await task

    @tasks.loop(minutes=15)
    async def run_garbage_collection(self):
        """Run the garbage collector periodically."""
        gc.collect()

    @run_garbage_collection.before_loop
    async def before_run_garbage_collection(self):
        """Wait until the bot is ready before starting the task."""
        await self.bot.wait_until_ready()
        await asyncio.sleep(900)



def setup(bot):
    bot.add_cog(AutoKickBan(bot))
