import asyncio
import datetime
from datetime import timezone
import discord
from discord.ext import commands
import DiscordUtils
import asyncpg
from features.punishing import log_infraction

dbpass = 'mysecretpassword'

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


def get_name(member):
    return f"{member.name}#{member.discriminator}"


def get_content(messages):
    message_content = []
    for message in messages:
        message_content.append(message.content)
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
        if i == 0 and res[i]:
            actual.append(f'{res[i]} days')
        if i == 1 and res[i]:
            actual.append(f'{res[i]} hours')
        if i == 2 and res[i]:
            actual.append(f'{res[i]} minutes')
        if i == 3 and res[i]:
            actual.append(f'{res[i]} seconds')

    return ', '.join(actual)


async def connections():
    global conn
    conn = await asyncpg.create_pool(host=d['host'], port=d['port'], user=d['user'], password=d['pwd'],
                                     database=d['db'])


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


class MessageLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):

        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', after.guild.id)

        if settings is not None:
            message_log_channel = dict(settings)['message_channel']
            actions = dict(settings)['message_actions']
        else:
            message_log_channel = None
            actions = log_actions['Message Events']
        if isinstance(message_log_channel,
                      int) and 'Message Edited' in actions and before.content != after.content:
            ch = self.bot.get_channel(message_log_channel)
            embed = discord.Embed(title=f"Message edited in #{self.bot.get_channel(before.channel.id)}",
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
            await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', message.guild.id)

        if settings is not None:
            message_log_channel = dict(settings)['message_channel']
            actions = dict(settings)['message_actions']
        else:
            message_log_channel = None
            actions = log_actions['Message Events']

        if isinstance(message_log_channel, int) and 'Message Deleted' in actions and message.content != '':
            ch = self.bot.get_channel(message_log_channel)
            embed = discord.Embed(title=f"Message deleted in #{self.bot.get_channel(message.channel.id)}",
                                  description=f"**Content:** {message.content}", color=remove_clr)
            url = ''
            if str(message.author.avatar) != 'None':
                url += str(message.author.avatar)
            else:
                url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
            embed.set_author(name=str(message.author), icon_url=url)
            embed.set_footer(
                text=f"Message ID: {message.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', payload.guild_id)
        if settings is not None:
            message_log_channel = dict(settings)['message_channel']
            actions = dict(settings)['message_actions']
        else:
            message_log_channel = None
            actions = log_actions['Message Events']
        messages = get_content(payload.cached_messages)
        user = (await self.bot.get_guild(payload.guild_id).audit_logs(limit=1).flatten())[0].user
        if isinstance(message_log_channel, int) and 'Message Bulk Deletion' in actions and len(
                payload.cached_messages) > 0:
            channel = self.bot.get_channel(payload.channel_id)
            ch = self.bot.get_channel(message_log_channel)
            string = ""
            for message in messages:
                string += f"{message}\n"
            embed = discord.Embed(title=f"Messages bulk deleted in #{channel}", color=remove_clr)
            embed.add_field(name="Deleted messages:", value=string)
            embed.add_field(name="Deleted by:",
                            value=f"{user}({user.mention})")
            embed.set_footer(
                text=f"Channel ID: {payload.channel_id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await ch.send(embed=embed)


class MemberLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tracker = DiscordUtils.InviteTracker(bot)
        self._last_member = None

    # members
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', before.guild.id)
        who_did_it = (await after.guild.audit_logs(limit=1).flatten())[0].user
        if settings is not None:
            member_log_channel = dict(settings)['member_channel']
            actions = dict(settings)['member_actions']
        else:
            member_log_channel = None
            actions = log_actions['Member Events']
        if before.nick != after.nick and isinstance(member_log_channel, int) and "Nickname Changed" in actions:
            embed = discord.Embed(title="Nickname changed",
                                  description=f"**Old nickname:** {before.display_name}\n**New nickname:** {after.display_name}\n**Changed by:** {who_did_it} ({who_did_it.mention})",
                                  color=update_clr)
            embed.set_footer(
                text=f"Member ID: {after.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            url = ''
            if str(after.avatar) != 'None':
                url += str(after.avatar)
            else:
                url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
            embed.set_author(name=str(after), icon_url=url)
            await self.bot.get_channel(member_log_channel).send(embed=embed)

        if before.roles != after.roles and isinstance(member_log_channel, int) and "Roles Changed" in actions:
            if len(before.roles) < len(after.roles):
                added_role = [role for role in after.roles if role not in before.roles][0].mention
                embed = discord.Embed(title="Role added",
                                      description=f"**Role added:** {added_role}\n**Added by:** {who_did_it} ({who_did_it.mention})",
                                      color=update_clr)
                embed.set_footer(text=f"{datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                url = ''
                if str(after.avatar) != 'None':
                    url += str(after.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(after), icon_url=url)
                await self.bot.get_channel(member_log_channel).send(embed=embed)
            else:
                removed_role = [role for role in before.roles if role not in after.roles][0].mention
                embed = discord.Embed(title="Role removed",
                                      description=f"**Role removed:** {removed_role}\n**Removed by:** {who_did_it} ({(await after.guild.audit_logs(limit=1).flatten())[0].user.mention})",
                                      color=update_clr)
                embed.set_footer(
                    text=f"Member ID: {after.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                url = ''
                if str(after.avatar) != 'None':
                    url += str(after.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(after), icon_url=url)
                await self.bot.get_channel(member_log_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        for guild in after.mutual_guilds:
            settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
            if settings is not None:
                member_log_channel = dict(settings)['member_channel']
                actions = dict(settings)['member_actions']
            else:
                member_log_channel = None
                actions = log_actions['Member Events']
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
                await self.bot.get_channel(member_log_channel).send(embed=embed)
            if str(before.avatar) != str(after.avatar) and "Avatar Changed" in actions and isinstance(
                    member_log_channel, int):
                embed = discord.Embed(title="Avatar changed", color=update_clr)
                embed.set_footer(
                    text=f"Member ID: {after.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                embed.set_image(url=str(after.avatar))
                embed.set_author(name=str(after))
                await self.bot.get_channel(member_log_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            server_actions = dict(settings)['server_actions']
            server_channel = dict(settings)['server_channel']
            member_actions = dict(settings)['member_actions']
            member_channel = dict(settings)['member_channel']
        else:
            member_channel = None
            member_actions = log_actions['Member Events']
            server_channel = None
            server_actions = log_actions['Server Changes']

        if member.bot and isinstance(server_channel, int) and "Bot Added" in server_actions:
            adder = (await member.guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add).flatten())[
                0].user
            info = {'Added by': f"{adder} ({adder.mention})"}
            embed = discord.Embed(title="Bot added", color=add_clr)
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
            embed.set_footer(text=f"Bot ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await self.bot.get_channel(server_channel).send(embed=embed)
        if not member.bot and isinstance(member_channel, int) and "Member Joined" in member_actions:
            inv_info = await self.tracker.fetch_inviter(member)
            inviter = inv_info[1]
            invite = inv_info[0]
            info = {'Created': t(
                int((datetime.datetime.now(timezone.utc) - member.created_at).total_seconds())),
                'Invited by': f"{inviter} ({inviter.mention})", 'Code used': invite.code,
                'Number of times code has been used': invite.uses + 1}
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
            await self.bot.get_channel(member_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', member.guild.id)
        if settings is not None:
            member_log_channel = dict(settings)['member_channel']
            actions = dict(settings)['member_actions']
        else:
            member_log_channel = None
            actions = log_actions['Member Events']
        if "Member Left" in actions and isinstance(member_log_channel, int):

            leave_event = [e for e in
                           (await member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick).flatten()) if
                           e.target.id == member.id]

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
                    await self.bot.get_channel(member_log_channel).send(embed=embed)


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        leave_event = [e for e in
                       (await member.guild.audit_logs(limit=1).flatten()) if
                       e.target.id == member.id if e.action == discord.AuditLogAction.kick]
        if len(leave_event) > 0 and not member.bot:
            settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', member.guild.id)
            if settings is not None:
                mod_channel = dict(settings)['moderation_channel']
                actions = dict(settings)['moderations']
            else:
                mod_channel = None
                actions = log_actions['Moderation Events']
            if "Member Kicked" in actions and isinstance(mod_channel, int):
                if (datetime.datetime.now(timezone.utc) - leave_event[0].created_at).total_seconds() <= 1:
                    embed = discord.Embed(title="Member kicked",
                                          description=f"**Reason:** {leave_event[0].reason}\n**Moderator:** {leave_event[0].user} ({leave_event[0].user.mention})",
                                          color=punish_clr)
                    url = ''
                    if str(member.avatar) != 'None':
                        url += str(member.avatar)
                    else:
                        url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                    embed.set_author(name=str(member), icon_url=url)
                    embed.set_footer(
                        text=f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                    await self.bot.get_channel(mod_channel).send(embed=embed)
            if not leave_event[0].user.bot and not member.bot:
                await member.send(
                    embed=discord.Embed(title=f"You've been banned from {member.guild}",
                                        description=f"**Moderator: ** {leave_event[0].user}\n**Reason: **{leave_event[0].reason}",
                                        color=0xf54254))
            await log_infraction(member, member.guild, {"type": "Kick", "Reason": leave_event[0].reason,
                                                        "Moderator": str(leave_event[0].user)}, conn)


    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        ban_event = (await guild.audit_logs(limit=1).flatten())[0]
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            mod_channel = dict(settings)['moderation_channel']
            actions = dict(settings)['moderations']
        else:
            mod_channel = None
            actions = log_actions['Moderation Events']

        if "Member Banned" in actions and isinstance(mod_channel, int):
            if not ban_event.user.bot and not user.bot:
                embed = discord.Embed(title="Member banned",
                                      description=f"**Reason:** {ban_event.reason}\n**Moderator:** {ban_event.user} ({ban_event.user.mention})",
                                      color=punish_clr)
                url = ''
                if str(user.avatar) != 'None':
                    url += str(user.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(user), icon_url=url)
                embed.set_footer(
                    text=f"Member ID: {user.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                await self.bot.get_channel(mod_channel).send(embed=embed)
                await conn.execute('DELETE FROM user_infraction_points WHERE memberkey=$1', f"{guild.id}_{user.id}")
        if not ban_event.user.bot and not user.bot:
            await user.send(
                embed=discord.Embed(title=f"You've been banned from {guild}",
                                    description=f"**Moderator: ** {ban_event.user}\n**Reason: **{ban_event.reason}", color=0xf54254))
        await log_infraction(user, guild, {"type": "Ban", "Reason": ban_event.reason, "Moderator": str(ban_event.user)},
                             conn)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        unban_event = (await guild.audit_logs(limit=1).flatten())[0]
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            mod_channel = dict(settings)['moderation_channel']
            actions = dict(settings)['moderations']
        else:
            mod_channel = None
            actions = log_actions['Moderation Events']
        if "Member Unbanned" in actions and isinstance(mod_channel, int) and not user.bot:

            embed = discord.Embed(title="Member unbanned",
                                  description=f"**Moderator:** {unban_event.user} ({unban_event.user.mention})",
                                  color=unpunish_clr)
            url = ''
            if str(user.avatar) != 'None':
                url += str(user.avatar)
            else:
                url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
            embed.set_author(name=str(user), icon_url=url)
            embed.set_footer(
                text=f"Member ID: {user.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
            await self.bot.get_channel(mod_channel).send(embed=embed)
        await log_infraction(user, guild, {"type": "Unban", "Moderator": str(unban_event.user)}, conn)

        await user.send(
            embed=discord.Embed(title=f"You've been unbanned from {guild}",
                                description=f"**Moderator: ** {unban_event.user}",color=0x33f25c))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not before.timed_out and after.timed_out:
            au = [e for e in (await after.guild.audit_logs(limit=1).flatten()) if
                  e.action == discord.AuditLogAction.member_update]
            if len(au) > 0:
                event = au[0]
                settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', after.guild.id)

                if settings is not None:
                    mod_channel = dict(settings)['moderation_channel']
                    actions = dict(settings)['moderations']
                else:
                    mod_channel = None
                    actions = log_actions['Moderation Events']
                if "Member Muted" in actions and isinstance(mod_channel, int) and not event.user.bot:

                    embed = discord.Embed(title="Member muted",
                                          description=f"**Muted for:** {t(int((after.communication_disabled_until - datetime.datetime.now(tz=datetime.timezone.utc)).total_seconds()))}\n**Reason:** {event.reason}\n**Moderator:** {event.user} ({event.user.mention})",
                                          color=punish_clr)
                    url = ''
                    if str(after.avatar) != 'None':
                        url += str(after.avatar)
                    else:
                        url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                    embed.set_author(name=str(after), icon_url=url)
                    embed.set_footer(
                        text=f"Member ID: {after.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                    await self.bot.get_channel(mod_channel).send(embed=embed)

                if not event.user.bot:
                    await after.send(embed=discord.Embed(title=f"You've been muted in {after.guild}",
                                                         description=f"**Duration:** {t(int((after.communication_disabled_until - datetime.datetime.now(tz=datetime.timezone.utc)).total_seconds())+1)}\n**Reason:** {event.reason}\n**Moderator: **{event.user}",color=0xf54254))
                    await log_infraction(after, after.guild, {"type": "Mute", "Muted for": t(int((
                                                                                                             after.communication_disabled_until - datetime.datetime.now(
                                                                                                         tz=datetime.timezone.utc)).total_seconds())),
                                                              "Reason": event.reason, "Moderator": str(event.user)},
                                         conn)

        if before.timed_out and not after.timed_out:
            au = [e for e in (await after.guild.audit_logs(limit=1).flatten()) if
                  e.action == discord.AuditLogAction.member_update]
            if len(au) > 0:
                event = au[0]
                settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', after.guild.id)
                if settings is not None:
                    mod_channel = dict(settings)['moderation_channel']
                    actions = dict(settings)['moderations']
                else:
                    mod_channel = None
                    actions = log_actions['Moderation Events']
                if "Member Unmuted" in actions and isinstance(mod_channel, int) and not event.user.bot:

                    embed = discord.Embed(title="Member unmuted",
                                          description=f"**Moderator:** {event.user} ({event.user.mention})",
                                          color=unpunish_clr)
                    url = ''
                    if str(after.avatar) != 'None':
                        url += str(after.avatar)
                    else:
                        url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                    embed.set_author(name=str(after), icon_url=url)
                    embed.set_footer(
                        text=f"Member ID: {after.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                    await self.bot.get_channel(mod_channel).send(embed=embed)

                if not event.user.bot:
                    await after.send(embed=discord.Embed(title=f"You've been unmuted in {after.guild}",
                                                         description=f"**Moderator: **{event.user}",color=0x33f25c))
                    await log_infraction(after, after.guild, {"type": "Unmute", "Moderator": str(event.user)},
                                         conn)


class GuildUpdate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', after.id)
        if settings is not None:
            server_log_channel = dict(settings)['server_channel']
            actions = dict(settings)['server_actions']
            ok_different = before.verification_level != after.verification_level or before.name != after.name or before.explicit_content_filter != after.explicit_content_filter or before.owner != after.owner or before.afk_channel != after.afk_channel or before.system_channel != after.system_channel or before.default_notifications != after.default_notifications or before.afk_timeout != after.afk_timeout
            if isinstance(server_log_channel, int):
                if ok_different:
                    embed = discord.Embed(title='Server updated',
                                          description=f"**Updated by:** {(await after.audit_logs(limit=1).flatten())[0].user} ({(await after.audit_logs(limit=1).flatten())[0].user.mention})",
                                          color=update_clr)

                    before_info = ""
                    after_info = ""

                    if before.verification_level != after.verification_level and 'Verification Level Changed' in actions:
                        before_info += f"**Verification level:** {before.verification_level.name}      \n"
                        after_info += f"**Verification level:** {after.verification_level.name}      \n"

                    if before.name != after.name and 'Server Name Changed' in actions:
                        before_info += f"**Name:** {before.name}      \n"
                        after_info += f"**Name:** {after.name}      \n"

                    if before.mfa_level != after.mfa_level and 'MFA Changed' in actions:
                        mfa_dict = {0: 'not required', 1: 'required'}
                        before_info += f"**MFA level:** {mfa_dict[before.mfa_level]}      \n"
                        after_info += f"**MFA level:** {mfa_dict[after.mfa_level]}      \n"

                    if before.explicit_content_filter != after.explicit_content_filter and 'Explicit Filter Changed' in actions:
                        before_info += f"**Explicit filter:** {before.explicit_content_filter}      \n"
                        after_info += f"**Explicit filter:** {after.explicit_content_filter}      \n"

                    if before.owner != after.owner and 'Server Owner Changed' in actions:
                        before_info += f"**Owner:** {before.owner}      \n"
                        after_info += f"**Owner:** {after.owner}      \n"

                    if before.afk_channel != after.afk_channel and 'AFK Channel Changed' in actions:
                        before_info += f"**AFK channel: ** {[before.afk_channel.mention if before.afk_channel is not None else 'None'][0]}      \n"
                        after_info += f"**AFK channel: ** {[after.afk_channel.mention if after.afk_channel is not None else 'None'][0]}      \n"

                    if before.system_channel != after.system_channel and 'System Channel Changed' in actions:
                        before_info += f"**System channel: ** {[before.system_channel.mention if before.system_channel is not None else 'None'][0]}      \n"
                        after_info += f"**System channel: ** {[after.system_channel.mention if after.system_channel is not None else 'None'][0]}      \n"

                    if before.default_notifications != after.default_notifications and 'Default Notifications Changed' in actions:
                        before_info += f"**Default notification settings: ** {before.default_notifications.name}      \n"
                        after_info += f"**Default notification settings: ** {after.default_notifications.name}      \n"

                    if before.afk_timeout != after.afk_timeout and "AFK Timeout Changed" in actions:
                        before_info += f"**AFK timeout: ** {before.afk_timeout}      \n"
                        after_info += f"**AFK timeout: ** {after.afk_timeout}      \n"
                    embed.add_field(name='Before', value=before_info)
                    embed.add_field(name='After', value=after_info)
                    embed.set_footer(text=datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S'))
                    await self.bot.get_channel(server_log_channel).send(embed=embed)

                if str(before.icon) != str(after.icon) and 'Server Icon Changed' in actions:
                    embed_info = {'title': 'Server icon changed',
                                  'updater': f"{(await after.audit_logs(limit=1).flatten())[0].user} ({(await after.audit_logs(limit=1).flatten())[0].user.mention})",
                                  'footer': f"{datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}"}
                    e = discord.Embed(title=embed_info['title'], description=f"**Changed by:** {embed_info['updater']}")
                    url = ''
                    if str(after.icon) == 'None':
                        url += 'https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/198142ac-f410-423a-bf0b-34c9cb5d9609/dbtif5j-60306864-d6b7-44b6-a9ff-65e8adcfb911.png?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7InBhdGgiOiJcL2ZcLzE5ODE0MmFjLWY0MTAtNDIzYS1iZjBiLTM0YzljYjVkOTYwOVwvZGJ0aWY1ai02MDMwNjg2NC1kNmI3LTQ0YjYtYTlmZi02NWU4YWRjZmI5MTEucG5nIn1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmZpbGUuZG93bmxvYWQiXX0.pRh5DK_cxlZ6SxVPqoUSsSNo1fqksJVP6ECGVUi6kmE'
                    else:
                        url = str(after.icon)
                    e.set_image(url=url)
                    e.set_footer(text=embed_info['footer'])
                    await self.bot.get_channel(server_log_channel).send(embed=e)

                if str(before.splash) != str(after.splash) and 'Invite Splash Changed' in actions:
                    embed_info = {'title': 'Invite splash changed',
                                  'updater': f"{(await after.audit_logs(limit=1).flatten())[0].user} ({(await after.audit_logs(limit=1).flatten())[0].user.mention})",
                                  'footer': f"{datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}"}
                    e = discord.Embed(title=embed_info['title'], description=f"**Changed by:** {embed_info['updater']}")
                    url = ''
                    if str(after.icon) == 'None':
                        url += 'https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/198142ac-f410-423a-bf0b-34c9cb5d9609/dbtif5j-60306864-d6b7-44b6-a9ff-65e8adcfb911.png?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7InBhdGgiOiJcL2ZcLzE5ODE0MmFjLWY0MTAtNDIzYS1iZjBiLTM0YzljYjVkOTYwOVwvZGJ0aWY1ai02MDMwNjg2NC1kNmI3LTQ0YjYtYTlmZi02NWU4YWRjZmI5MTEucG5nIn1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmZpbGUuZG93bmxvYWQiXX0.pRh5DK_cxlZ6SxVPqoUSsSNo1fqksJVP6ECGVUi6kmE'
                    else:
                        url = str(after.icon)
                    e.set_image(url=url)
                    e.set_footer(text=embed_info['footer'])
                    await self.bot.get_channel(server_log_channel).send(embed=e)

                if str(before.discovery_splash) != str(
                        after.discovery_splash) and 'Discovery Splash Changed' in actions:
                    embed_info = {'title': 'Discovery splash changed',
                                  'updater': f"{(await after.audit_logs(limit=1).flatten())[0].user} ({(await after.audit_logs(limit=1).flatten())[0].user.mention})",
                                  'footer': f"{datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}"}
                    e = discord.Embed(title=embed_info['title'], description=f"**Changed by:** {embed_info['updater']}")
                    url = ''
                    if str(after.icon) == 'None':
                        url += 'https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/198142ac-f410-423a-bf0b-34c9cb5d9609/dbtif5j-60306864-d6b7-44b6-a9ff-65e8adcfb911.png?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7InBhdGgiOiJcL2ZcLzE5ODE0MmFjLWY0MTAtNDIzYS1iZjBiLTM0YzljYjVkOTYwOVwvZGJ0aWY1ai02MDMwNjg2NC1kNmI3LTQ0YjYtYTlmZi02NWU4YWRjZmI5MTEucG5nIn1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmZpbGUuZG93bmxvYWQiXX0.pRh5DK_cxlZ6SxVPqoUSsSNo1fqksJVP6ECGVUi6kmE'
                    else:
                        url = str(after.icon)
                    e.set_image(url=url)
                    e.set_footer(text=embed_info['footer'])
                    await self.bot.get_channel(server_log_channel).send(embed=e)

                if str(before.banner) != str(after.banner) and 'Banner Changed' in actions:
                    embed_info = {'title': 'Banner changed',
                                  'updater': f"{(await after.audit_logs(limit=1).flatten())[0].user} ({(await after.audit_logs(limit=1).flatten())[0].user.mention})",
                                  'footer': f"{datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}"}
                    e = discord.Embed(title=embed_info['title'], description=f"**Changed by:** {embed_info['updater']}")
                    url = ''
                    if str(after.icon) == 'None':
                        url += 'https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/198142ac-f410-423a-bf0b-34c9cb5d9609/dbtif5j-60306864-d6b7-44b6-a9ff-65e8adcfb911.png?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7InBhdGgiOiJcL2ZcLzE5ODE0MmFjLWY0MTAtNDIzYS1iZjBiLTM0YzljYjVkOTYwOVwvZGJ0aWY1ai02MDMwNjg2NC1kNmI3LTQ0YjYtYTlmZi02NWU4YWRjZmI5MTEucG5nIn1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmZpbGUuZG93bmxvYWQiXX0.pRh5DK_cxlZ6SxVPqoUSsSNo1fqksJVP6ECGVUi6kmE'
                    else:
                        url = str(after.icon)
                    e.set_image(url=url)
                    e.set_footer(text=embed_info['footer'])
                    await self.bot.get_channel(server_log_channel).send(embed=e)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            server_log_channel = dict(settings)['server_channel']
            actions = dict(settings)['server_actions']
            if isinstance(server_log_channel, int):
                did = (await guild.audit_logs(limit=1).flatten())[0]
                user = did.user
                before = list(before)
                after = list(after)
                embed_info = {}
                emoji_id = 0
                if len(after) < len(before) and 'Emoji Deleted' in actions:
                    deleted = [emoji for emoji in before if emoji not in after][0]
                    emoji_id += deleted.id
                    embed_info['title'] = "Emoji deleted"
                    embed_info['url'] = deleted.url
                    embed_info['name'] = f"**Deleted emoji:** {deleted.name}\n"
                    embed_info['updater'] = f"{user} ({user.mention})"
                    embed_info['changetype'] = 'Deleted'
                    embed_info['color'] = remove_clr
                if len(after) > len(before) and 'Emoji Added' in actions:
                    added = [emoji for emoji in after if emoji not in before][0]
                    emoji_id += added.id
                    embed_info['title'] = "Emoji added"
                    embed_info['url'] = added.url
                    embed_info['name'] = f"**Added emoji:** {added.name}\n"
                    embed_info['updater'] = f"{user} ({user.mention})"
                    embed_info['changetype'] = 'Added'
                    embed_info['color'] = add_clr
                if len(after) == len(before) and 'Emoji Updated' in actions:
                    changed = \
                    [emoji for emoji in after if before[before.index(emoji)].name != after[before.index(emoji)].name][0]
                    emoji_id += changed.id
                    embed_info['title'] = "Emoji updated"
                    embed_info['url'] = changed.url
                    embed_info[
                        'name'] = f"**Previous name:** {before[before.index(changed)].name}\n**New name:** {after[after.index(changed)].name}\n"
                    embed_info['updater'] = f"{user} ({user.mention})"
                    embed_info['changetype'] = 'Updated'
                    embed_info['color'] = update_clr
                embed_info[
                    'footer'] = f"Emoji ID: {emoji_id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}"
                embed = discord.Embed(title=embed_info['title'],
                                      description=f"{embed_info['name']}**{embed_info['changetype']} by:** {embed_info['updater']}\n**Emoji icon:**",
                                      color=embed_info['color'])
                embed.set_image(url=embed_info['url'])
                embed.set_footer(text=embed_info['footer'])

                await self.bot.get_channel(server_log_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        guild = channel.guild
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            server_log_channel = dict(settings)['server_channel']
            actions = dict(settings)['server_actions']
            if isinstance(server_log_channel, int) and 'Channel Created' in actions:
                user = (await guild.audit_logs(limit=1).flatten())[0].user
                channel_type = ''
                if isinstance(channel, discord.TextChannel):
                    channel_type += 'Text'
                if isinstance(channel, discord.VoiceChannel):
                    channel_type += 'Voice'
                if isinstance(channel, discord.StageChannel):
                    channel_type += 'Stage'
                if isinstance(channel, discord.CategoryChannel):
                    channel_type += 'Category'
                embed_info = {'title': f"{channel_type} channel created", "user": f"{user} ({user.mention})",
                              "channel": f"{channel.mention}",
                              "footer": f"Channel ID: {channel.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}"}
                embed = discord.Embed(title=embed_info['title'],
                                      description=f"**Channel:** {embed_info['channel']}\n**Created by:** {embed_info['user']}",
                                      color=add_clr)
                embed.set_footer(text=embed_info['footer'])
                await self.bot.get_channel(server_log_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            server_log_channel = dict(settings)['server_channel']
            actions = dict(settings)['server_actions']
            if isinstance(server_log_channel, int) and 'Channel Deleted' in actions:
                user = (await guild.audit_logs(limit=1).flatten())[0].user
                channel_type = ''
                if isinstance(channel, discord.TextChannel):
                    channel_type += 'Text'
                if isinstance(channel, discord.VoiceChannel):
                    channel_type += 'Voice'
                if isinstance(channel, discord.StageChannel):
                    channel_type += 'Stage'
                if isinstance(channel, discord.CategoryChannel):
                    channel_type += 'Category'
                embed_info = {'title': f"{channel_type} channel deleted", "user": f"{user} ({user.mention})",
                              "channel": f"{channel}",
                              "footer": f"Channel ID: {channel.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}"}
                embed = discord.Embed(title=embed_info['title'],
                                      description=f"**Channel name:** {embed_info['channel']}\n**Deleted by:** {embed_info['user']}",
                                      color=remove_clr)
                embed.set_footer(text=embed_info['footer'])
                await self.bot.get_channel(server_log_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        guild = after.guild
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            server_log_channel = dict(settings)['server_channel']
            actions = dict(settings)['server_actions']
            if isinstance(server_log_channel, int) and "Channel Updated" in actions:
                person = (await after.guild.audit_logs(limit=1).flatten())[0].user
                if isinstance(before, discord.TextChannel):
                    ok_different = before.name != after.name or before.topic != after.topic or before.slowmode_delay != after.slowmode_delay or before.is_nsfw() != after.is_nsfw()
                    if ok_different:
                        embed = discord.Embed(title=f"Channel #{after.name} updated",
                                              description=f"**Updated by:** {person} ({person.mention})",
                                              color=update_clr)
                        before_info = ""
                        after_info = ""
                        if before.name != after.name:
                            before_info += f"**Name:** {before.name}        \n"
                            after_info += f"**Name:** {after.name}      \n"
                        if before.topic != after.topic:
                            before_info += f"**Topic:** {before.topic}       \n"
                            after_info += f"**Topic:** {after.topic}       \n"
                        if before.slowmode_delay != after.slowmode_delay:
                            before_info += f"**Slowmode:** {before.slowmode_delay} seconds       \n"
                            after_info += f"**Slowmode:** {after.slowmode_delay} seconds        \n"
                        if before.is_nsfw() != after.is_nsfw():
                            before_info += f"**NSFW:** {before.is_nsfw()}       \n"
                            after_info += f"**NSFW:** {after.is_nsfw()}        \n"
                        embed.add_field(name="Before: ", value=before_info)
                        embed.add_field(name="After: ", value=after_info)
                        embed.set_footer(
                            text=f"Channel ID: {after.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}")
                        await self.bot.get_channel(server_log_channel).send(embed=embed)

                    if before.overwrites != after.overwrites:
                        old = before.overwrites
                        new = after.overwrites
                        if len(new) < len(old):
                            embed = discord.Embed(
                                title=f'Overwrites in {before.name} for {[role.name for role in old.keys() if role not in new.keys()][0]} removed',
                                description=f"**Removed by:** {person} ({person.mention})", color=update_clr)
                            embed.set_footer(
                                text=f"Channel ID: {after.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}")
                            await self.bot.get_channel(server_log_channel).send(embed=embed)
                        if len(new) > len(old):
                            embed = discord.Embed(
                                title=f'Overwrites in {before.name} for {[role.name for role in new.keys() if role not in old.keys()][0]} added',
                                description=f"**Added by:** {person} ({person.mention})", color=update_clr)
                            embed.set_footer(
                                text=f"Channel ID: {after.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}")
                            await self.bot.get_channel(server_log_channel).send(embed=embed)
                        if len(new) == len(old):
                            print('l')
                            changed = []
                            ids = []
                            for i in old:
                                changed.append([1 if old[i] == new[i] else 0][0])

                            for i in range(len(changed)):
                                if changed[i] == 0:
                                    role = [r.id for r in list(old.keys())][i]
                                    most_recent = [event.id for event in await (
                                        after.guild.audit_logs(action=discord.AuditLogAction.overwrite_update,
                                                               user=person)).flatten() if event.extra.id == role][0]
                                    ids.append(most_recent)
                            ids.sort()
                            correct_id = ids[0]
                            role = [e for e in await (
                                after.guild.audit_logs(action=discord.AuditLogAction.overwrite_update,
                                                       user=person)).flatten() if e.id == correct_id][0].extra
                            changes = []
                            o = list(iter(before.overwrites_for(role)))
                            n = list(iter(after.overwrites_for(role)))
                            for i in range(len(o)):
                                if o[i] != n[i]:
                                    changes.append(
                                        f"**{o[i][0].replace('_', ' ')}:** {o[i][1]} → {n[i][1]}\n".replace('True',
                                                                                                            ':white_check_mark:').replace(
                                            'False', ":x:").replace("None", ':white_large_square:'))
                            embed = discord.Embed(title=f'Overwrites in #{after.name} for "{role}" updated',
                                                  description=f"**Updated by:** {person} ({person.mention})",
                                                  color=update_clr)
                            string = ""
                            for change in changes:
                                string += change
                            embed.add_field(name='New overwrites', value=string)
                            embed.set_footer(
                                text=f"Channel ID: {after.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}")
                            await self.bot.get_channel(server_log_channel).send(embed=embed)

                if isinstance(before, discord.VoiceChannel):
                    ok_different = [before.name != after.name, before.overwrites != after.overwrites,
                                    before.bitrate != after.bitrate,
                                    before.video_quality_mode != after.video_quality_mode,
                                    before.rtc_region != after.rtc_region, before.user_limit != after.user_limit].count(
                        True) > 0
                    if ok_different:
                        embed = discord.Embed(title=f"Voice channel {after.name} updated",
                                              description=f"**Updated by:** {person} ({person.mention})",
                                              color=update_clr)
                        before_info = ""
                        after_info = ""
                        if before.name != after.name:
                            before_info += f"**Name:** {before.name}        \n"
                            after_info += f"**Name:** {after.name}      \n"
                        if before.bitrate != after.bitrate:
                            before_info += f"**Bitrate:** {before.bitrate / 1000} kbps        \n"
                            after_info += f"**Bitrate:** {after.bitrate / 1000} kbps        \n"
                        if before.video_quality_mode != after.video_quality_mode:
                            before_info += f"**Video quality mode:** {before.video_quality_mode.name}        \n"
                            after_info += f"**Video quality mode:** {after.video_quality_mode.name}        \n"
                        if before.user_limit != after.user_limit:
                            before_info += f"**User limit:** {before.user_limit}        \n"
                            after_info += f"**User limit:** {after.user_limit}        \n"
                        if before.rtc_region != after.rtc_region:
                            before_info += f"**RTC region:** {before.rtc_region}        \n"
                            after_info += f"**RTC region:** {after.rtc_region}        \n"
                        embed.add_field(name="Before: ", value=before_info)
                        embed.add_field(name="After: ", value=after_info)
                        embed.set_footer(
                            text=f"Channel ID: {after.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}")
                        await self.bot.get_channel(server_log_channel).send(embed=embed)

                        if before.overwrites != after.overwrites:
                            old = before.overwrites
                            new = after.overwrites
                            if len(new) < len(old):
                                embed = discord.Embed(
                                    title=f'Overwrites in {before.name} for {[role.name for role in old.keys() if role not in new.keys()][0]} removed',
                                    description=f"**Removed by:** {person} ({person.mention})")
                                embed.set_footer(text=f"{datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                                await self.bot.get_channel(server_log_channel).send(embed=embed)
                            if len(new) > len(old):
                                embed = discord.Embed(
                                    title=f'Overwrites in {before.name} for {[role.name for role in new.keys() if role not in old.keys()][0]} added',
                                    description=f"**Added by:** {person} ({person.mention})")
                                embed.set_footer(text=f"{datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                                await self.bot.get_channel(server_log_channel).send(embed=embed)
                            if len(new) == len(old):
                                changed = []
                                ids = []
                                for i in old:
                                    changed.append([1 if old[i] == new[i] else 0][0])

                                for i in range(len(changed)):
                                    if changed[i] == 0:
                                        role = [r.id for r in list(old.keys())][i]
                                        most_recent = [event.id for event in await (
                                            after.guild.audit_logs(action=discord.AuditLogAction.overwrite_update,
                                                                   user=person)).flatten() if event.extra.id == role][0]
                                        ids.append(most_recent)
                                ids.sort()
                                correct_id = ids[0]
                                role = [e for e in await (
                                    after.guild.audit_logs(action=discord.AuditLogAction.overwrite_update,
                                                           user=person)).flatten() if e.id == correct_id][0].extra
                                changes = []
                                o = list(iter(before.overwrites_for(role)))
                                n = list(iter(after.overwrites_for(role)))
                                for i in range(len(o)):
                                    if o[i] != n[i]:
                                        changes.append(
                                            f"**{o[i][0].replace('_', ' ')}:** {o[i][1]} → {n[i][1]}\n".replace('True',
                                                                                                                ':white_check_mark:').replace(
                                                'False', ":x:").replace("None", ':white_large_square:'))
                                embed = discord.Embed(title=f'Overwrites in #{after.name} for "{role}" updated',
                                                      description=f"**Updated by:** {person} ({person.mention})")
                                string = ""
                                for change in changes:
                                    string += change
                                embed.add_field(name='New overwrites', value=string)
                                embed.set_footer(
                                    text=f"Channel ID: {after.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}")
                                await self.bot.get_channel(server_log_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', member.guild.id)
        if settings is not None:
            server_log_channel = dict(settings)['server_channel']
            actions = dict(settings)['server_actions']
            if isinstance(server_log_channel, int):
                if member.bot and 'Bot Removed' in actions:
                    embed = discord.Embed(title="Bot removed", description="", color=remove_clr)
                    url = ''
                    if str(member.avatar) != 'None':
                        url += str(member.avatar)
                    else:
                        url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                    embed.set_author(name=str(member), icon_url=url)
                    embed.set_footer(
                        text=f"Bot ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                    who_did_it = (await member.guild.audit_logs(limit=1).flatten())[0].user
                    embed.description = f"**Removed by:** {who_did_it} ({who_did_it.mention})"
                    await self.bot.get_channel(server_log_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        guild = role.guild
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            server_log_channel = dict(settings)['server_channel']
            actions = dict(settings)['server_actions']
            if isinstance(server_log_channel, int) and 'Role Created' in actions:
                user = (await guild.audit_logs(limit=1).flatten())[0].user
                rt = ''
                if role.is_integration():
                    rt += 'Integration'
                else:
                    rt += 'Role'
                embed_info = {'title': f"{rt} created", "user": f"{user} ({user.mention})",
                              "role": f"{role.mention}",
                              "footer": f"Role ID: {role.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}"}
                embed = discord.Embed(title=embed_info['title'],
                                      description=f"**Role:** {embed_info['role']}\n**Created by:** {embed_info['user']}",
                                      color=add_clr)
                embed.set_footer(text=embed_info['footer'])
                await self.bot.get_channel(server_log_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        guild = role.guild
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            server_log_channel = dict(settings)['server_channel']
            actions = dict(settings)['server_actions']
            if isinstance(server_log_channel, int) and 'Role Deleted' in actions:
                user = (await guild.audit_logs(limit=1).flatten())[0].user
                rt = ''
                if role.is_integration():
                    rt += 'Integration'
                else:
                    rt += 'Role'
                embed_info = {'title': f"{rt} deleted", "user": f"{user} ({user.mention})",
                              "role": f"{role.mention}",
                              "footer": f"Role ID: {role.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}"
                              }
                embed = discord.Embed(title=embed_info['title'],
                                      description=f"**Role:** {role.name}\n**Deleted by:** {embed_info['user']}",
                                      color=remove_clr)
                embed.set_footer(text=embed_info['footer'])
                await self.bot.get_channel(server_log_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        guild = after.guild
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            server_log_channel = dict(settings)['server_channel']
            actions = dict(settings)['server_actions']
            if isinstance(server_log_channel, int) and 'Role Updated' in actions:
                who_did_it = \
                    (await after.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update).flatten())[0].user
                embed = discord.Embed(title=f'Role "{before.name}" updated',
                                      description=f"**Updated by:** {who_did_it} ({who_did_it.mention})",
                                      color=update_clr)
                before_info = ''
                after_info = ''

                if before.color != after.color:
                    before_info += f'**Color:** {str(hex(before.color.value))[2:]}      \n'
                    after_info += f'**Color:** {str(hex(after.color.value))[2:]}        \n'
                if before.name != after.name:
                    before_info += f'**Name:** {before.name}        \n'
                    after_info += f'**Name:** {after.name}      \n'
                if before.mentionable != after.mentionable:
                    before_info += f'**Mentionable:** {before.mentionable}      \n'
                    after_info += f'**Mentionable:** {after.mentionable}        \n'
                if before.hoist != after.hoist:
                    before_info += f'**Hoist:** {before.hoist}      \n'
                    after_info += f'**Hoist:** {after.hoist}        \n'
                if before_info != '':
                    embed.add_field(name="Before", value=before_info)
                    embed.add_field(name="After", value=after_info)
                if before.permissions != after.permissions:
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
                        text=f"Role ID: {after.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}")
                    await self.bot.get_channel(server_log_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
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

        invite_info = {'code': invite.code, 'channel': f"{invite.channel} ({invite.channel.mention})", 'max_age': age,
                       'max_uses': uses, 'expiry_time': invite.max_age, 'temporary': invite.temporary,
                       'creator': f"{invite.inviter} ({invite.inviter.mention})"}
        guild = invite.guild
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            server_log_channel = dict(settings)['server_channel']
            actions = dict(settings)['server_actions']
            if isinstance(server_log_channel, int) and 'Invite Created' in actions:
                embed_info = {'title': f"Invite created", "user": f"{invite.inviter} ({invite.inviter.mention})",
                              "info": f"**Code:** {invite_info['code']}\n**Channel:** {invite_info['channel']}\n**Max age in seconds:** {invite_info['max_age']}\n**Max uses:** {invite_info['max_uses']}\n**Temporary:** {str(invite_info['temporary']).lower()}\n**Created by:** {invite_info['creator']}",
                              "footer": f"{datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}"
                              }
                embed = discord.Embed(title=embed_info['title'],
                                      description=embed_info['info'], color=add_clr)
                embed.set_footer(text=embed_info['footer'])
                await self.bot.get_channel(server_log_channel).send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        uses = invite.max_uses
        if invite.max_uses == 0:
            uses -= uses
            uses = str(uses)
            uses = uses[0:0]
            uses += 'unlimited'

        guild = invite.guild

        invite_info = {'code': invite.code,
                       'creator': f"{(await guild.audit_logs(limit=1).flatten())[0].user} ({(await guild.audit_logs(limit=1).flatten())[0].user.mention})"}
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            server_log_channel = dict(settings)['server_channel']
            actions = dict(settings)['server_actions']
            if isinstance(server_log_channel, int) and 'Invite Deleted' in actions:
                embed_info = {'title': f"Invite deleted",
                              "info": f"**Code:** {invite_info['code']}\n**Deleted by:** {invite_info['creator']}",
                              "footer": f"{datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}"}
                embed = discord.Embed(title=embed_info['title'], description=embed_info['info'], color=remove_clr)
                embed.set_footer(text=embed_info['footer'])
                await self.bot.get_channel(server_log_channel).send(embed=embed)


class VCLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self._last_member = None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        guild = member.guild
        settings = await conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            vc_channel = dict(settings)['voicestate_channel']
            actions = dict(settings)['vc_actions']
            embed_info = {"footer": f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%y %H:%M:%S')}"}
            if isinstance(vc_channel, int):
                if before.channel is not None and after.channel is not None and "Member Moved" in actions and before.channel != after.channel:
                    if len(await after.channel.guild.audit_logs(limit=1,
                                                                action=discord.AuditLogAction.member_move).flatten()) > 0:
                        user = (await after.channel.guild.audit_logs(limit=1,
                                                                     action=discord.AuditLogAction.member_move).flatten())[
                            0].user
                        embed_info['title'] = "Member moved"
                        embed_info[
                            'info'] = f'**Moved from:** {before.channel.mention}\n**Moved to:** {after.channel.mention}\n**Moved by:** {user} ({user.mention})'
                    else:
                        embed_info['title'] = "Member switched voice channel"
                        embed_info[
                            'info'] = f'**Went from:** {before.channel.mention}\n**Went to:** {after.channel.mention}'
                elif after.channel is not None and before.channel is None and "Member Joined VC" in actions:
                    embed_info['title'] = "Member joined voice channel"
                    embed_info['info'] = f'**Channel:** {after.channel.mention}'
                elif after.channel is None and before.channel is not None and "Member Left VC" in actions:
                    embed_info['title'] = "Member left voice channel"
                    embed_info['info'] = f'**Channel:** {before.channel.mention}'
                embed = discord.Embed(title=embed_info['title'], description=embed_info['info'], color=update_clr)
                url = ''
                if str(member.avatar) != 'None':
                    url += str(member.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(member), icon_url=url)
                embed.set_footer(text=embed_info['footer'])
                await self.bot.get_channel(vc_channel).send(embed=embed)


asyncio.get_event_loop().run_until_complete(connections())


def setup(bot):
    bot.add_cog(MessageLog(bot))
    bot.add_cog(MemberLog(bot))
    bot.add_cog(Moderation(bot))
    bot.add_cog(GuildUpdate(bot))
    bot.add_cog(VCLogging(bot))
