import asyncio
import datetime
from datetime import timezone
import discord
import aiohttp

from features.punishing import log_infraction

dbpass = 'mysecretpassword'
unknown = 'Unknown (I need audit log permissions to access this)'
default_avatar = 'https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/198142ac-f410-423a-bf0b-34c9cb5d9609/dbtif5j-60306864-d6b7-44b6-a9ff-65e8adcfb911.png?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7InBhdGgiOiJcL2ZcLzE5ODE0MmFjLWY0MTAtNDIzYS1iZjBiLTM0YzljYjVkOTYwOVwvZGJ0aWY1ai02MDMwNjg2NC1kNmI3LTQ0YjYtYTlmZi02NWU4YWRjZmI5MTEucG5nIn1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmZpbGUuZG93bmxvYWQiXX0.pRh5DK_cxlZ6SxVPqoUSsSNo1fqksJVP6ECGVUi6kmE'
webhook_pfp = "https://cdn.discordapp.com/attachments/1274041694018469980/1356831963679293481/MndBTSfgkAAAAASUVORK5CYII.png?ex=67eff9fc&is=67eea87c&hm=95f641dcd59f677052f202e1c8dd7f192d67384ed09dcf968bf9405d4a259498&"
d = {}
with open('tk.json', 'r+') as f:
    info = eval(f.read())['db']
    for key in list(info.keys()):
        d[key] = info[key]


async def get_invite(before, after):
    old_invites = await before.invites()
    new_invites = await after.invites()
    if len(old_invites) == len(new_invites):
        for i in range(len(old_invites)):
            if new_invites[i].uses > old_invites[i].uses:
                return new_invites[i]

    else:
        for i in range(len(new_invites)):
            if new_invites[i] not in old_invites:
                return new_invites[i]


def get_content(messages):
    message_content = []
    for message in messages:
        message_content.append(f"{len(message_content)+1}. {message.content}")
    return message_content


def t(time):
    day = time // (24 * 3600)
    time = time % (24 * 3600)
    hour = time // 3600
    time %= 3600
    minutes = time // 60
    time %= 60
    seconds = time
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

async def send_embed_through_wh(embed, webhook_url):
    embed_data = embed.to_dict()

    payload = {
        "username": "AMGX's Logging Minion",
        "avatar": webhook_pfp,
        "embeds": [embed_data]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload) as response:
            pass


async def send_embeds_through_wh(embeds, webhook_url):
    payload = {
        "username": "AMGX's Logging Minion",
        "avatar_url": webhook_pfp,
        "embeds": [embed.to_dict() for embed in embeds]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload) as response:
            pass



#
# async def connections():
#     global conn
#     conn = await asyncpg.create_pool(host=d['host'], port=d['port'], user=d['user'], password=d['pwd'],
#                                      database=d['db'])


def has_guild_permissions(b, permission):
    bot_perms = dict(list(b.guild_permissions))
    if bot_perms[permission]:
        return True
    return False


update_clr = 0x5797f7
add_clr = 0x78ff9c
remove_clr = 0xff3d3d
punish_clr = 0xbf1408
unpunish_clr = 0x68f286
log_actions = {"Message Events": ["Message Deleted", "Message Edited", "Message Bulk Deletion"], "Member Events": [
    "Username Changed", "Avatar Changed", "Custom Status Changed", "Nickname Changed", "Roles Changed", "Member Joined",
    "Member Left"], "Moderation Events": ["Member Warned", "Infraction Removed", "Member Muted", "Member Unmuted",
                                          "Member Kicked", "Member Tempbanned",
                                          "Member Banned", "Member Unbanned"],
               "Server Changes": ["Emoji Added", "Emoji Updated", "Emoji Deleted", "Channel Created", "Channel Updated",
                                  "Channel Deleted"
                   , "Role Created", "Role Updated", "Role Deleted", "Server Name Changed", "Server Icon Changed",
                                  "Discovery Splash Changed", "AFK Channel Changed", "System Channel Changed",
                                  "Default Notifications Changed", "AFK Timeout Changed", "Bot Added",
                                  "Bot Removed", "Invite Splash Changed", "Banner Changed", "Explicit Filter Changed",
                                  "Verification Level Changed", "Invite Created", "Invite Deleted", "MFA Changed",
                                  "Server Owner Changed"], "Voice Channel Events": ["Member Joined VC",
                                                                                    "Member Left VC", "Member Moved"]}

cant_fetch = discord.Embed(title='Channel overwrites updated',
                           description='Could not fetch details. I need view audit log permissions.')

gone_members = {}


async def message_edit(conn, bot, before, after):
    settings = await conn.fetchrow('SELECT message_channel, message_actions, msg_webhook FROM modlogs WHERE guild_id=$1',
                                   after.guild.id)

    if settings is not None:
        actions_not_empty = dict(settings)['message_actions'] is not None
        message_log_channel = dict(settings)['message_channel'] if actions_not_empty else None
        actions = dict(settings)['message_actions'] if actions_not_empty else log_actions['Message Events']
        wh_url = dict(settings)['msg_webhook'] if actions_not_empty else None

    else:
        message_log_channel = None
        actions = log_actions['Message Events']
        wh_url = None
    if isinstance(message_log_channel,
                  int) and 'Message Edited' in actions and before.content != after.content:
        ch = bot.get_channel(message_log_channel)
        embed = discord.Embed(title=f"Message edited in #{bot.get_channel(before.channel.id)}",
                              description=f"**Old message:** {before.content}\n**New message:** {after.content}\n",
                              color=update_clr)
        url = ''
        if str(after.author.avatar) != 'None':
            url += str(after.author.avatar)
        else:
            url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
        embed.set_author(name=str(after.author), icon_url=url)
        embed.set_footer(
            text=f"Message ID: {after.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
        if wh_url is not None:
            await send_embed_through_wh(embed, wh_url)
        else:
            await ch.send(embed=embed)


async def message_delete(conn, bot, message):
    settings = await conn.fetchrow('SELECT message_channel, message_actions, msg_webhook FROM modlogs WHERE guild_id=$1',
                                   message.guild.id)

    if settings is not None:
        actions_not_empty = dict(settings)['message_actions'] is not None
        message_log_channel = dict(settings)['message_channel'] if actions_not_empty else None
        actions = dict(settings)['message_actions'] if actions_not_empty else log_actions['Message Events']
        wh_url = dict(settings)['msg_webhook'] if actions_not_empty else None

    else:
        message_log_channel = None
        actions = log_actions['Message Events']
        wh_url = None

    if isinstance(message_log_channel, int) and 'Message Deleted' in actions and message.content != '':
        ch = bot.get_channel(message_log_channel)
        embed = discord.Embed(title=f"Message deleted in #{bot.get_channel(message.channel.id)}",
                              description=f"**Content:** {message.content}", color=remove_clr)
        url = ''
        if str(message.author.avatar) != 'None':
            url += str(message.author.avatar)
        else:
            url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
        embed.set_author(name=str(message.author), icon_url=url)
        embed.set_footer(
            text=f"Message ID: {message.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
        if wh_url is not None:
            await send_embed_through_wh(embed, wh_url)
        else:
            await ch.send(embed=embed)


async def raw_bulk_message_delete(conn, bot, payload):
    settings = await conn.fetchrow('SELECT message_channel, message_actions, msg_webhook FROM modlogs WHERE guild_id=$1',
                                   payload.guild_id)
    if settings is not None:
        actions_not_empty = dict(settings)['message_actions'] is not None
        message_log_channel = dict(settings)['message_channel'] if actions_not_empty else None
        actions = dict(settings)['message_actions'] if actions_not_empty else log_actions['Message Events']
        wh_url = dict(settings)['msg_webhook'] if actions_not_empty else None
    else:
        message_log_channel = None
        actions = log_actions['Message Events']
        wh_url = None

    messages = get_content(payload.cached_messages)
    guild = bot.get_guild(payload.guild_id)
    if has_guild_permissions(guild.me, 'view_audit_log'):
        u = (await guild.audit_logs(limit=1, action=discord.AuditLogAction.message_bulk_delete).flatten())[0].user
        user = f"{u}({u.mention})"
    else:
        user = unknown
    if isinstance(message_log_channel, int) and 'Message Bulk Deletion' in actions and len(
            payload.cached_messages) > 0:
        channel = bot.get_channel(payload.channel_id)
        ch = bot.get_channel(message_log_channel)
        string = "\n".join(messages)
        embed = discord.Embed(title=f"Messages bulk deleted in #{channel}", color=remove_clr, description="")
        if len(f"### __Deleted messages:__\n{string}\n\n### _Deleted by:__ {user}") > 4096:
            embed.description += f"### __Deleted messages:__ Too many to show (total length above 4096).\n\n### __Deleted by:__ {user}"
        else:
            embed.description += f"### __Deleted messages:__\n{string}\n\n### Deleted by: {user}"

        embed.set_footer(
            text=f"Channel ID: {payload.channel_id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
        if wh_url is not None:
            await send_embed_through_wh(embed, wh_url)
        else:
            await ch.send(embed=embed)


# members


async def handle_send(member, embed):
    try:
        await member.send(embed=embed)
    except:
        pass


async def displayname_handle(conn, bot, before, after):
    if before.display_name != after.display_name:
        settings = await conn.fetchrow('SELECT member_channel, member_actions, member_webhook FROM modlogs WHERE guild_id=$1',
                                       before.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['member_actions'] is not None
            member_log_channel = dict(settings)['member_channel'] if actions_not_empty else None
            actions = dict(settings)['member_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['member_webhook'] if actions_not_empty else None
        else:
            member_log_channel = None
            actions = log_actions['Member Events']
            wh_url = None

        if "Username Changed" in actions and isinstance(member_log_channel, int):
            embed = discord.Embed(title="Display name changed",
                                  description=f"**Old display name:** {before.name}\n**New display name:** {after.name}",
                                  color=update_clr)
            embed.set_footer(text=f"{datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            url = ''
            if str(after.avatar) != 'None':
                url += str(after.avatar)
            else:
                url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
            embed.set_author(name=str(after), icon_url=url)
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(member_log_channel).send(embed=embed)



async def user_update(conn, bot, before, after):
    for guild in after.mutual_guilds:
        settings = await conn.fetchrow(
            'SELECT member_channel, member_actions, member_webhook FROM modlogs WHERE guild_id=$1',
            guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['member_actions'] is not None
            member_log_channel = dict(settings)['member_channel'] if actions_not_empty else None
            actions = dict(settings)['member_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['member_webhook'] if actions_not_empty else None
        else:
            member_log_channel = None
            actions = log_actions['Member Events']
            wh_url = None
        if before.name != after.name and "Username Changed" in actions and isinstance(member_log_channel, int):
            embed = discord.Embed(title="Name changed",
                                  description=f"**Old username:** {before.name}\n**New username:** {after.name}",
                                  color=update_clr)
            embed.set_footer(text=f"{datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            url = ''
            if str(after.avatar) != 'None':
                url += str(after.avatar)
            else:
                url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
            embed.set_author(name=str(after), icon_url=url)
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(member_log_channel).send(embed=embed)

        if before.global_name != after.global_name and "Username Changed" in actions and isinstance(member_log_channel,
                                                                                                    int):
            embed = discord.Embed(title="Display name changed",
                                  description=f"**Old display name:** {before.global_name}\n**New display name:** {after.global_name}",
                                  color=update_clr)
            embed.set_footer(text=f"{datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            url = ''
            if str(after.avatar) != 'None':
                url += str(after.avatar)
            else:
                url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
            embed.set_author(name=str(after), icon_url=url)
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(member_log_channel).send(embed=embed)

        if str(before.avatar) != str(after.avatar) and "Avatar Changed" in actions and isinstance(
                member_log_channel, int) and not after.bot:
            embed = discord.Embed(title="Avatar changed", color=update_clr)
            embed.set_footer(
                text=f"Member ID: {after.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            embed.set_image(url=str(after.avatar))
            embed.set_author(name=str(after))
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(member_log_channel).send(embed=embed)


async def member_join(conn, bot, member, tracker):
    try:
        del gone_members[member.id]
    except KeyError:
        pass

    guild = member.guild
    settings = await conn.fetchrow(
        'SELECT member_channel, member_actions, member_webhook FROM modlogs WHERE guild_id=$1',
        guild.id)
    if settings is not None:
        actions_not_empty = dict(settings)['member_actions'] is not None
        member_log_channel = dict(settings)['member_channel'] if actions_not_empty else None
        actions = dict(settings)['member_actions'] if actions_not_empty else log_actions['Member Events']
        wh_url = dict(settings)['member_webhook'] if actions_not_empty else None
    else:
        member_log_channel = None
        actions = log_actions['Member Events']
        wh_url = None

    if not member.bot and isinstance(member_log_channel, int) and "Member Joined" in actions:
        if has_guild_permissions(guild.me, 'manage_guild'):
            try:
                inv_info = await tracker.fetch_inviter(member)
                inviter = inv_info[1]
                invite = inv_info[0]
                info = {'Created': t(
                    int((datetime.datetime.now(timezone.utc) - member.created_at).total_seconds())),
                    'Invited by': f"{inviter.name} ({inviter.mention})", 'Code used': invite.code,
                    'Number of times code has been used': invite.uses + 1}
            except Exception as e:
                print(e)
                info = {'Created': t(int((datetime.datetime.now(timezone.utc) - member.created_at).total_seconds())),
                    'Invited by': f"Could not fetch"}
        else:
            info = {'Created': int((datetime.datetime.now(timezone.utc) - member.created_at).total_seconds()),
                    'Invited by': 'Failed to fetch: I need manage server permissions to access'}
        embed = discord.Embed(title="Member joined", color=add_clr)
        description = ''
        for piece in info:
            description += f"**{piece}:** {info[piece]}\n"
        embed.description = description
        url = ''
        if str(member.avatar) != 'None':
            url += str(member.avatar)
        else:
            url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
        embed.set_author(name=str(member), icon_url=url)
        embed.set_footer(
            text=f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
        if wh_url is not None:
            await send_embed_through_wh(embed, wh_url)
        else:
            await bot.get_channel(member_log_channel).send(embed=embed)


async def member_remove(conn, bot, member):
    if len(member.mutual_guilds) == 0 and member.dm_channel is None:
        gone_members[member.id] = member

    settings = await conn.fetchrow(
        'SELECT member_channel, member_actions, member_webhook FROM modlogs WHERE guild_id=$1',
        member.guild.id)
    if settings is not None:
        actions_not_empty = dict(settings)['member_actions'] is not None
        member_log_channel = dict(settings)['member_channel'] if actions_not_empty else None
        actions = dict(settings)['member_actions'] if actions_not_empty else log_actions['Member Events']
        wh_url = dict(settings)['member_webhook'] if actions_not_empty else None
    else:
        member_log_channel = None
        actions = log_actions['Member Events']
        wh_url = None

    if "Member Left" in actions and isinstance(member_log_channel, int):
        if has_guild_permissions(member.guild.me, 'view_audit_log'):
            leave_event = [e for e in
                           (await member.guild.audit_logs(limit=1).flatten()) if
                           e.target.id == member.id and e.action == discord.AuditLogAction.kick and abs((datetime.datetime.now(tz=timezone.utc) - e.created_at).total_seconds()) < 3]
        else:
            leave_event = []

        if len(leave_event) == 0:
            if not member.bot:
                embed = discord.Embed(title="", description="", color=remove_clr)
                url = ''
                if str(member.avatar) != 'None':
                    url += str(member.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(member), icon_url=url)
                embed.set_footer(
                    text=f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                embed.title = "Member left"
                if wh_url is not None:
                    await send_embed_through_wh(embed, wh_url)
                else:
                    await bot.get_channel(member_log_channel).send(embed=embed)


async def member_ban(user):
    if len(user.mutual_guilds) == 0 and user.dm_channel is None:
        gone_members[user.id] = user


async def voice_state_update(conn, bot, member, before, after):
    guild = member.guild
    settings = await conn.fetchrow('SELECT voicestate_channel, vc_actions, vc_webhook FROM modlogs WHERE guild_id=$1', guild.id)
    if settings is not None:
        actions_not_empty = dict(settings)['vc_actions'] is not None
        vc_channel = dict(settings)['voicestate_channel'] if actions_not_empty else None
        actions = dict(settings)['vc_actions'] if actions_not_empty else log_actions['Member Events']
        wh_url = dict(settings)['vc_webhook'] if actions_not_empty else None
    else:
        vc_channel = None
        actions = log_actions['Voice Channel Events']
        wh_url = None

    embed_info = {"footer": f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}"}
    if isinstance(vc_channel, int):
        if before.channel is not None and after.channel is not None and "Member Moved" in actions and before.channel != after.channel:
            await asyncio.sleep(0.5)
            if has_guild_permissions(member.guild.me, 'view_audit_log'):
                event = await after.channel.guild.audit_logs(limit=1).flatten()
            else:
                event = []
            if len(event) > 0:
                if event[0].action == discord.AuditLogAction.member_move and event[0].extra.channel.id == after.channel.id and abs((datetime.datetime.now(tz=timezone.utc) - event[0].created_at).total_seconds()) < 1.2:
                    user = event[0].user
                    embed_info['title'] = "Member moved"
                    embed_info[
                        'info'] = f'**Moved from:** {before.channel.mention}\n**Moved to:** {after.channel.mention}\n**Moved by:** {user.name} ({user.mention})'
                else:
                    embed_info['title'] = "Member switched voice channel"
                    embed_info[
                        'info'] = f'**Went from:** {before.channel.mention}\n**Went to:** {after.channel.mention}'
            else:
                embed_info['title'] = "Member switched voice channel"
                embed_info[
                    'info'] = f'**Went from:** {before.channel.mention}\n**Went to:** {after.channel.mention}'
            embed_info['color'] = update_clr
        elif after.channel is not None and before.channel is None and "Member Joined VC" in actions:
            embed_info['title'] = "Member joined voice channel"
            embed_info['info'] = f'**Channel:** {after.channel.mention}'
            embed_info['color'] = add_clr
        elif after.channel is None and before.channel is not None and "Member Left VC" in actions:
            embed_info['title'] = "Member left voice channel"
            embed_info['info'] = f'**Channel:** {before.channel.mention}'
            embed_info['color'] = remove_clr
        embed = discord.Embed(title=embed_info['title'], description=embed_info['info'], color=embed_info['color'])
        url = ''
        if str(member.avatar) != 'None':
            url += str(member.avatar)
        else:
            url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
        embed.set_author(name=str(member), icon_url=url)
        embed.set_footer(text=embed_info['footer'])
        if wh_url is not None:
            await send_embed_through_wh(embed, wh_url)
        else:
            await bot.get_channel(vc_channel).send(embed=embed)


def get_user(bot, user_id):
    user = bot.get_user(user_id)
    if user is None:
        return gone_members[user_id]
    return user


async def audit_log_handle(conn, bot, entry):

    user = f"{entry.user.name} ({entry.user.mention})"

    # member events
    if entry.action == discord.AuditLogAction.member_update:

        if hasattr(entry.changes.before, 'nick'):
            settings = await conn.fetchrow('SELECT member_channel, member_actions, member_webhook FROM modlogs WHERE guild_id=$1',
                                           entry.target.guild.id)
            if settings is not None:
                actions_not_empty = dict(settings)['member_actions'] is not None
                member_log_channel = dict(settings)['member_channel'] if actions_not_empty else None
                actions = dict(settings)['member_actions'] if actions_not_empty else log_actions['Member Events']
                wh_url = dict(settings)['member_webhook'] if actions_not_empty else None
            else:
                member_log_channel = None
                actions = log_actions['Member Events']
                wh_url = None

            if isinstance(member_log_channel, int) and "Nickname Changed" in actions:
                embed = discord.Embed(title="Nickname changed",
                                      description=f"**Old nickname:** {entry.target.global_name if entry.changes.before.nick is None else entry.changes.before.nick}\n**New nickname:** {entry.target.global_name if entry.changes.after.nick is None else entry.changes.after.nick}\n**Changed by:** {user}",
                                      color=update_clr)
                embed.set_footer(
                    text=f"Member ID: {entry.target.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                url = ''
                if str(entry.target.avatar) != 'None':
                    url += str(entry.target.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(entry.target), icon_url=url)
                if wh_url is not None:
                    await send_embed_through_wh(embed, wh_url)
                else:
                    await bot.get_channel(member_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.member_role_update:
        settings = await conn.fetchrow('SELECT member_channel, member_actions FROM modlogs WHERE guild_id=$1',
                                       entry.target.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['member_actions'] is not None
            member_log_channel = dict(settings)['member_channel'] if actions_not_empty else None
            actions = dict(settings)['member_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['member_webhook'] if actions_not_empty else None
        else:
            member_log_channel = None
            actions = log_actions['Member Events']
            wh_url = None

        if isinstance(member_log_channel, int) and "Roles Changed" in actions:
            before = entry.changes.before
            after = entry.changes.after

            if len(before.roles) < len(after.roles):
                added_role = [role for role in after.roles if role not in before.roles][0].mention
                embed = discord.Embed(title="Role added",
                                      description=f"**Role added:** {added_role}\n**Added by:** {user}",
                                      color=update_clr)
                embed.set_footer(text=f"Member ID: {entry.target.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                url = ''
                if str(entry.target.avatar) != 'None':
                    url += str(entry.target.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(entry.target), icon_url=url)
                await bot.get_channel(member_log_channel).send(embed=embed)
            else:
                removed_role = [role for role in before.roles if role not in after.roles][0].mention
                embed = discord.Embed(title="Role removed",
                                      description=f"**Role removed:** {removed_role}\n**Removed by:** {user}",
                                      color=update_clr)
                embed.set_footer(
                    text=f"Member ID: {entry.target.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                url = ''
                if str(entry.target.avatar) != 'None':
                    url += str(entry.target.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(entry.target), icon_url=url)
                if wh_url is not None:
                    await send_embed_through_wh(embed, wh_url)
                else:
                    await bot.get_channel(member_log_channel).send(embed=embed)

    # moderation events

    if entry.action == discord.AuditLogAction.member_update:
        if hasattr(entry.changes.before, 'communication_disabled_until'):
            settings = await conn.fetchrow('SELECT moderation_channel, moderations FROM modlogs WHERE guild_id=$1',
                                           entry.target.guild.id)

            if settings is not None:
                if dict(settings)['moderations'] is not None:
                    mod_channel = dict(settings)['moderation_channel']
                    actions = dict(settings)['moderations']
                else:
                    mod_channel = None
                    actions = log_actions['Moderation Events']
            else:
                mod_channel = None
                actions = log_actions['Moderation Events']

            if "Member Muted" in actions and isinstance(mod_channel, int) and entry.user.id != 834072169507848273 and entry.target.timed_out:

                embed = discord.Embed(title="Member muted",
                                      description=f"**Muted for:** {t(int((entry.target.communication_disabled_until - datetime.datetime.now(tz=datetime.timezone.utc)).total_seconds()))}\n**Reason:** {entry.reason}\n**Moderator:** {user} ",
                                      color=punish_clr)
                url = ''
                if str(entry.target.avatar) != 'None':
                    url += str(entry.target.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(entry.target), icon_url=url)
                embed.set_footer(
                    text=f"Member ID: {entry.target.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                await bot.get_channel(mod_channel).send(embed=embed)

                if not entry.user.id != 834072169507848273:
                    await entry.target.send(embed=discord.Embed(title=f"You've been muted in {entry.target.guild}",
                                                         description=f"**Duration:** {t(int((entry.target.communication_disabled_until - datetime.datetime.now(tz=datetime.timezone.utc)).total_seconds()) + 1)}\n**Reason:** {entry.reason}\n**Moderator: **{user}",
                                                         color=0xf54254))
                    await log_infraction(entry.target, entry.target.guild, {"type": "Mute", "Muted for": t(int((
                                                                                                         entry.target.communication_disabled_until - datetime.datetime.now(
                                                                                                     tz=datetime.timezone.utc)).total_seconds())),
                                                              "Reason": entry.reason, "Moderator": str(entry.user)},
                                         conn)

            if "Member Unmuted" in actions and isinstance(mod_channel, int) and entry.user.id != 834072169507848273 and not entry.target.timed_out:

                embed = discord.Embed(title="Member unmuted",
                                      description=f"**Moderator:** {user}",
                                      color=unpunish_clr)
                url = ''
                if str(entry.target.avatar) != 'None':
                    url += str(entry.target.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(entry.target), icon_url=url)
                embed.set_footer(
                    text=f"Member ID: {entry.target.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                await bot.get_channel(mod_channel).send(embed=embed)

                if entry.user.id != 834072169507848273:
                    await entry.target.send(embed=discord.Embed(title=f"You've been unmuted in {entry.target.guild}",
                                                         description=f"**Moderator: **{user}", color=0x33f25c))
                    await log_infraction(entry.target, entry.target.guild, {"type": "Unmute", "Moderator": str(entry.user)},
                                         conn)

    if entry.action == discord.AuditLogAction.kick:
        await asyncio.sleep(0.5)
        if entry.target is None:
            member = get_user(bot, entry._target_id)
        else:
            member = entry.target

        if not member.bot:
            settings = await conn.fetchrow('SELECT moderation_channel, moderations, mod_webhook FROM modlogs WHERE guild_id=$1',
                                           entry.guild.id)
            if settings is not None:
                actions_not_empty = dict(settings)['moderations'] is not None
                mod_channel = dict(settings)['moderation_channel'] if actions_not_empty else None
                actions = dict(settings)['moderations'] if actions_not_empty else log_actions['Member Events']
                wh_url = dict(settings)['mod_webhook'] if actions_not_empty else None
            else:
                mod_channel = None
                actions = log_actions['Moderation Events']
                wh_url = None
            if "Member Kicked" in actions and isinstance(mod_channel, int):
                embed = discord.Embed(title="Member kicked",
                                      description=f"**Reason:** {entry.reason}\n**Moderator:** {user}",
                                      color=punish_clr)
                url = ''
                if str(member.avatar) != 'None':
                    url += str(member.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(member), icon_url=url)
                embed.set_footer(
                    text=f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                if wh_url is not None:
                    await send_embed_through_wh(embed, wh_url)
                else:
                    await bot.get_channel(mod_channel).send(embed=embed)
            if not entry.user.id == 834072169507848273 and not member.bot:
                try:
                    await member.send(
                        embed=discord.Embed(title=f"You've been kicked from {entry.guild}",
                                            description=f"**Reason: **{entry.reason}\n**Moderator: ** {entry.user}",
                                            color=0xf54254))
                except:
                    pass
                await log_infraction(member, entry.guild, {"type": "Kick", "Reason": entry.reason,
                                                            "Moderator": str(entry.user)}, conn)

        if member.bot:
            settings = await conn.fetchrow('SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
                                           entry.guild.id)
            if settings is not None:
                actions_not_empty = dict(settings)['server_actions'] is not None
                server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
                actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
                wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
            else:
                server_log_channel = None
                actions = log_actions['Server Changes']
                wh_url = None
            if "Bot Removed" in actions and isinstance(server_log_channel, int):
                embed = discord.Embed(title="Bot removed",
                                      description=f"**Removed by:** {user}",
                                      color=remove_clr)
                url = ''
                if str(member.avatar) != 'None':
                    url += str(member.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(member), icon_url=url)
                embed.set_footer(
                    text=f"Bot ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                if wh_url is not None:
                    await send_embed_through_wh(embed, wh_url)
                else:
                    await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.ban:
        await asyncio.sleep(0.5)
        member = get_user(bot, entry._target_id)
        if not member.bot:
            settings = await conn.fetchrow('SELECT moderation_channel, moderations, mod_webhook FROM modlogs WHERE guild_id=$1',
                                           entry.guild.id)

            if settings is not None:
                actions_not_empty = dict(settings)['moderations'] is not None
                mod_channel = dict(settings)['moderation_channel'] if actions_not_empty else None
                actions = dict(settings)['moderations'] if actions_not_empty else log_actions['Member Events']
                wh_url = dict(settings)['mod_webhook'] if actions_not_empty else None
            else:
                mod_channel = None
                actions = log_actions['Moderation Events']
                wh_url = None

            if "Member Banned" in actions and isinstance(mod_channel, int):
                if entry.user.id != bot.user.id and not member.bot:
                    embed = discord.Embed(title="Member banned",
                                          description=f"**Reason:** {entry.reason}\n**Moderator:** {user}",
                                          color=punish_clr)
                    url = ''
                    if str(member.avatar) != 'None':
                        url += str(member.avatar)
                    else:
                        url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                    embed.set_author(name=str(member), icon_url=url)
                    embed.set_footer(
                        text=f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                    if wh_url is not None:
                        await send_embed_through_wh(embed, wh_url)
                    else:
                        await bot.get_channel(mod_channel).send(embed=embed)
            if entry.user.id != 834072169507848273 and not member.bot:
                await conn.execute('DELETE FROM user_infraction_points WHERE memberkey=$1', f"{entry.guild.id}_{member.id}")
                try:
                    await member.send(
                        embed=discord.Embed(title=f"You've been banned from {entry.guild}",
                                            description=f"**Reason: **{entry.reason}\n**Moderator: ** {entry.user}", color=0xf54254))
                except:
                    pass
                await log_infraction(member, entry.guild, {"type": "Ban", "Reason": entry.reason, "Moderator": str(entry.user)},
                                     conn)
        if member.bot:
            settings = await conn.fetchrow('SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
                                           entry.guild.id)
            if settings is not None:
                actions_not_empty = dict(settings)['server_actions'] is not None
                server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
                actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
                wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
            else:
                server_log_channel = None
                actions = log_actions['Server Changes']
                wh_url = None
            if "Bot Removed" in actions and isinstance(server_log_channel, int):
                embed = discord.Embed(title="Bot removed",
                                      description=f"**Removed by:** {user}",
                                      color=remove_clr)
                url = ''
                if str(member.avatar) != 'None':
                    url += str(member.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(member), icon_url=url)
                embed.set_footer(
                    text=f"Bot ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                if wh_url is not None:
                    await send_embed_through_wh(embed, wh_url)
                else:
                    await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.unban:
        await asyncio.sleep(0.5)
        member = get_user(bot, entry._target_id)
        settings = await conn.fetchrow('SELECT moderation_channel, moderations FROM modlogs WHERE guild_id=$1',
                                       entry.guild.id)

        if settings is not None:
            actions_not_empty = dict(settings)['moderations'] is not None
            mod_channel = dict(settings)['moderation_channel'] if actions_not_empty else None
            actions = dict(settings)['moderations'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['mod_webhook'] if actions_not_empty else None
        else:
            mod_channel = None
            actions = log_actions['Moderation Events']
            wh_url = None

        if "Member Unbanned" in actions and isinstance(mod_channel, int) and not entry.user.id == bot.user.id:

            embed = discord.Embed(title="Member unbanned",
                                  description=f"**Moderator:** {user}",
                                  color=unpunish_clr)
            url = ''
            if str(member.avatar) != 'None':
                url += str(member.avatar)
            else:
                url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
            embed.set_author(name=str(member), icon_url=url)
            embed.set_footer(
                text=f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(mod_channel).send(embed=embed)
        await handle_send(member, discord.Embed(title=f"You've been unbanned from {entry.guild}",
                                              description=f"**Moderator: ** {entry.user}", color=0x33f25c))
        await log_infraction(member, entry.guild, {"type": "Unban", "Moderator": str(entry.user)}, conn)




    # guild edits

    if entry.action == discord.AuditLogAction.guild_update:
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            entry.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int):
            embeds = []

            embed = discord.Embed(title='Server updated',
                                  description=f"**Updated by:** {user}",
                                  color=update_clr)

            before_info = ""
            after_info = ""

            if hasattr(entry.changes.before, 'verification_level') and 'Verification Level Changed' in actions:
                before_info += f"**Verification level:** {entry.changes.before.verification_level.name}      \n"
                after_info += f"**Verification level:** {entry.changes.after.verification_level.name}      \n"

            if hasattr(entry.changes.before, 'name') and 'Server Name Changed' in actions:
                before_info += f"**Name:** {entry.changes.before.name}      \n"
                after_info += f"**Name:** {entry.changes.after.name}      \n"

            if hasattr(entry.changes.before, 'mfa_level') and 'MFA Changed' in actions:
                mfa_dict = {0: 'not required', 1: 'required'}
                before_info += f"**MFA level:** {mfa_dict[entry.changes.before.mfa_level]}      \n"
                after_info += f"**MFA level:** {mfa_dict[entry.changes.after.mfa_level]}      \n"

            if hasattr(entry.changes.before, 'explicit_content_filter') and 'Explicit Filter Changed' in actions:
                before_info += f"**Explicit filter:** {entry.changes.before.explicit_content_filter}      \n"
                after_info += f"**Explicit filter:** {entry.changes.after.explicit_content_filter}      \n"

            if hasattr(entry.changes.before, 'owner') and 'Server Owner Changed' in actions:
                before_info += f"**Owner:** {entry.changes.before.owner}      \n"
                after_info += f"**Owner:** {entry.changes.after.owner_id}      \n"

            if hasattr(entry.changes.before, 'afk_channel') and 'AFK Channel Changed' in actions:
                before_info += f"**AFK channel: ** {[entry.changes.before.afk_channel.mention if entry.changes.before.afk_channel is not None else 'None'][0]}      \n"
                after_info += f"**AFK channel: ** {[entry.changes.after.afk_channel.mention if entry.changes.after.afk_channel is not None else 'None'][0]}      \n"

            if hasattr(entry.changes.before, 'system_channel') and 'System Channel Changed' in actions:
                before_info += f"**System channel: ** {[entry.changes.before.system_channel.mention if entry.changes.before.system_channel is not None else 'None'][0]}      \n"
                after_info += f"**System channel: ** {[entry.changes.after.system_channel.mention if entry.changes.after.system_channel is not None else 'None'][0]}      \n"

            if hasattr(entry.changes.before, 'default_notifications') and 'Default Notifications Changed' in actions:
                before_info += f"**Default notification settings: ** {entry.changes.before.default_notifications.name}      \n"
                after_info += f"**Default notification settings: ** {entry.changes.after.default_notifications.name}      \n"

            if hasattr(entry.changes.before, 'afk_timeout') and "AFK Timeout Changed" in actions:
                before_info += f"**AFK timeout: ** {entry.changes.before.afk_timeout}      \n"
                after_info += f"**AFK timeout: ** {entry.changes.after.afk_timeout}      \n"

            if not (before_info == '' and after_info == ''):
                embed.add_field(name='Before', value=before_info)
                embed.add_field(name='After', value=after_info)
                embed.set_footer(text=datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S'))
                embeds.append(embed)

            if hasattr(entry.changes.before, 'icon') and 'Server Icon Changed' in actions:
                embed_info = {'title': 'Server icon changed',
                              'updater': user,
                              'footer': f"{datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}"}
                e = discord.Embed(title=embed_info['title'], description=f"**Changed by:** {embed_info['updater']}")
                url = ''
                if str(entry.changes.after.icon) == 'None':
                    url += default_avatar
                else:
                    url = str(entry.changes.after.icon)
                e.set_image(url=url)
                e.set_footer(text=embed_info['footer'])
                embeds.append(e)

            if hasattr(entry.changes.before, 'splash') and 'Invite Splash Changed' in actions:
                embed_info = {'title': 'Invite splash changed',
                              'updater': user,
                              'footer': f"{datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}"}
                e = discord.Embed(title=embed_info['title'], description=f"**Changed by:** {embed_info['updater']}")
                url = ''
                if str(entry.changes.after.splash) == 'None':
                    url += default_avatar
                else:
                    url = str(entry.changes.after.splash)
                e.set_image(url=url)
                e.set_footer(text=embed_info['footer'])
                embeds.append(e)

            if hasattr(entry.changes.before, 'discovery_splash') and 'Discovery Splash Changed' in actions:
                embed_info = {'title': 'Discovery splash changed',
                              'updater': user,
                              'footer': f"{datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}"}
                e = discord.Embed(title=embed_info['title'], description=f"**Changed by:** {embed_info['updater']}")
                url = ''
                if str(entry.changes.after.discovery_splash) == 'None':
                    url += default_avatar
                else:
                    url = str(entry.changes.after.discovery_splash)
                e.set_image(url=url)
                e.set_footer(text=embed_info['footer'])
                embeds.append(e)
                # await bot.get_channel(server_log_channel).send(embed=e)

            if hasattr(entry.changes.before, 'banner') and 'Banner Changed' in actions:
                embed_info = {'title': 'Banner changed',
                              'updater': user,
                              'footer': f"{datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}"}
                e = discord.Embed(title=embed_info['title'], description=f"**Changed by:** {embed_info['updater']}")
                url = ''
                if str(entry.changes.after.banner) == 'None':
                    url += default_avatar
                else:
                    url = str(entry.changes.after.banner)
                e.set_image(url=url)
                e.set_footer(text=embed_info['footer'])
                embeds.append(e)

            if len(embeds) > 0:
                if wh_url is not None:
                    await send_embeds_through_wh(embeds, wh_url)
                else:
                    await bot.get_channel(server_log_channel).send(embeds=embeds)

    if entry.action == discord.AuditLogAction.emoji_create:
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            entry.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int) and 'Emoji Added' in actions:
            embed_info = {}
            new_emoji = entry.target
            emoji_id = new_emoji.id
            embed_info['title'] = "Emoji added"
            embed_info['url'] = new_emoji.url
            embed_info['name'] = f"**Added emoji:** {new_emoji.name}\n"
            embed_info['updater'] = f"{user}"
            embed_info['changetype'] = 'Added'
            embed_info['color'] = add_clr
            embed_info[
                'footer'] = f"Emoji ID: {emoji_id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}"
            embed = discord.Embed(title=embed_info['title'],
                                  description=f"{embed_info['name']}**{embed_info['changetype']} by:** {embed_info['updater']}\n**Emoji icon:**",
                                  color=embed_info['color'])
            embed.set_image(url=embed_info['url'])
            embed.set_footer(text=embed_info['footer'])

            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.emoji_delete:

        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            entry.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int) and 'Emoji Deleted' in actions:
            embed_info = {'title': "Emoji deleted", 'name': f"**Deleted emoji:** {entry.changes.before.name}\n",
                          'updater': f"{user}", 'changetype': 'Deleted', 'color': remove_clr,
                          'footer': f"Emoji ID: {entry.target.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}"}
            embed = discord.Embed(title=embed_info['title'],
                                  description=f"{embed_info['name']}**{embed_info['changetype']} by:** {embed_info['updater']}",
                                  color=embed_info['color'])
            embed.set_footer(text=embed_info['footer'])
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.emoji_update:
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            entry.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int) and 'Emoji Updated' in actions:
            embed_info = {}

            emoji_id = entry.target.id
            embed_info['title'] = "Emoji updated"
            embed_info['url'] = entry.target.url
            embed_info[
                'name'] = f"**Previous name:** {entry.changes.before.name}\n**New name:** {entry.changes.after.name}\n"
            embed_info['updater'] = f"{user}"
            embed_info['changetype'] = 'Updated'
            embed_info['color'] = update_clr
            embed_info[
                'footer'] = f"Emoji ID: {emoji_id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}"
            embed = discord.Embed(title=embed_info['title'],
                                  description=f"{embed_info['name']}**{embed_info['changetype']} by:** {embed_info['updater']}\n**Emoji icon:**",
                                  color=embed_info['color'])
            embed.set_image(url=embed_info['url'])
            embed.set_footer(text=embed_info['footer'])

            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.channel_create:
        channel = entry.target
        guild = channel.guild
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None
        if isinstance(server_log_channel, int) and 'Channel Created' in actions:

            channel_type = ''
            if isinstance(channel, discord.TextChannel):
                channel_type += 'Text'
            if isinstance(channel, discord.VoiceChannel):
                channel_type += 'Voice'
            if isinstance(channel, discord.StageChannel):
                channel_type += 'Stage'
            if isinstance(channel, discord.CategoryChannel):
                channel_type += 'Category'
            if isinstance(channel, discord.ForumChannel):
                channel_type += 'Forum'

            embed_info = {'title': f"{channel_type} channel created", "user": f"{user}",
                          "channel": f"{channel.mention}",
                          "footer": f"Channel ID: {channel.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}"}
            embed = discord.Embed(title=embed_info['title'],
                                  description=f"**Channel:** {embed_info['channel']}\n**Created by:** {embed_info['user']}",
                                  color=add_clr)
            embed.set_footer(text=embed_info['footer'])
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.channel_delete:
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            entry.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int) and 'Channel Deleted' in actions:
            channel_type = ''
            if entry.changes.before.type == discord.ChannelType.text:
                channel_type += 'Text'
            if entry.changes.before.type == discord.ChannelType.voice:
                channel_type += 'Voice'
            if entry.changes.before.type == discord.ChannelType.stage_voice:
                channel_type += 'Stage'
            if entry.changes.before.type == discord.ChannelType.category:
                channel_type += 'Category'
            if entry.changes.before.type == discord.ChannelType.forum:
                channel_type += 'Forum'

            embed_info = {'title': f"{channel_type} channel deleted", "user": f"{user}",
                          "channel": f"{entry.changes.before.name}",
                          "footer": f"Channel ID: {entry.target.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}"}
            embed = discord.Embed(title=embed_info['title'],
                                  description=f"**Channel name:** {embed_info['channel']}\n**Deleted by:** {embed_info['user']}",
                                  color=remove_clr)
            embed.set_footer(text=embed_info['footer'])
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.channel_update:
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            entry.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int) and 'Channel Updated' in actions:
            embed = discord.Embed(title=f"{'Text' if isinstance(entry.target, discord.TextChannel) or isinstance(entry.target, discord.ForumChannel) else 'Voice'} channel '{entry.target.name}' updated",
                                  description=f"**Updated by:** {user}",
                                  color=update_clr)
            before_info = ""
            after_info = ""
            before = entry.changes.before
            after = entry.changes.after
            if hasattr(before, 'name'):
                before_info += f"**Name:** {before.name}        \n"
                after_info += f"**Name:** {after.name}      \n"
            if hasattr(before, 'topic'):
                before_info += f"**Topic:** {before.topic}       \n"
                after_info += f"**Topic:** {after.topic}       \n"
            if hasattr(before, 'slowmode_delay'):
                before_info += f"**Slowmode:** {t(before.slowmode_delay) if before.slowmode_delay > 0 else '0 seconds'}       \n"
                after_info += f"**Slowmode:** {t(after.slowmode_delay) if after.slowmode_delay > 0 else '0 seconds'}        \n"
            if hasattr(before, 'nsfw'):
                before_info += f"**NSFW:** {before.nsfw}       \n"
                after_info += f"**NSFW:** {after.nsfw}        \n"
            if hasattr(before, 'default_auto_archive_duration'):
                before_info += f"**Archive threads after:** {t(before.default_auto_archive_duration * 60)}       \n"
                after_info += f"**Archive threads after:** {t(after.default_auto_archive_duration * 60)}        \n"
            if hasattr(before, 'bitrate'):
                before_info += f"**Bitrate:** {before.bitrate//1000} kbps       \n"
                after_info += f"**Bitrate:** {after.bitrate//1000} kbps        \n"
            if hasattr(before, 'rtc_region'):
                before_info += f"**Region Override:** {before.rtc_region if before.rtc_region is not None else 'automatic'}       \n"
                after_info += f"**Region Override:** {after.rtc_region  if after.rtc_region is not None else 'automatic'}        \n"
            if hasattr(before, 'user_limit'):
                before_info += f"**User limit:** {before.user_limit if before.user_limit > 0 else 'unlimited'}       \n"
                after_info += f"**User limit:** {after.user_limit if after.user_limit > 0 else 'unlimited'}        \n"
            if hasattr(before, 'video_quality_mode'):
                before_info += f"**Video quality mode:** {before.video_quality_mode.name if before.video_quality_mode is not None else 'automatic'}       \n"
                after_info += f"**Video quality mode:** {after.video_quality_mode.name if after.video_quality_mode is not None else 'automatic'}        \n"

            embed.add_field(name="Before: ", value=before_info)
            embed.add_field(name="After: ", value=after_info)
            embed.set_footer(
                text=f"Channel ID: {entry.target.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}")
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.overwrite_update:
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            entry.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int) and 'Channel Updated' in actions:
            perm_changes = get_perm_changes(entry)
            changes = ""
            for change in perm_changes[0]:
                changes += f"**{change.replace('_', ' ')}: ** {perm_changes[0][change]} → {perm_changes[1][change]}\n".replace('True',':white_check_mark:').replace('False', ":x:").replace("None", ':white_large_square:')

            embed = discord.Embed(title=f"Overwrites in channel '{entry.target.name}' for {'member' if isinstance(entry.extra, discord.Member) else 'role'} '{entry.extra.name}' updated",
                              description=f"**Updated by:** {user}", color=update_clr)
            embed.add_field(name='New overwrites', value=changes)
            embed.set_footer(
                text=f"Channel ID: {entry.target.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}")
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.overwrite_create:
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            entry.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int) and 'Channel Updated' in actions:
            embed = discord.Embed(
                title=f"Overwrites in channel '{entry.target.name}' for {'member' if isinstance(entry.extra, discord.Member) else 'role'} '{entry.extra.name}' created",
                description=f"**Created by:** {user}", color=add_clr)
            embed.set_footer(
                text=f"Channel ID: {entry.target.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}")

            if entry.extra.id == entry.guild.id:
                perm_changes = everyone_overwrite_perms(entry)
                changes = ""
                for change in perm_changes:
                    changes += f"{change}: None → {perm_changes[change]}\n".replace('True',
                                                                                    ':white_check_mark:').replace(
                        'False', ":x:").replace("None", ':white_large_square:')
                embed.add_field(name="With overwrites:", value=changes)

            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.overwrite_delete:
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            entry.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int) and 'Channel Updated' in actions:
            embed = discord.Embed(
                title=f"Overwrites in channel '{entry.target.name}' for {'member' if isinstance(entry.extra, discord.Member) else 'role'} '{entry.extra.name}' deleted",
                description=f"**Deleted by:** {user}", color=remove_clr)
            embed.set_footer(
                text=f"Channel ID: {entry.target.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}")
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.role_create:
        guild = entry.target.guild
        role = entry.target
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            entry.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int) and 'Role Created' in actions:
            rt = ''
            if role.is_integration():
                rt += 'Integration'
            else:
                rt += 'Role'
            embed_info = {'title': f"{rt} created", "user": f"{user}",
                          "role": f"{role.name}",
                          "footer": f"Role ID: {role.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}"}
            embed = discord.Embed(title=embed_info['title'],
                                  description=f"**Role:** {embed_info['role']}\n**Created by:** {embed_info['user']}",
                                  color=add_clr)
            embed.set_footer(text=embed_info['footer'])
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.role_delete:
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            entry.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int) and 'Role Deleted' in actions:

            embed_info = {'title': f"Role deleted", "user": f"{user}",
                          "role": f"{entry.changes.before.name}",
                          "footer": f"Role ID: {entry.target.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}"
                          }
            embed = discord.Embed(title=embed_info['title'],
                                  description=f"**Role:** {embed_info['role']}\n**Deleted by:** {embed_info['user']}",
                                  color=remove_clr)
            embed.set_footer(text=embed_info['footer'])
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.role_update:
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            entry.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int) and 'Role Updated' in actions:
            embed = discord.Embed(title=f'Role "{entry.target.name}" updated',
                                  description=f"**Updated by:** {user}",
                                  color=update_clr)
            before_info = ''
            after_info = ''
            before = entry.changes.before
            after = entry.changes.after

            if hasattr(before, 'color'):
                before_info += f'**Color:** {str(hex(before.color.value))[2:]}      \n'
                after_info += f'**Color:** {str(hex(after.color.value))[2:]}        \n'
            if hasattr(before, 'name'):
                before_info += f'**Name:** {before.name}        \n'
                after_info += f'**Name:** {after.name}      \n'
            if hasattr(before, 'mentionable'):
                before_info += f'**Mentionable:** {before.mentionable}      \n'
                after_info += f'**Mentionable:** {after.mentionable}        \n'
            if hasattr(before, 'hoist'):
                before_info += f'**Hoist:** {before.hoist}      \n'
                after_info += f'**Hoist:** {after.hoist}        \n'
            if before_info != '':
                embed.add_field(name="Before", value=before_info)
                embed.add_field(name="After", value=after_info)
            if hasattr(before, 'permissions'):
                changed = ""
                old = list(iter(before.permissions))
                new = list(iter(after.permissions))
                for i in range(len(old)):
                    if old[i] != new[i]:
                        changed += f"**{old[i][0].replace('_', ' ')}:** {old[i][1]} → {new[i][1]}\n"
                updated = changed.replace('False', ':x:').replace('True', ':white_check_mark:')
                embed.add_field(name="New permissions", value=updated)
            if before_info != '' or before.permissions != after.permissions:
                embed.set_footer(
                    text=f"Role ID: {entry.target.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}")
                if wh_url is not None:
                    await send_embed_through_wh(embed, wh_url)
                else:
                    await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.invite_create:
        invite = entry.target
        uses = invite.max_uses
        if invite.max_uses == 0:
            uses -= uses
            uses = str(uses)
            uses = uses[0:0]
            uses += 'unlimited'

        age = invite.max_age
        if age == 0:
            age -= age
            age = str(age)
            age = age[0:0]
            age += 'never expires'

        invite_info = {'code': invite.code, 'channel': invite.channel.mention, 'max_age': age,
                       'max_uses': uses, 'expiry_time': t(invite.max_age), 'temporary': invite.temporary,
                       'creator': f"{invite.inviter.name} ({invite.inviter.mention})"}
        guild = invite.guild
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int) and 'Invite Created' in actions:
            embed_info = {'title': f"Invite created", "user": f"{invite.inviter.name} ({invite.inviter.mention})",
                          "info": f"**Code:** {invite_info['code']}\n**Channel:** {invite_info['channel']}\n**Max age in seconds:** {invite_info['max_age']}\n**Max uses:** {invite_info['max_uses']}\n**Temporary:** {str(invite_info['temporary']).lower()}\n**Created by:** {invite_info['creator']}",
                          "footer": f"{datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}"
                          }
            embed = discord.Embed(title=embed_info['title'],
                                  description=embed_info['info'], color=add_clr)
            embed.set_footer(text=embed_info['footer'])
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.invite_delete:
        invite = entry.target
        uses = invite.max_uses
        if invite.max_uses == 0:
            uses -= uses
            uses = str(uses)
            uses = uses[0:0]
            uses += 'unlimited'

        age = invite.max_age
        if age == 0:
            age -= age
            age = str(age)
            age = age[0:0]
            age += 'never expires'

        invite_info = {'code': invite.code, 'channel': invite.channel.mention, 'max_age': age,
                       'max_uses': uses, 'expiry_time': t(invite.max_age), 'temporary': invite.temporary,
                       'creator': f"{invite.inviter.name} ({invite.inviter.mention})", "uses": invite.uses}
        guild = invite.guild
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int) and 'Invite Deleted' in actions:
            embed_info = {'title': f"Invite deleted", "user": f"{invite.inviter.name} ({invite.inviter.mention})",
                          "info": f"**Deleted by:** {user}\n**Code:** {invite_info['code']}\n**Channel:** {invite_info['channel']}\n**Uses:** {invite_info['uses']}\n**Max uses:** {invite_info['max_uses']}\n**Max age in seconds:** {invite_info['max_age']}\n**Temporary:** {str(invite_info['temporary']).lower()}\n**Created by:** {invite_info['creator']}",
                          "footer": f"{datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}"
                          }
            embed = discord.Embed(title=embed_info['title'],
                                  description=embed_info['info'], color=remove_clr)
            embed.set_footer(text=embed_info['footer'])
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(server_log_channel).send(embed=embed)

    if entry.action == discord.AuditLogAction.bot_add:
        settings = await conn.fetchrow(
            'SELECT server_channel, server_actions, server_webhook FROM modlogs WHERE guild_id=$1',
            entry.guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['server_actions'] is not None
            server_log_channel = dict(settings)['server_channel'] if actions_not_empty else None
            actions = dict(settings)['server_actions'] if actions_not_empty else log_actions['Member Events']
            wh_url = dict(settings)['server_webhook'] if actions_not_empty else None
        else:
            server_log_channel = None
            actions = log_actions['Server Changes']
            wh_url = None

        if isinstance(server_log_channel, int) and "Bot Added" in actions:
            embed = discord.Embed(title="Bot added", description=f"**Added by:** {user}", color=add_clr)
            url = ''
            if str(entry.target.avatar) != 'None':
                url += str(entry.target.avatar)
            else:
                url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
            embed.set_author(name=str(entry.target), icon_url=url)
            embed.set_footer(text=f"Bot ID: {entry.target.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            if wh_url is not None:
                await send_embed_through_wh(embed, wh_url)
            else:
                await bot.get_channel(server_log_channel).send(embed=embed)


def get_perm_changes(entry):
    old_deny = []
    new_deny = []
    old_allow = []
    new_allow = []

    if hasattr(entry.changes.before, 'deny'):
        old_deny += list(iter(entry.changes.before.deny))
        new_deny += list(iter(entry.changes.after.deny))
        perm_names = [i[0] for i in old_deny]

    if hasattr(entry.changes.before, 'allow'):
        old_allow += list(iter(entry.changes.before.allow))
        new_allow += list(iter(entry.changes.after.allow))
        perm_names = [i[0] for i in old_allow]

    perm_len = max([len(old_deny), len(old_allow), len(new_deny), len(new_allow)])

    old_perms = {}
    new_perms = {}

    for i in range(perm_len):
        if len(old_deny) > 0:
            if old_deny[i][1]:
                old_perms[perm_names[i]] = 'False'
        if len(old_allow) > 0:
            if old_allow[i][1]:
                old_perms[perm_names[i]] = 'True'

        if len(new_deny) > 0:
            if new_deny[i][1]:
                new_perms[perm_names[i]] = 'False'
        if len(new_allow) > 0:
            if new_allow[i][1]:
                new_perms[perm_names[i]] = 'True'

    for i in old_perms:
        if i not in new_perms:
            new_perms[i] = 'None'

    for i in new_perms:
        if i not in old_perms:
            old_perms[i] = 'None'

    things_to_del = []

    for i in old_perms:
        if old_perms[i] == new_perms[i]:
            things_to_del.append(i)

    for i in things_to_del:
        del old_perms[i], new_perms[i]

    return [old_perms, new_perms]


def everyone_overwrite_perms(entry):
    new_deny = []
    new_allow = []

    if hasattr(entry.changes.after, 'deny'):
        new_deny += list(iter(entry.changes.after.deny))
        perm_names = [i[0] for i in new_deny]

    if hasattr(entry.changes.after, 'allow'):
        new_allow += list(iter(entry.changes.after.allow))
        perm_names = [i[0] for i in new_allow]

    perm_len = max([len(new_deny), len(new_allow)])

    new_perms = {}

    for i in range(perm_len):
        if len(new_deny) > 0:
            if new_deny[i][1]:
                new_perms[perm_names[i]] = 'False'
        if len(new_allow) > 0:
            if new_allow[i][1]:
                new_perms[perm_names[i]] = 'True'

    return new_perms

