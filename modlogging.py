import asyncio
import gc
import json
from asyncio import sleep
from discord import Forbidden, AuditLogAction
from discord.ext import commands
import asyncpg
from features import modlog_funcs
from datetime import datetime

d = {}

with open('tk.json', 'r') as f:
    info = json.load(f)['db']
    d.update(info)
    f.close()


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


class InviteTracker:
    def __init__(self, bot):
        self.bot = bot
        self._cache = {}
        self.add_listeners()

    def add_listeners(self):
        self.bot.add_listener(self.cache_invites, "on_ready")
        self.bot.add_listener(self.update_invite_cache, "on_invite_create")
        self.bot.add_listener(self.remove_invite_cache, "on_invite_delete")
        self.bot.add_listener(self.add_guild_cache, "on_guild_join")
        self.bot.add_listener(self.remove_guild_cache, "on_guild_remove")

    async def cache_invites(self):
        for guild in self.bot.guilds:
            try:
                self._cache[guild.id] = {}
                for invite in await guild.invites():
                    self._cache[guild.id][invite.code] = invite
            except Forbidden:
                continue

    async def update_invite_cache(self, invite):
        if invite.guild.id not in self._cache.keys():
            self._cache[invite.guild.id] = {}
        self._cache[invite.guild.id][invite.code] = invite

    async def remove_invite_cache(self, invite):
        if invite.guild.id not in self._cache.keys():
            return
        ref_invite = self._cache[invite.guild.id][invite.code]
        if (
                ref_invite.created_at.timestamp() + ref_invite.max_age > datetime.utcnow().timestamp() or ref_invite.max_age == 0) and ref_invite.max_uses > 0 and ref_invite.uses == ref_invite.max_uses - 1:
            try:
                async for entry in invite.guild.audit_logs(limit=1, action=AuditLogAction.invite_delete):
                    if entry.target.code != invite.code:
                        self._cache[invite.guild.id][ref_invite.code].revoked = True
                        return
                else:
                    self._cache[invite.guild.id][ref_invite.code].revoked = True
                    return
            except Forbidden:
                self._cache[invite.guild.id][ref_invite.code].revoked = True
                return
        else:
            self._cache[invite.guild.id].pop(invite.code)

    async def add_guild_cache(self, guild):
        self._cache[guild.id] = {}
        for invite in await guild.invites():
            self._cache[guild.id][invite.code] = invite

    async def remove_guild_cache(self, guild):
        try:
            self._cache.pop(guild.id)
        except KeyError:
            return

    async def fetch_inviter(self, member):
        await sleep(self.bot.latency)
        for new_invite in await member.guild.invites():
            for cached_invite in self._cache[member.guild.id].values():
                if new_invite.code == cached_invite.code and new_invite.uses - cached_invite.uses == 1 or cached_invite.revoked:
                    if cached_invite.revoked:
                        self._cache[member.guild.id].pop(cached_invite.code)
                    elif new_invite.inviter == cached_invite.inviter:
                        self._cache[member.guild.id][cached_invite.code] = new_invite
                    else:
                        self._cache[member.guild.id][cached_invite.code].uses += 1
                    return [cached_invite, cached_invite.inviter]


class MessageLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        try:
            await modlog_funcs.message_edit(self.bot.conn, self.bot, before, after)
        except:
            pass

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        print("tard")
        await modlog_funcs.message_delete(self.bot.conn, self.bot, message)
        # try:
        #     await modlog_funcs.message_delete(conn, self.bot, message)
        # except:
        #     print("bruh")
        #     pass

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        try:
            await modlog_funcs.raw_bulk_message_delete(self.bot.conn, self.bot, payload)
        except:
            pass


class MemberLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tracker = InviteTracker(bot)
        self._last_member = None

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        try:
            await modlog_funcs.user_update(self.bot.conn, self.bot, before, after)
        except:
            pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            await modlog_funcs.member_join(self.bot.conn, self.bot, member, self.tracker)
        except:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            await modlog_funcs.member_remove(self.bot.conn, self.bot, member)
        except:
            pass


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        try:
            await modlog_funcs.member_ban(user)
        except:
            pass


class GuildUpdate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.Cog.listener()
    async def on_audit_log_entry(self, entry):
        try:
            await modlog_funcs.audit_log_handle(self.bot.conn, self.bot, entry)
        except:
            pass


conn_thing = {'conn_count': 0}


class VCLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self._last_member = None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        try:
            await modlog_funcs.voice_state_update(self.bot.conn, self.bot, member, before, after)
        except:
            pass

    @commands.Cog.listener()
    async def on_disconnect(self):
        # try:
        #     await conn.close()
        # except:
        #     pass
        self.bot._connection._messages.clear()
        self.bot._connection._stickers.clear()
        self.bot._connection._polls.clear()
        # try:
        #     del conn
        # except:
        #     pass
        gc.collect()

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


def setup(bot):
    bot.add_cog(MessageLog(bot))
    bot.add_cog(MemberLog(bot))
    bot.add_cog(Moderation(bot))
    bot.add_cog(GuildUpdate(bot))
    bot.add_cog(VCLogging(bot))
