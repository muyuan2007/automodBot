from discord.ext import commands, tasks
import re
import discord
import requests
from features.punishing import log_ban
import asyncpg
import asyncio
from features.spellchecking import check

async def handle_send(member, embed):
    try:
        await member.send(embed=embed)
    except:
        print('a')


async def connections():
    global conn
    conn = await asyncpg.create_pool(host=d['host'], port=d['port'], user=d['user'],password=d['pwd'], database=d['db'])


def get_time_in_seconds(time,unit):
    if unit == 'seconds':
        return time
    if unit == 'minutes':
        return 60*time
    if unit == 'hours':
        return 3600*time
    if unit == 'days':
        return 86400*time


def not_sub(text, target):
    return f" {text} " in target or target.strip() == text or target.strip().endswith(f" {text}") or target.strip().startswith(f"{text} ")


d = {}

with open('tk.json','r+') as f:
    info = eval(f.read())['db']
    for key in list(info.keys()):
        d[key] = info[key]
badProfiles = { 'hitler': 'Substring', 'nazi': 'Substring', 'adolf': 'Substring', 'holocaust': 'Substring', 'auschwitz': 'Substring', 'rapist': 'Substring', 'porn': 'Substring', 'molest': 'Substring', 'traffick': 'Substring', 'rape': 'NoSubstring', 'raping': 'NoSubstring', 'pedo': 'Substring', 'paedo': 'Substring', 'sex': 'NoSubstring'}

class AutoKickBan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
    @commands.Cog.listener('on_member_join')
    async def autokickban(self, member):
        global r
        r = ''
        guild_id = member.guild.id
        g = member.guild
        bot_user = f'{self.bot.user.name}#{self.bot.user.discriminator}'
        rules = await conn.fetchrow('SELECT * FROM autokickban WHERE guild_id=$1', guild_id)
        if rules is not None:
            ban_rules = dict(rules)['banrules']
            kick_rules = dict(rules)['kickrules']
        else:
            ban_rules = [str({"type": "nsfwpfp", "timeVal": 24, "timeUnit": "hours", "usernames": {}, "statuses": {}}),str({"type": "username", "timeVal": 24, "timeUnit": "hours", "usernames": badProfiles, "statuses": {}}),str({"type": "status", "timeVal": 24, "timeUnit": "hours", "usernames": {}, "statuses": badProfiles})]
            kick_rules = [str({"type": "accountAge", "timeVal": 7, "timeUnit": "days", "usernames": {}, "statuses": {}}),str({"type": "promoName", "timeVal": 24, "timeUnit": "hours", "usernames": {}, "statuses": {}})]
        global alr_gone
        alr_gone = False
        print(ban_rules)
        for rule in ban_rules:
            rule = eval(rule)
            if rule['type'] == 'accountAge' and not alr_gone:
                if (member.joined_at - member.created_at).total_seconds() <= get_time_in_seconds(rule['timeVal'],
                                                                                                 rule['timeUnit']):
                    r = f"Auto ban function: account too young, account age is {(member.joined_at - member.created_at).total_seconds()} seconds old, minimum account age is {get_time_in_seconds(rule['timeVal'], rule['timeUnit'])} seconds"
                    await log_ban(self.bot, member.guild, member, r, self.bot, conn)
                    await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                          description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                    alr_gone = True
                    await member.ban(reason=r)


            if rule['type'] == 'promoName' and not alr_gone:
                r = f"Auto ban function: invite link in name/status"
                if bool(re.findall(r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?', member.name)):
                    await log_ban(self.bot, member.guild, member, r, self.bot, conn)
                    await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                          description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                    alr_gone = True
                    await member.ban(reason=r)
                if len([activity for activity in member.activities if
                        isinstance(activity, discord.CustomActivity)]) > 0:
                    status = [activity for activity in member.activities if isinstance(activity, discord.CustomActivity)][0].name
                    if bool(re.findall(r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?',
                                       status)):
                        await log_ban(self.bot, member.guild, member, r, self.bot, conn)
                        await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                                      description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                        alr_gone = True
                        await member.ban(reason=r)

            if rule['type'] == 'nsfwpfp' and not alr_gone:
                if requests.post("https://api.deepai.org/api/nsfw-detector", data={'image': str(member.avatar), },
                                 headers={'api-key': '0c25ca40-f09f-45d2-8546-8bd867cc32fd'}).json()['output'][
                    'nsfw_score'] >= 0.9:
                    r = "Auto ban function: NSFW avatar"
                    await log_ban(self.bot, member.guild, member, r, self.bot, conn)
                    await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                          description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                    await member.ban(reason=r)

                    alr_gone = True
            if rule['type'] == 'username':
                no_sub_usernames = [name for name in list(rule['usernames'].keys()) if
                                    rule['usernames'][name] == 'NoSubstring']
                sub_usernames = [name for name in list(rule['usernames'].keys()) if
                                 rule['usernames'][name] == 'Substring']
                for name in no_sub_usernames:
                    if (not_sub(name.lower(), check(member.name.lower()).lower()) or not_sub(name.lower(),
                                                                                             member.name.lower())) and not alr_gone:
                        r = f"Auto ban function: blacklisted word in name: {name}"
                        await log_ban(self.bot, member.guild, member, r, self.bot, conn)
                        alr_gone = True
                        await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                              description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                        await member.ban(reason=r)

                for name in sub_usernames:
                    print(check(member.name.lower()).lower())
                    if (name.lower() in check(member.name.lower()).lower() or name.lower() in member.name.lower()) and not alr_gone:
                        r = f"Auto ban function: blacklisted word in name: {name}"
                        await log_ban(self.bot, member.guild, member, r, self.bot, conn)
                        alr_gone = True
                        await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                              description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                        await member.ban(reason=r)

            if rule['type'] == 'status':
                if len([activity for activity in member.activities if
                        isinstance(activity, discord.CustomActivity)]) > 0:
                    status = \
                        [activity for activity in member.activities if isinstance(activity, discord.CustomActivity)][
                            0].name
                    no_sub_statuses = [name for name in list(rule['statuses'].keys()) if
                                       rule['statuses'][name] == 'NoSubstring']
                    sub_statuses = [name for name in list(rule['statuses'].keys()) if
                                    rule['statuses'][name] == 'Substring']

                    for stt in no_sub_statuses:
                        if (not_sub(stt.lower(), check(status.lower()).lower()) or not_sub(stt.lower(), status.lower())) and not alr_gone:
                            r = f"Auto ban function: blacklisted word in status: {stt}"
                            await log_ban(self.bot, member.guild, member, r, self.bot, conn)
                            alr_gone = True
                            await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                                  description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                            await member.ban(reason=r)

                    for stt in sub_statuses:
                        if (stt.lower() in check(status.lower()).lower() or stt.lower() in status.lower()) and not alr_gone:
                            r = f"Auto ban function: blacklisted word in status: {stt}"
                            await log_ban(self.bot, member.guild, member, r, self.bot, conn)
                            alr_gone = True
                            await handle_send(member, embed=discord.Embed(title=f"You've been banned from {g}",
                                                                  description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                            await member.ban(reason=r)


            r = ''
            g = member.guild
            alr_gone = False
            for rule in kick_rules:
                rule = eval(rule)
                if rule['type'] == 'accountAge' and not alr_gone:
                    if (member.joined_at - member.created_at).total_seconds() <= get_time_in_seconds(rule['timeVal'],
                                                                                                     rule['timeUnit']):
                        r = f"Auto kick function: account too young, account age is {(member.joined_at - member.created_at).total_seconds()} seconds old, minimum account age is {get_time_in_seconds(rule['timeVal'], rule['timeUnit'])} seconds"
                        await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                              description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                        alr_gone = True
                        await member.kick(reason=r)

                if rule['type'] == 'promoName' and not alr_gone:
                    r = f"Auto kick function: invite link in name/status"
                    if bool(re.findall(r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?', member.name)):
                        await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                              description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                        alr_gone = True
                        await member.kick(reason=r)

                    if len([activity for activity in member.activities if
                            isinstance(activity, discord.CustomActivity)]) > 0:
                        status = [activity for activity in member.activities if
                                  isinstance(activity, discord.CustomActivity)][0].name
                        if bool(re.findall(r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?',
                                           status)):
                            await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                                          description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                            alr_gone = True
                            await member.kick(reason=r)

                if rule['type'] == 'nsfwpfp' and not alr_gone:
                    if requests.post("https://api.deepai.org/api/nsfw-detector", data={'image': str(member.avatar), },
                                     headers={'api-key': '0c25ca40-f09f-45d2-8546-8bd867cc32fd'}).json()['output'][
                        'nsfw_score'] >= 0.9:
                        r = "Auto kick function: NSFW avatar"
                        await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                              description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                        alr_gone = True
                        await member.kick(reason=r)

                if rule['type'] == 'username':
                    no_sub_usernames = [name for name in list(rule['usernames'].keys()) if
                                        rule['usernames'][name] == 'NoSubstring']
                    sub_usernames = [name for name in list(rule['usernames'].keys()) if
                                     rule['usernames'][name] == 'Substring']
                    for name in no_sub_usernames:
                        if (not_sub(name.lower(), check(member.name.lower()).lower()) or not_sub(name.lower(), member.name.lower())) and not alr_gone:
                            r = f"Auto kick function: blacklisted word in name: {name}"
                            alr_gone = True
                            await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                                  description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                            await member.kick(reason=r)

                            alr_gone = True
                    for name in sub_usernames:
                        if (name.lower() in check(
                                member.name.lower()).lower() or name.lower() in member.name.lower()) and not alr_gone:
                            r = f"Auto kick function: blacklisted word in name: {name}"
                            await member.kick(reason=r)
                            await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                                  description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                            alr_gone = True

                if rule['type'] == 'status':
                    if len([activity for activity in member.activities if
                            isinstance(activity, discord.CustomActivity)]) > 0:
                        status = \
                            [activity for activity in member.activities if isinstance(activity, discord.CustomActivity)][
                                0].name
                        no_sub_statuses = [name for name in list(rule['statuses'].keys()) if
                                           rule['statuses'][name] == 'NoSubstring']
                        sub_statuses = [name for name in list(rule['statuses'].keys()) if
                                        rule['statuses'][name] == 'Substring']

                        for stt in no_sub_statuses:
                            if (not_sub(stt.lower(), check(status.lower()).lower()) or not_sub(stt.lower(),
                                                                                               status.lower())) and not alr_gone:
                                r = f"Auto kick function: blacklisted word in status: {stt}"
                                alr_gone = True
                                await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                                      description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                                await member.kick(reason=r)

                        for stt in sub_statuses:
                            if (stt.lower() in check(status.lower()).lower() or stt.lower() in check(status.lower())) and not alr_gone:
                                r = f"Auto kick function: blacklisted word in status: {stt}"
                                alr_gone = True
                                await handle_send(member, embed=discord.Embed(title=f"You've been kicked from {g}",
                                                                      description=f"**Reason: **{r}\n**Moderator: **{bot_user}", color=0xf54254))
                                await member.kick(reason=r)



asyncio.get_event_loop().run_until_complete(connections())

    
def setup(bot):
    bot.add_cog(AutoKickBan(bot))