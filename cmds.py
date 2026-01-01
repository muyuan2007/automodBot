import gc
import json
from discord.commands import slash_command
import discord
from discord.ext import commands
from discord import option
import asyncio
import asyncpg
from features import cmd_funcs
from psutil import Process
from datetime import datetime

s = {'badlinks': 'Blacklisted links', 'badwords': 'Blacklisted words', 'badnicks': 'Blacklisted nicknames',
     'badnames': 'Blacklisted usernames', 'badstatuses': 'Blacklisted custom statuses'}

table_dict = {'General settings': 'automodgeneral', 'Action logging': 'modlogs', 'Message spam': 'messagespam', 'Emoji spam': 'emojispam',
              'Mention spam': 'mentionspam', 'Sticker spam': 'stickerspam', 'Attachment spam': 'attachmentspam',
              'Link spam': 'linkspam', 'Duplicate characters': 'duplicatecharacters',
              'Duplicate messages': 'duplicatemessages', 'Line breaks': 'linebreaks', 'Capitals': 'toomanycaps',
              'Invites': 'invites', 'Selfbotting': 'selfbot',
              'Bad words': 'badwords', 'Bad links': 'badlinks',
              'Bad nicknames': 'badnicks', 'Bad usernames': 'badnames', 'Bad custom statuses': 'badstatuses',
              'Automated punishments': 'autopunish', ' Auto kick/ban': 'autokickban',
              }

print("tardation")

d = {}
me = 825455379424739388
with open('tk.json', 'r') as f:
    info = json.load(f)['db']
    d.update(info)
    f.close()

async def handle_send(member, embed):
    try:
        await member.send(embed=embed)
    except:
        pass


async def connections():
    global warn_conn
    warn_conn = await asyncpg.create_pool(host=d['host'], port=d['port'], user=d['user'], password=d['pwd'],
                                          database=d['db'])


def has_perms(member1, member2, permission):
    guild = member2.guild
    perms = dict(list(member1.guild_permissions))
    if (perms[permission] and not guild.owner_id == member1.id and member2.top_role.position < member1.top_role.position) or guild.owner_id == member1.id:
        return True
    return False


def has_guild_permissions(b, permission):
    bot_perms = dict(list(b.guild_permissions))
    if bot_perms[permission]:
        return True
    return False


class Punishing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @slash_command(description="Warn a member")
    @option("member", description="Member to warn")
    @option("amount", description="Amount of points to warn")
    @option("reason", description="Reason to warn member")
    @commands.has_permissions(kick_members=True, ban_members=True)
    async def warn(self, ctx, member: discord.Member, amount: int, reason=None):
        try:
            if has_perms(ctx.author, member, "ban_members") and has_perms(ctx.author, member, "kick_members"):
                await cmd_funcs.handle_warn(self.bot.conn, self.bot, ctx, member, amount, reason)
            else:
                await ctx.respond("<:amgx_error:1045162027737415751> You don't have permissions to warn this member.")
        except:
            pass

    @warn.error
    async def handle_warn_error(self, ctx, error):
        try:
            await cmd_funcs.handle_warn_error(ctx, error)
        except:
            pass


    @slash_command(description="Bulk delete messages")
    @option("amount", description="Number of messages to delete (cannot exceed 500)")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        try:
            if has_guild_permissions(ctx.guild.me, 'manage_messages'):
                await cmd_funcs.handle_purge(ctx, amount)
            else:
                await ctx.respond("<:amgx_error:1045162027737415751> I don't have permissions to purge messages.")
        except:
            pass

    @purge.error
    async def purge_error(self, ctx, error):
        try:
            await cmd_funcs.handle_purge_error(ctx, error)
        except:
            pass

    @slash_command(description="Remove warning points from a member")
    @option("member", description="Member to remove warning points from")
    @option("amount", description="Number of warning points to remove (0 to remove all points)")
    @commands.has_permissions(kick_members=True, ban_members=True)
    async def unwarn(self, ctx, member: discord.Member, amount: int):
        try:
            print(has_perms(ctx.author, member, "kick_members") and has_perms(ctx.author, member, "ban_members"))
            await cmd_funcs.unwarn(self.bot.conn, self.bot, member, amount, ctx, ctx.author)
        except:
            pass


    @unwarn.error
    async def unwarn_error(self, ctx, error):
        try:
            await cmd_funcs.handle_unwarn_error(ctx, error)
        except:
            pass


    @slash_command(description="Check a member's warn points")
    @option("member", description="Member to check warn points for")
    async def warns(self, ctx, *, member: discord.Member = None):
        try:
            if member is None:
                await cmd_funcs.handle_warns(self.bot.conn, ctx, ctx.author)
            else:
                await cmd_funcs.handle_warns(self.bot.conn, ctx, member)
        except:
            pass



    @warns.error
    async def send_who(self, ctx, error):
        try:
            await cmd_funcs.handle_send_who(self.bot.conn, ctx, error)
        except:
            pass


    @slash_command(description="Mute a member")
    @option("member", description="Member to mute")
    @option("duration", description="Mute duration in seconds")
    @option("reason", description="Reason to mute member")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: int, *, reason=None):
        try:
            if has_perms(ctx.guild.me, member, 'moderate_members') and ctx.author != member:
                if has_perms(ctx.author, member, 'moderate_members'):
                    await cmd_funcs.handle_mute(self.bot.conn, self.bot, ctx, member, duration, reason)
                else:
                    await ctx.respond(f"<:amgx_error:1045162027737415751> You don't have permissions to mute {member}.")
            else:
                if ctx.author != member:
                    await ctx.respond(f"<:amgx_error:1045162027737415751> I don't have permissions to mute {member}.")
                else:
                    await ctx.respond(f"<:amgx_error:1045162027737415751> You cannot moderate yourself!")
        except:
            pass


    @mute.error
    async def mute_error(self, ctx, error):
        try:
            await cmd_funcs.handle_mute_error(ctx, error)
        except:
            pass


    @slash_command(description="Kick a member")
    @commands.has_permissions(kick_members=True)
    @option("member", description="Member to kick")
    @option("reason", description="Reason to kick member")
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        try:
            if has_perms(ctx.guild.me, member, 'kick_members') and ctx.author != member:
                if has_perms(ctx.author, member, 'kick_members'):
                    await cmd_funcs.handle_kick(ctx, member, reason)
                else:
                    await ctx.respond(f"<:amgx_error:1045162027737415751> You don't have permissions to kick {member}.")
            else:
                if ctx.author != member:
                    await ctx.respond(f"<:amgx_error:1045162027737415751> I don't have permissions to kick {member}.")
                else:
                    await ctx.respond(f"<:amgx_error:1045162027737415751> You cannot moderate yourself!")
        except:
            pass


    @kick.error
    async def kick_error(self, ctx, error):
        try:
            await cmd_funcs.handle_kick_error(ctx, error)
        except:
            pass


    @slash_command(description="Temporarily ban a member")
    @commands.has_permissions(ban_members=True)
    @option("member", description="Member to ban")
    @option("duration", description="Duration of ban in seconds")
    @option("reason", description="Reason to ban member")
    async def tempban(self, ctx, member: discord.Member, duration: int, *, reason=None):
        try:
            if has_perms(ctx.guild.me, member, 'ban_members') and member != ctx.author:
                if has_perms(ctx.author, member, 'ban_members'):
                    await cmd_funcs.handle_tempban(self.bot.conn, self.bot, ctx, member, duration, reason, ctx.author)
                else:
                    await ctx.respond(f"<:amgx_error:1045162027737415751> You don't have permissions to ban {member}.")
            else:
                if ctx.author != member:
                    await ctx.respond(f"<:amgx_error:1045162027737415751> I don't have permissions to ban {member}.")
                else:
                    await ctx.respond('<:amgx_error:1045162027737415751> You cannot moderate yourself!')
        except:
            pass


    @tempban.error
    async def handle_tempban_error(self, ctx, error):
        try:
            await cmd_funcs.handle_tempban_error(ctx, error)
        except:
            pass


    @slash_command(description="Ban a member")
    @option("member", description="Member to ban")
    @option("reason", description="Reason to ban member")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        try:
            if has_perms(ctx.guild.me, member, 'ban_members') and member != ctx.author:
                if has_perms(ctx.author, member, 'ban_members'):
                    await cmd_funcs.handle_ban(self.bot.conn, self.bot, ctx, member, reason)
                else:
                    await ctx.respond(f"<:amgx_error:1045162027737415751> You don't have permissions to ban {member}.")
            else:
                if ctx.author != member:
                    await ctx.respond(f"<:amgx_error:1045162027737415751> I don't have permissions to ban {member}.")
                else:
                    await ctx.respond('<:amgx_error:1045162027737415751> You cannot moderate yourself!')
        except:
            pass

    @ban.error
    async def ban_error(self, ctx, error):
        try:
            await cmd_funcs.handle_ban_error(ctx, error)
        except:
            pass


    @slash_command(description="Unmute a member")
    @option("member", description="Member to unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        try:
            if has_perms(ctx.guild.me, member, 'moderate_members') and ctx.author != member:
                if has_perms(ctx.author, member, 'moderate_members'):
                    await cmd_funcs.handle_unmute(self.bot.conn, self.bot, ctx, member)
                else:
                    await ctx.respond(f"<:amgx_error:1045162027737415751> You don't have permissions to unmute {member}.")
            else:
                if ctx.author != member:
                    await ctx.respond(f"<:amgx_error:1045162027737415751> I don't have permissions to unmute {member}.")
                else:
                    await ctx.respond('<:amgx_error:1045162027737415751> You cannot moderate yourself!')
        except:
            pass


    @unmute.error
    async def unmute_error(self, ctx, error):
        try:
            await cmd_funcs.handle_unmute_error(ctx, error)
        except:
            pass


    @slash_command(description="Unban a member")
    @option("member", description="Member to unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, member: discord.User):
        try:
            if has_guild_permissions(ctx.guild.me, 'ban_members') and member != ctx.author:
                if has_guild_permissions(ctx.author, 'ban_members'):
                    await cmd_funcs.handle_unban(ctx, member)
                else:
                    await ctx.respond(f"<:amgx_error:1045162027737415751> You don't have permissions to unban {member}.")
            else:
                if ctx.author != member:
                    await ctx.respond(f"<:amgx_error:1045162027737415751> I don't have permissions to unban {member}.")
                else:
                    await ctx.respond('<:amgx_error:1045162027737415751> You cannot moderate yourself!')
        except:
            pass


    @unban.error
    @commands.has_permissions(ban_members=True)
    async def unban_error(self, ctx, error):
        try:
            await cmd_funcs.handle_unban_error(ctx, error)
        except:
            pass


conn_thing = {'conn_count': 0}


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @slash_command(description="Provide feedback to help improve AMGX!")
    @option('title', description="Briefly summarize your feedback!")
    @option('feedback', description="Provide us with all the feedback you want, in detail!")
    async def feedback(self, ctx, title, feedback):
        try:
            await cmd_funcs.handle_feedback(self.bot, title, feedback)
            await ctx.respond(f"<:amgx_success:1045162009903243294> Feedback sent.")
        except:
            pass

    @slash_command(description="Check dashboard settings for a certain bot setting")
    @option('setting', description="The type of setting to check", choices=list(table_dict.keys()))
    async def amsettings(self, ctx, setting):
        try:
            await cmd_funcs.handle_amsettings(self.bot.conn, ctx, table_dict[setting])
        except:
            pass

    @slash_command(description="Check all of member's infractions")
    @option("member", description="The member to check infractions for")
    @option("page", description="The member to check infractions for")
    async def infractions(self, ctx, member: discord.Member = None, page: int = 1):
        try:
            await cmd_funcs.handle_infractions(self.bot.conn, ctx, member, page)
        except:
            pass

    @infractions.error
    async def inf_err(self, ctx, error):
        try:
            await cmd_funcs.handle_inf_err(ctx, error)
        except:
            pass

    @commands.Cog.listener()
    async def on_disconnect(self):
        # try:
        #     await warn_conn.close()
        # except:
        #     pass
        self.bot._connection._messages.clear()
        self.bot._connection._stickers.clear()
        self.bot._connection._polls.clear()
        # try:
        #     del warn_conn
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
    #

def setup(bot):
    bot.add_cog(Punishing(bot))
    bot.add_cog(Settings(bot))

