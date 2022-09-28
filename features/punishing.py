import asyncio
from operator import itemgetter
import discord
import datetime
import json


async def handle_send(member, embed):
    try:
        await member.send(embed=embed)
    except:
        print('a')

def time_from_two_vals(time, unit):
    if unit == 'seconds':
        return time
    if unit == 'minutes':
        return 60 * time
    if unit == 'hours':
        return 3600 * time
    if unit == 'days':
        return 86400 * time


def find_max_rule(rules, amount):
    sorted_rules = sorted(rules, key=itemgetter('threshold'))
    for rule in sorted_rules:
        if rule['threshold'] <= amount and len(
                [punish_rule for punish_rule in sorted_rules[sorted_rules.index(rule) + 1:] if
                 punish_rule['threshold'] <= amount]) == 0:
            return rule
    return {'non_violated': 'no rules were violated'}


async def warn(bot, member, guild, amount, connection, reason, who):
    bot_user = f'{bot.user.name}#{bot.user.discriminator}'
    key = f"{guild.id}_{member.id}"
    user = await connection.fetchrow('SELECT * FROM user_infraction_points where memberkey=$1', key)
    old_points = 0
    if user is None:
        await connection.execute('INSERT INTO user_infraction_points (memberkey, points) VALUES ($1, $2)', key, amount)
    else:
        user = dict(user)
        old_points += user['points']
        new_amount = user['points'] + amount
        await connection.execute('UPDATE user_infraction_points SET memberkey=$1, points=$2 where memberkey=$1', key,
                                 new_amount)

    await log_warn(bot, guild, member, amount, old_points + amount, who, reason, connection)

    autopunish = await connection.fetchrow('SELECT * FROM autopunish WHERE guild_id=$1', guild.id)

    if autopunish is not None:
        rules = [eval(rule) for rule in dict(autopunish)['rules']]
    else:
        rules = [{'type':"mute", "durationType": "hours", "duration": 6, "threshold": 15},{'type':"kick", "durationType": "minutes", "duration": 1, "threshold": 30},{'type':"tempban", "durationType": "days", "duration": 3, "threshold": 45},{'type':"ban", "durationType": "minutes", "duration": 1, "threshold": 60}]
    max_rule = find_max_rule(rules, old_points + amount)
    if 'type' in list(max_rule.keys()):
        if max_rule['type'] == 'mute' and old_points < max_rule['threshold']:
            await log_mute(bot, guild, member, f"{max_rule['duration']} {max_rule['durationType']}", f"reaching {max_rule['threshold']} points", bot, connection)
            await member.timeout(until=datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(
                seconds=time_from_two_vals(max_rule['duration'], max_rule['durationType'])))

            await handle_send(member, embed=discord.Embed(title=f"You've been muted in {guild}",
                                                          description=f"**Duration:** {max_rule['duration']} {max_rule['durationType']}\n**Reason:** reaching {max_rule['threshold']} points\n**Moderator: **{bot_user}", color=0xf54254))
        if max_rule['type'] == 'kick' and old_points < max_rule['threshold']:
            await handle_send(member,  embed=discord.Embed(title=f"You've been kicked from {guild}", description=f"**Reason:** reaching {max_rule['threshold']} points\n**Moderator: **{bot_user}", color=0xf54254))
            await member.kick(reason=f"reaching {max_rule['threshold']} points")
        if max_rule['type'] == 'tempban' and old_points < max_rule['threshold']:
            await handle_send(member, embed=discord.Embed(title=f"You've been temporarily banned from {guild}",description=f"**Duration:** {max_rule['duration']} {max_rule['durationType']}\n**Reason:** reaching {max_rule['threshold']} points\n**Moderator: **{bot_user}", color=0xf54254))
            await member.ban(delete_message_days=0)

            await log_tempban(bot, guild, member, f"{max_rule['duration']} {max_rule['durationType']}",
                              f"reaching {max_rule['threshold']} points", bot, connection)
            await asyncio.sleep(time_from_two_vals(max_rule['duration'], max_rule['durationType']))
            await member.unban()
        if max_rule['type'] == 'ban':
            await handle_send(member, embed=discord.Embed(title=f"You've been banned from {guild}", description=f"**Reason:** reaching {max_rule['threshold']} points\n**Moderator: **{bot_user}", color=0xf54254))
            await member.ban(reason=f"reaching {max_rule['threshold']} points", delete_message_days=0)
            await log_ban(bot, guild, member, f"reaching {max_rule['threshold']} points", bot, connection)


async def log_mute(bot, guild, member, time, reason, who, connection):
    settings = await connection.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
    if settings is not None:
        mod_channel = dict(settings)['moderation_channel']
        actions = dict(settings)['moderations']
        if isinstance(mod_channel, int):
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
                await bot.get_channel(mod_channel).send(
                    embed=embed)

    await log_infraction(member, guild, {"type": "Mute", "Muted for": time, "Reason": reason, "Moderator": f"{bot.user.name}#{bot.user.discriminator}"}, connection)


async def log_unmute(bot, guild, member, connection, who):
    settings = await connection.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
    if settings is not None:
        mod_channel = dict(settings)['moderation_channel']
        actions = dict(settings)['moderations']
        if isinstance(mod_channel, int):
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
                await bot.get_channel(mod_channel).send(embed=embed)

        await log_infraction(member, guild, {"type": "Unmute", "Moderator": f"{who}"}, connection)


async def log_warn(bot, guild, member, points, current, warned_by, reason, connection):
    if isinstance(warned_by, discord.Bot):
        warned_by = guild.me
    settings = await connection.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
    if settings is not None:
        mod_channel = dict(settings)['moderation_channel']
        actions = dict(settings)['moderations']
        if isinstance(mod_channel, int):
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
                await bot.get_channel(mod_channel).send(embed=embed)

    await log_infraction(member, guild, {"type": "Warn", "Points added": points, "Reason": reason, "Moderator": f"{warned_by}"}, connection)


async def log_tempban(bot, guild, member, time, reason, who, connection):
    settings = await connection.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
    if settings is not None:
        mod_channel = dict(settings)['moderation_channel']
        actions = dict(settings)['moderations']
        if isinstance(mod_channel, int):
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
                embed.description = f'**Tempbanned for:** {time}\n**Reason: **{reason}\n**Moderator: ** {bot.user.name}#{bot.user.discriminator}'
                await bot.get_channel(mod_channel).send(embed=embed)

    await log_infraction(member, guild, {"type": "Tempban", "Banned for": time, "Reason": reason, "Moderator": f"{bot.user.name}#{bot.user.discriminator}"}, connection)



async def log_ban(bot, guild, member, reason, who, connection):
    settings = await connection.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
    if settings is not None:
        mod_channel = dict(settings)['moderation_channel']
        actions = dict(settings)['moderations']
        if isinstance(mod_channel, int):
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
                await bot.get_channel(mod_channel).send(embed=embed)
                await connection.execute('DELETE FROM user_infraction_points WHERE memberkey=$1',
                                   f"{guild.id}_{member.id}")
    await log_infraction(member, guild, {"type": "Ban", "Reason": reason, "Moderator": f"{bot.user.name}#{bot.user.discriminator}"}, connection)



async def punish_nsfw(bot, user, guild, punishments, table, warn_conn, reason):
    bot_user = f'{bot.user.name}#{bot.user.discriminator}'
    reason = f"Automatic action for {reason}"
    if "Ban" in punishments:
        await handle_send(user, embed=discord.Embed(title=f"You've been banned from {guild}", description=f"**Reason:** {reason}\n**Moderator: **{bot_user}", color=0xf54254))
        await user.ban(delete_message_days=0)
        await log_ban(bot, guild, user, reason, bot, warn_conn)

    if "Warn" in punishments and table['points'] not in [None, 0]:
        await warn(bot, user, guild, table['points'], warn_conn, reason, bot)
        await handle_send(user, embed=discord.Embed(title=f"You've been warned in {guild}", description=f"**Points added:** {table['points']}\n**Reason:** {reason}\n**Moderator: **{bot_user}", color=0xf54254))
    if "Tempban" in punishments and table['duration'] not in [None, 0]:
        await handle_send(user, embed=discord.Embed(title=f"You've been temporarily banned from {guild}",
                                                    description=f"**Duration: **{table['timeval']} {table['timeunit']}\n**Reason:** {reason}\n**Moderator: **{bot_user}", color=0xf54254))
        await user.ban(reason=reason, delete_message_days=0)
        await log_tempban(bot, guild, user, f"{table['timeval']} {table['timeunit']}", reason, bot, warn_conn)
        await asyncio.sleep(table['duration'])
        await user.unban()
    if "Kick" in punishments:
        await handle_send(user,
                          embed=discord.Embed(title=f"You've been kicked from {guild}",
                                              description=f"**Reason:** {reason}\n**Moderator: **{bot_user}", color=0xf54254))
        await user.kick(reason=reason)
    if "Mute" in punishments and table['duration'] not in [None, 0]:
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




def setup(bot):
    print('')