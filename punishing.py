import asyncio
from operator import itemgetter
import discord
import datetime
import json
import aiohttp

webhook_pfp = "https://cdn.discordapp.com/attachments/1274041694018469980/1356831963679293481/MndBTSfgkAAAAASUVORK5CYII.png?ex=67edffbc&is=67ecae3c&hm=22564715d61ff337cce22605cfed5a817e79930a8efac9538aa0af153042cfad&"


async def send_embed_through_wh(embed, webhook_url):
    embed_data = embed.to_dict()

    payload = {
        "username": "AMGX's Logging Minion",
        "avatar_url": webhook_pfp,
        "embeds": [embed_data]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload) as response:
            pass


async def t(secs):
    day = secs // (24 * 3600)
    secs = secs % (24 * 3600)
    hour = secs // 3600
    secs %= 3600
    minutes = secs // 60
    secs %= 60
    seconds = secs
    res = [day, hour, minutes, seconds]

    actual = []
    for i in range(len(res)):
        s = "s" if res[i] > 1 else ""
        if i == 0 and res[i]:
            actual.append(f'{res[i]} day{s}')
        if i == 1 and res[i]:
            actual.append(f'{res[i]} hour{s}')
        if i == 2 and res[i]:
            actual.append(f'{res[i]} minute{s}')
        if i == 3 and res[i]:
            actual.append(f'{res[i]} second{s}')

    return ', '.join(actual)


async def handle_send(member, embed):
    try:
        await member.send(embed=embed)
    except:
        pass


async def time_from_two_vals(time, unit):
    if unit == 'seconds':
        return time
    if unit == 'minutes':
        return 60 * time
    if unit == 'hours':
        return 3600 * time
    if unit == 'days':
        return 86400 * time


async def find_max_rule(rules, amount):
    sorted_rules = sorted(rules, key=itemgetter('threshold'))
    for rule in sorted_rules:
        if rule['threshold'] <= amount and len(
                [punish_rule for punish_rule in sorted_rules[sorted_rules.index(rule) + 1:] if
                 punish_rule['threshold'] <= amount]) == 0:
            return rule
    return {'non_violated': 'no rules were violated'}


async def has_permissions(b, member, permission):
    guild = member.guild
    bot_perms = dict(list(b.guild_permissions))
    if bot_perms[permission] and not guild.owner.id == member.id and member.top_role.position < b.top_role.position:
        return True
    return False


async def warn(bot, member, guild, amount, connection, reason, who):
    bot_user = f'{bot.user.name}#{bot.user.discriminator}'
    key = f"{guild.id}_{member.id}"
    inf_info = await connection.fetchrow('SELECT * FROM user_infraction_points where memberkey=$1', key)
    old_points = 0
    if inf_info is None:
        await connection.execute('INSERT INTO user_infraction_points (memberkey, points) VALUES ($1, $2)', key, amount)
    else:
        inf_info = dict(inf_info)
        old_points += inf_info['points']
        new_amount = inf_info['points'] + amount
        await connection.execute('UPDATE user_infraction_points SET memberkey=$1, points=$2 where memberkey=$1', key,
                                 new_amount)

    await log_warn(bot, guild, member, amount, old_points + amount, who, reason, connection)

    autopunish = await connection.fetchrow('SELECT * FROM autopunish WHERE guild_id=$1', guild.id)

    if autopunish is not None:
        rules = [eval(rule) for rule in dict(autopunish)['rules']]
    else:
        rules = [{'type':"mute", "durationType": "hours", "duration": 6, "threshold": 15},{'type':"kick", "durationType": "minutes", "duration": 1, "threshold": 30},{'type':"tempban", "durationType": "days", "duration": 3, "threshold": 45},{'type':"ban", "durationType": "minutes", "duration": 1, "threshold": 60}]

    max_rule = await find_max_rule(rules, old_points + amount)
    d = {'punishment': '', 'amount': 0}
    if 'type' in list(max_rule.keys()):

        d['reason'] = f'reaching {max_rule["threshold"]} points'
        if max_rule['type'] == 'mute' and old_points < max_rule['threshold'] and await has_permissions(guild.me, member, 'moderate_members'):
            d['punishment'] = max_rule['type']
            d['amount'] += await time_from_two_vals(max_rule['duration'], max_rule['durationType'])

        if max_rule['type'] == 'kick' and old_points < max_rule['threshold'] and await has_permissions(guild.me, member, 'kick_members'):
            d['punishment'] = max_rule['type']

        if max_rule['type'] == 'tempban' and old_points < max_rule['threshold'] and await has_permissions(guild.me, member, 'ban_members'):
            d['punishment'] = max_rule['type']
            d['amount'] += await time_from_two_vals(max_rule['duration'], max_rule['durationType'])

        if max_rule['type'] == 'ban' and old_points < max_rule['threshold'] and await has_permissions(guild.me, member, 'ban_members'):
            d['punishment'] = max_rule['type']

    return d


async def unban_tempbanned(user, duration):
    await asyncio.sleep(duration)
    await user.unban()


async def tempban(bot, user, reason, duration, guild, who, conn):
    await user.ban(reason=reason)
    await handle_send(user, discord.Embed(title=f"You've been temporarily banned from {guild}",
                                          description=f"**Duration: **{await t(duration)}\n**Reason:** {reason}\n**Moderator: **{who}",
                                          color=0xf54254))
    await log_tempban(bot, guild, user, duration, reason, who, conn)
    try:
        unban_task = asyncio.create_task(unban_tempbanned(user, duration))
        await unban_task
    except:
        return


async def log_mute(bot, guild, member, time, reason, who, connection):
    settings = await connection.fetchrow('SELECT moderation_channel, moderations, mod_webhook FROM modlogs WHERE guild_id=$1', guild.id)
    if settings is not None:
        actions_not_empty = dict(settings)['moderations'] is not None
        mod_channel = dict(settings)['moderation_channel'] if actions_not_empty else None
        actions = dict(settings)['moderations'] if actions_not_empty else None
        wh_url = dict(settings)['mod_webhook'] if actions_not_empty else None
        if isinstance(mod_channel, int) and isinstance(actions, list):
            if "Member Muted" in actions:
                embed = discord.Embed(title="", description="", color=0xbf1408)
                url = ''
                if str(member.avatar) != 'None':
                    url += str(member.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(member), icon_url=url)
                embed.set_footer(text=f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                embed.title = 'Member muted'
                embed.description = f'**Muted for:** {time}\n**Reason:** {reason}\n**Moderator: ** {bot.user.name}#{bot.user.discriminator}'
                if wh_url is not None:
                    await send_embed_through_wh(embed, wh_url)
                else:
                    await bot.get_channel(mod_channel).send(embed=embed)

    await log_infraction(member, guild, {"type": "Mute", "Muted for": time, "Reason": reason, "Moderator": f"{bot.user.name}#{bot.user.discriminator}"}, connection)


async def log_unmute(bot, guild, member, connection, who):
    settings = await connection.fetchrow(
        'SELECT moderation_channel, moderations, mod_webhook FROM modlogs WHERE guild_id=$1', guild.id)
    if settings is not None:
        actions_not_empty = dict(settings)['moderations'] is not None
        mod_channel = dict(settings)['moderation_channel'] if actions_not_empty else None
        actions = dict(settings)['moderations'] if actions_not_empty else None
        wh_url = dict(settings)['mod_webhook'] if actions_not_empty else None
        if isinstance(mod_channel, int) and isinstance(actions, list):
            if "Member Unmuted" in actions:
                embed = discord.Embed(title="", description=f"**Moderator:** {who} ({who.mention})", color=0x08bf1d)
                url = ''
                if str(member.avatar) != 'None':
                    url += str(member.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(member), icon_url=url)
                embed.set_footer(text=f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                embed.title = 'Member unmuted'
                if wh_url is not None:
                    await send_embed_through_wh(embed, wh_url)
                else:
                    await bot.get_channel(mod_channel).send(embed=embed)

        await log_infraction(member, guild, {"type": "Unmute", "Moderator": f"{who}"}, connection)


async def log_warn(bot, guild, member, points, current, warned_by, reason, connection):
    if isinstance(warned_by, discord.Bot):
        warned_by = guild.me
    settings = await connection.fetchrow(
        'SELECT moderation_channel, moderations, mod_webhook FROM modlogs WHERE guild_id=$1', guild.id)
    if settings is not None:
        actions_not_empty = dict(settings)['moderations'] is not None
        mod_channel = dict(settings)['moderation_channel'] if actions_not_empty else None
        actions = dict(settings)['moderations'] if actions_not_empty else None
        wh_url = dict(settings)['mod_webhook'] if actions_not_empty else None
        if isinstance(mod_channel, int) and isinstance(actions, list):
            if "Member Warned" in actions:
                embed = discord.Embed(title="", description="", color=0xbf1408)
                url = ''
                if str(member.avatar) != 'None':
                    url += str(member.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(member), icon_url=url)
                embed.set_footer(text=f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                embed.title = 'Member warned'
                embed.description = f'**Points added:** {points}\n**Current points:** {current}\n**Moderator:** {warned_by} ({warned_by.mention})\n**Reason:** {reason}'
                if wh_url is not None:
                    await send_embed_through_wh(embed, wh_url)
                else:
                    await bot.get_channel(mod_channel).send(embed=embed)

    await log_infraction(member, guild, {"type": "Warn", "Points added": points, "Reason": reason, "Moderator": f"{warned_by}"}, connection)


async def log_tempban(bot, guild, member, time, reason, who, connection):
    settings = await connection.fetchrow(
        'SELECT moderation_channel, moderations, mod_webhook FROM modlogs WHERE guild_id=$1', guild.id)
    if settings is not None:
        actions_not_empty = dict(settings)['moderations'] is not None
        mod_channel = dict(settings)['moderation_channel'] if actions_not_empty else None
        actions = dict(settings)['moderations'] if actions_not_empty else None
        wh_url = dict(settings)['mod_webhook'] if actions_not_empty else None
        if isinstance(mod_channel, int) and isinstance(actions, list):
            if "Member Tempbanned" in actions:
                embed = discord.Embed(title="", description="", color=0xbf1408)
                url = ''
                if str(member.avatar) != 'None':
                    url += str(member.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(member), icon_url=url)
                embed.set_footer(text=f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                embed.title = 'Member tempbanned'
                embed.description = f'**Tempbanned for:** {await t(time)}\n**Reason: **{reason}\n**Moderator: ** {bot.user.name}#{bot.user.discriminator}'
                if wh_url is not None:
                    await send_embed_through_wh(embed, wh_url)
                else:
                    await bot.get_channel(mod_channel).send(embed=embed)

    await log_infraction(member, guild, {"type": "Tempban", "Banned for": await t(time), "Reason": reason, "Moderator": f"{bot.user.name}#{bot.user.discriminator}"}, connection)


async def log_ban(bot, guild, member, reason, who, connection):
    settings = await connection.fetchrow(
        'SELECT moderation_channel, moderations, mod_webhook FROM modlogs WHERE guild_id=$1', guild.id)
    if settings is not None:
        actions_not_empty = dict(settings)['moderations'] is not None
        mod_channel = dict(settings)['moderation_channel'] if actions_not_empty else None
        actions = dict(settings)['moderations'] if actions_not_empty else None
        wh_url = dict(settings)['mod_webhook'] if actions_not_empty else None
        if isinstance(mod_channel, int) and isinstance(actions, list):
            if "Member Banned" in actions:
                embed = discord.Embed(title="", description="", color=0xbf1408)
                url = ''
                if str(member.avatar) != 'None':
                    url += str(member.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(member), icon_url=url)
                embed.set_footer(text=f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                embed.title = 'Member banned'
                embed.description = f'**Reason: **{reason}\n**Moderator: ** {bot.user.name}#{bot.user.discriminator}'
                if wh_url is not None:
                    await send_embed_through_wh(embed, wh_url)
                else:
                    await bot.get_channel(mod_channel).send(embed=embed)
    await connection.execute('DELETE FROM user_infraction_points WHERE memberkey=$1',
                       f"{guild.id}_{member.id}")
    await log_infraction(member, guild, {"type": "Ban", "Reason": reason, "Moderator": f"{bot.user.name}#{bot.user.discriminator}"}, connection)


async def punish_nsfw(bot, user, guild, punishments, table, warn_conn, reason):
    bot_user = f'{bot.user.name}#{bot.user.discriminator}'
    reason = f"Automatic action for {reason}"
    if "Ban" in punishments and await has_permissions(guild.me, user, 'ban_members'):
        await user.ban()
        await handle_send(user, embed=discord.Embed(title=f"You've been banned from {guild}", description=f"**Reason:** {reason}\n**Moderator: **{bot_user}", color=0xf54254))
        await log_ban(bot, guild, user, reason, bot, warn_conn)

    if "Warn" in punishments and table['points'] not in [None, 0]:
        await warn(bot, user, guild, table['points'], warn_conn, reason, bot)
        await handle_send(user, embed=discord.Embed(title=f"You've been warned in {guild}", description=f"**Points added:** {table['points']}\n**Reason:** {reason}\n**Moderator: **{bot_user}", color=0xf54254))
    if "Tempban" in punishments and table['duration'] not in [None, 0] and await has_permissions(guild.me, user, 'ban_members'):
        await tempban(bot, user, reason, table['duration'], guild, bot_user, warn_conn)

    if "Kick" in punishments and await has_permissions(guild.me, user, 'kick_members'):
        await user.kick(reason=reason)
        await handle_send(user,
                          embed=discord.Embed(title=f"You've been kicked from {guild}",
                                              description=f"**Reason:** {reason}\n**Moderator: **{bot_user}", color=0xf54254))
    if "Mute" in punishments and table['duration'] not in [None, 0] and await has_permissions(guild.me, user, 'moderate_members'):
        await user.timeout(until=datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=table['duration']))
        await handle_send(user, embed=discord.Embed(title=f"You've been muted in {guild}",
                                                    description=f"**Duration:** {table['timeval']} {table['timeunit']}\n**Reason:** {reason}\n**Moderator: **{bot_user}", color=0xf54254))
        await log_mute(bot, guild, user, f"{table['timeval']} {table['timeunit']}", reason, bot, warn_conn)


async def log_infraction(member, guild, infraction, connection):
    inf_info = infraction
    inf_info['Time'] = datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')
    info = await connection.fetchrow('select * from infractions where member_id=$1 and guild_id=$2', member.id, guild.id)
    if info is None:
        await connection.execute('insert into infractions (member_id, guild_id, infractions) values ($1, $2, $3)', member.id, guild.id,[json.dumps(inf_info)])
    else:
        infractions = (dict(info))['infractions']
        infractions.append(json.dumps(inf_info))
        await connection.execute('update infractions set infractions=$1 where member_id=$2 and guild_id=$3',
                                 infractions, member.id, guild.id)

