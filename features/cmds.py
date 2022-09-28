import re

import discord
from discord.ext import commands
import asyncio
import asyncpg
import datetime
from features.punishing import warn, log_mute, log_unmute, log_tempban, log_ban, log_infraction
from difflib import SequenceMatcher as sm


tables = ['modlogs','messagespam', 'emojispam', 'mentionspam', 'stickerspam', 'attachmentspam', 'linkspam','duplicatecharacters','duplicatemessages','linebreaks','toomanycaps','invites','selfbot','nsfwcontent','hatespeech','badwords','badlinks','badnicks','badnames','badstatuses','nsfwpfp','autopunish','autokickban', 'automodgeneral']
setting_stuff = ["Modlog settings","Message spam settings","Emoji spam settings","Mention spam settings","Sticker spam settings","Attachment spam settings","Link spam settings", "Duplicate character settings", "Duplicate message settings", "Line break settings", "Capitals settings", "Invite settings", "Selfbot settings", "NSFW content settings", "Hate speech settings",'Bad word settings','Bad link settings','Bad nickname settings','Bad username settings','Bad custom status settings','NSFW avatar settings', 'Autopunish settings',' Auto kick/ban settings', 'Whitelist settings']
s = {'badlinks': 'Blacklisted links','badwords': 'Blacklisted words','badnicks': 'Blacklisted nicknames','badnames': 'Blacklisted usernames','badstatuses': 'Blacklisted custom statuses'}
overusing_types = {'duplicatemessages': 'repeated messages', 'linebreaks': 'line breaks', 'toomanycaps': '% caps', 'duplicate characters': 'repeated character(s)'}

default_settings = {'messagespam': {"punishments":["Delete message","Mute","Warn"],"maxes":[5,2],"channel_whitelists":'{}',"role_whitelists":'{}',"points":5,"timeval":40,"timeunit":"minutes"}, 'emojispam': {"punishments":["Delete message","Mute"],"maxes":[5,2],"channel_whitelists":'{}',"role_whitelists":'{}',"points":0,"timeval":20,"timeunit":"minutes"}, 'mentionspam': {"punishments":["Delete message","Mute","Warn"],"maxes":[8,2],"channel_whitelists":'{}',"role_whitelists":'{}',"points":6,"timeval":3,"timeunit":"hours"}, 'stickerspam': {"punishments":["Delete message","Mute"],"maxes":[5,2],"channel_whitelists":'{}',"role_whitelists":'{}',"points":0,"timeval":2,"timeunit":"hours"}, 'attachmentspam': {"punishments":["Delete message","Mute","Warn"],"maxes":[5,2],"channel_whitelists":'{}',"role_whitelists":'{}',"points":5,"timeval":3,"timeunit":"hours"}, 'linkspam': {"punishments":["Delete message","Mute"],"maxes":[6,2],"channel_whitelists":'{}',"role_whitelists":'{}',"points":0,"timeval":2,"timeunit":"hours"}, 'linebreaks': {"punishments":["Delete message","Mute"],"top":6,"points":0,"timeunit":"minutes","timeval":30,"channel_whitelists":'{}',"role_whitelists":'{}'}, 'toomanycaps': {"punishments":["Delete message","Mute","Warn"],"top":90,"points":5,"timeunit":"minutes","timeval":45,"channel_whitelists":'{}',"role_whitelists":'{}'}, 'duplicatemessages': {"punishments":["Delete message","Mute","Warn"],"top":5,"points":4,"timeunit":"hours","timeval":2,"channel_whitelists":'{}',"role_whitelists":'{}'}, 'duplicatecharacters': {"punishments":["Delete message","Mute","Warn"],"top":10,"points":5,"timeunit":"minutes","timeval":45,"channel_whitelists":'{}',"role_whitelists":'{}'}, 'invites': {"punishments":["Delete message","Warn"],"points":5,"timeunit":"minutes","timeval":0,"channel_whitelists":'{}',"role_whitelists":'{}'}, 'nsfwcontent': {"punishments":["Delete message","Ban"],"points":0,"timeunit":"minutes","timeval":0,"channel_whitelists":'{}',"role_whitelists":'{}'}, 'hatespeech': {"punishments":["Delete message","Warn","Tempban"],"points":15,"timeunit":"days","timeval":3,"channel_whitelists":'{}',"role_whitelists":'{}'}, 'selfbot': {"punishments":["Delete message","Ban"],"points":0,"timeunit":"minutes","timeval":0,"role_whitelists":'{}'},


'badwords': [str({"title":"slurs","punishments":["Delete message","Warn"],"words":{"nigger":"Substring","fag":"Substring","tranny":"Substring","trannies":"Substring","chingchong":"Substring","ching chang":"Substring"},"points":20,"timeval":0,"timeunit":"minutes","whitelistedRoles":{},"whitelistedChannels":{},"duration":0})],

'badlinks': [str({"title":"nsfw","punishments":["Delete message","Ban"],"words":{"pornhub":"Substring","xvideos":"Substring","spankbang":"Substring","xnxx":"Substring","xhamster":"Substring","chaturbate":"Substring","youporn":"Substring","tnaflix":"Substring","nuvid":"Substring","drtuber":"Substring","xxxbunker":"Substring","xxxvideo":"Substring","fapvidhd":"Substring","xxxvideos247":"Substring","pornhd":"Substring","redtube":"Substring","fapster":"Substring","tastyblacks":"Substring","hclips":"Substring","tube8":"Substring"},"points":0,"timeval":0,"timeunit":"minutes","whitelistedRoles":{},"whitelistedChannels":{},"duration":0}),str({"title":"gory","punishments":["Delete message","Ban"],"words":{"bestgore":"Substring","theync":"Substring","kaotic":"Substring","goregrish":"Substring","crazyshit":"Substring","efukt":"Substring","runthegauntlet":"Substring","ogrishforum":"Substring"},"points":0,"timeval":0,"timeunit":"minutes","whitelistedRoles":{},"whitelistedChannels":{},"duration":0})],

'badnicks': [str({"title":"triggering","punishments":["Ban"],"words":{"hitler":"Substring","nazi":"Substring","adolf":"Substring","holocaust":"Substring","auschwitz":"Substring","rapist":"Substring","porn":"Substring","molest":"Substring","traffick":"Substring","rape":"NoSubstring","raping":"NoSubstring","pedo":"Substring","paedo":"Substring","sex":"NoSubstring"},"points":0,"timeval":0,"timeunit":"minutes","whitelistedRoles":{},"whitelistedChannels":{},"duration":0}),str({"title":"slurs","punishments":["Warn","Tempban"],"words":{"nigger":"Substring","fag":"Substring","tranny":"Substring","trannies":"Substring","chingchong":"Substring","ching chang":"Substring"},"points":20,"timeval":3,"timeunit":"days","whitelistedRoles":{},"whitelistedChannels":{},"duration":0})],

'badnames': [str({"title":"triggering","punishments":["Ban"],"words":{"hitler":"Substring","nazi":"Substring","adolf":"Substring","holocaust":"Substring","auschwitz":"Substring","rapist":"Substring","porn":"Substring","molest":"Substring","traffick":"Substring","rape":"NoSubstring","raping":"NoSubstring","pedo":"Substring","paedo":"Substring","sex":"NoSubstring"},"points":0,"timeval":0,"timeunit":"minutes","whitelistedRoles":{},"whitelistedChannels":{},"duration":0}),str({"title":"slurs","punishments":["Warn","Tempban"],"words":{"nigger":"Substring","fag":"Substring","tranny":"Substring","trannies":"Substring","chingchong":"Substring","ching chang":"Substring"},"points":20,"timeval":3,"timeunit":"days","whitelistedRoles":{},"whitelistedChannels":{},"duration":0})],

'badstatuses': [str({"title":"triggering","punishments":["Ban"],"words":{"hitler":"Substring","nazi":"Substring","adolf":"Substring","holocaust":"Substring","auschwitz":"Substring","rapist":"Substring","porn":"Substring","molest":"Substring","traffick":"Substring","rape":"NoSubstring","raping":"NoSubstring","pedo":"Substring","paedo":"Substring","sex":"NoSubstring"},"points":0,"timeval":0,"timeunit":"minutes","whitelistedRoles":{},"whitelistedChannels":{},"duration":0}),str({"title":"slurs","punishments":["Warn","Tempban"],"words":{"nigger":"Substring","fag":"Substring","tranny":"Substring","trannies":"Substring","chingchong":"Substring","ching chang":"Substring"},"points":20,"timeval":3,"timeunit":"days","whitelistedRoles":{},"whitelistedChannels":{},"duration":0})],


'nsfwpfp': {"punishments":["Ban"],"points":0,"timeunit":"minutes","timeval":0,"role_whitelists":'{}'}}

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
badProfiles = { 'hitler': 'Substring', 'nazi': 'Substring', 'adolf': 'Substring', 'holocaust': 'Substring', 'auschwitz': 'Substring', 'rapist': 'Substring', 'porn': 'Substring', 'molest': 'Substring', 'traffick': 'Substring', 'rape': 'NoSubstring', 'raping': 'NoSubstring', 'pedo': 'Substring', 'paedo': 'Substring', 'sex': 'NoSubstring'}

default_modlogs = {'message_channel': '', 'member_channel': '', 'moderation_channel': '', 'server_channel': '', 'voicestate_channel': '', 'message_actions': ['Message Deleted', 'Message Edited', 'Message Bulk Deletion'], 'member_actions': ['Username Changed', 'Avatar Changed', 'Custom Status Changed', 'Member Joined', 'Roles Changed', 'Nickname Changed', 'Member Left'], 'moderations': ['Member Warned', 'Member Kicked', 'Infraction Removed', 'Member Tempbanned', 'Member Muted', 'Member Unbanned', 'Member Unmuted', 'Member Banned'], 'server_actions': ['Emoji Added', 'Emoji Updated', 'Emoji Deleted', 'Channel Deleted', 'Channel Updated', 'Channel Created', 'Role Created', 'Role Updated', 'Role Deleted', 'Server Icon Changed', 'Discovery Splash Changed', 'Server Name Changed', 'AFK Channel Changed', 'System Channel Changed', 'Default Notifications Changed', 'Bot Removed', 'Bot Added', 'AFK Timeout Changed', 'Invite Splash Changed', 'Banner Changed', 'Explicit Filter Changed', 'Invite Deleted', 'Invite Created', 'Server Owner Changed', 'MFA Changed', 'Verification Level Changed'], 'vc_actions': ['Member Joined VC', 'Member Left VC', 'Member Moved']}
default_autopunish = [{'type':"mute", "durationType": "hours", "duration": 6, "threshold": 15},{'type':"kick", "durationType": "minutes", "duration": 1, "threshold": 30},{'type':"tempban", "durationType": "days", "duration": 3, "threshold": 45},{'type':"ban", "durationType": "minutes", "duration": 1, "threshold": 60}]
default_autokb = {'banrules':[str({"type": "nsfwpfp", "timeVal": 24, "timeUnit": "hours", "usernames": {}, "statuses": {}}),str({"type": "username", "timeVal": 24, "timeUnit": "hours", "usernames": badProfiles, "statuses": {}}),str({"type": "status", "timeVal": 24, "timeUnit": "hours", "usernames": {}, "statuses": badProfiles})],'kickrules':[str({"type": "accountAge", "timeVal": 7, "timeUnit": "days", "usernames": {}, "statuses": {}}),str({"type": "promoName", "timeVal": 24, "timeUnit": "hours", "usernames": {}, "statuses": {}})]}
d = {}

with open('tk.json','r+') as f:
    info = eval(f.read())['db']
    for key in list(info.keys()):
        d[key] = info[key]


async def handle_send(member, embed):
    try:
        await member.send(embed=embed)
    except:
        print('a')


def settings_to_embed(settings, autotype, ind):
    tba = []
    if autotype == 'spam':
        punishments = settings['punishments']
        m = 'maxes'
        p = settings['points']
        timeval = settings['timeval']
        unit = settings['timeunit']
        tba.append(f"**Punishments: **{', '.join(punishments)}")
        tba.append(f"**Maxes: **{settings[m][0]} in {settings[m][1]} seconds")
        if 'Warn' in punishments and p not in [0, 1, None]:
            tba.append(f'**Warn points: **{p}')
        if 'Mute' in punishments and timeval not in [0, 1, None]:
            tba.append(f"**Mute duration: **{timeval} {unit}")
        if 'Tempban' in punishments and timeval not in [0, 1, None]:
            tba.append(f"**Tempban duration: **{timeval} {unit}")
        channel_whitelists = eval(settings['channel_whitelists'])
        ch_wl = ", ".join([f"<#{ch}>" for ch in list(channel_whitelists.values())])
        role_whitelists = eval(settings['role_whitelists'])
        rl_wl = (", ".join([f"<@&{rl}>" for rl in list(role_whitelists.values())]))
        tba.append(f"**Channel whitelists: **{ch_wl}")
        tba.append(f"**Role whitelists: **{rl_wl}")
    if autotype == 'toomuch':
        a = ''
        if ind == 10:
            a += '% caps'
        punishments = settings['punishments']
        m = 'top'
        p = settings['points']
        timeval = settings['timeval']
        unit = settings['timeunit']
        tba.append(f"**Punishments: **{', '.join(punishments)}")
        tba.append(f"**Max: **{settings[m]}{a}")
        if 'Warn' in punishments and p not in [0, 1, None]:
            tba.append(f'**Warn points: **{p}')
        if 'Mute' in punishments and timeval not in [0, 1, None]:
            tba.append(f"**Mute duration: **{timeval} {unit}")
        if 'Tempban' in punishments and timeval not in [0, 1, None]:
            tba.append(f"**Tempban duration: **{timeval} {unit}")
        channel_whitelists = eval(settings['channel_whitelists'])
        ch_wl = ", ".join([f"<#{ch}>" for ch in list(channel_whitelists.values())])
        role_whitelists = eval(settings['role_whitelists'])
        rl_wl = (", ".join([f"<@&{rl}>" for rl in list(role_whitelists.values())]))
        tba.append(f"**Channel whitelists: **{ch_wl}")
        tba.append(f"**Role whitelists: **{rl_wl}")
    if autotype == 'unacceptable':
        if 'channel_whitelists' in settings:
            punishments = settings['punishments']
            p = settings['points']
            timeval = settings['timeval']
            unit = settings['timeunit']
            tba.append(f"**Punishments: **{', '.join(punishments)}")
            if 'Warn' in punishments and p not in [0, 1, None]:
                tba.append(f'**Warn points: **{p}')
            if 'Mute' in punishments and timeval not in [0, 1, None]:
                tba.append(f"**Mute duration: **{timeval} {unit}")
            if 'Tempban' in punishments and timeval not in [0, 1, None]:
                tba.append(f"**Tempban duration: **{timeval} {unit}")
            channel_whitelists = eval(settings['channel_whitelists'])
            ch_wl = ", ".join([f"<#{ch}>" for ch in list(channel_whitelists.values())])
            role_whitelists = eval(settings['role_whitelists'])
            rl_wl = (", ".join([f"<@&{rl}>" for rl in list(role_whitelists.values())]))
            tba.append(f"**Channel whitelists: **{ch_wl}")
            tba.append(f"**Role whitelists: **{rl_wl}")
        role_whitelists = eval(settings['role_whitelists'])
        rl_wl = (", ".join([f"<@&{rl}>" for rl in list(role_whitelists.values())]))
        tba.append(f"**Role whitelists: **{rl_wl}")
    if autotype == 'modlogs':
        chs = ['Message log channel', 'Member log channel', 'Moderation log channel', 'Server log channel',
               'Voice state log channel']

        actions = ['Message actions', 'Member actions', 'Moderations', 'Server actions', 'Voice state actions']
        a = ['message_actions', 'member_actions', 'moderations', 'server_actions', 'vc_actions']
        msg_ch = settings['message_channel']
        mem_ch = settings['member_channel']
        mod_ch = settings['moderation_channel']
        ser_ch = settings['server_channel']
        vc_ch = settings['voicestate_channel']
        channels = [msg_ch, mem_ch, mod_ch, ser_ch, vc_ch]
        for ch in channels:
            if isinstance(ch, int):
                tba.append(f"**{chs[channels.index(ch)]}: **<#{ch}>")
            else:
                tba.append(f"**{chs[channels.index(ch)]}**:")
        for k in a:
            if isinstance(settings[k], list):
                tba.append(f"**{actions[a.index(k)]}: **{', '.join(settings[k])}")
            else:
                tba.append(f"**{actions[a.index(k)]}: **")
    if autotype == 'general':

        channel_whitelists = eval(settings['channel_whitelists'])
        ch_wl = ", ".join([f"<#{ch}>" for ch in list(channel_whitelists.values())])
        role_whitelists = eval(settings['role_whitelists'])
        rl_wl = (", ".join([f"<@&{rl}>" for rl in list(role_whitelists.values())]))
        tba.append(f"**Channel whitelists: **{ch_wl}")
        tba.append(f"**Role whitelists: **{rl_wl}")

    return discord.Embed(title=setting_stuff[ind], description="\n".join(tba))



dbpass = 'mysecretpassword'


async def connections():
    global warn_conn
    warn_conn = await asyncpg.create_pool(host=d['host'], port=d['port'], user=d['user'],password=d['pwd'], database=d['db'])


def multi_settings_to_embed(settings, autotype, ind,table):
    embed = discord.Embed()
    if autotype == 'autopunish':
        embed.title = setting_stuff[ind]
        rules = [eval(rule) for rule in settings]
        for rule in rules:
            description = ""
            if rule['type'] in ['mute', 'tempban']:
                d = rule['duration']
                u = rule['durationType']
                description += f"**Action: ** {rule['type']} for {d} {u}\n"
            else:
                description += f"**Action: **{rule['type']}\n"
            description += f"**Threshold: **{rule['threshold']} warn points\n"
            embed.add_field(name=f"Rule #{rules.index(rule)+1}", value=description, inline=False)
    if autotype == 'autokb':
        embed.title = 'Auto kick/ban settings'
        types = {'accountAge': 'account age', 'status': 'blacklisted statuses', 'nsfwpfp': 'NSFW avatars','promoName': 'invite links in username/status', 'username': 'blacklisted usernames'}
        kick_description = ''
        ban_description = ''
        if "kickrules" in settings:
            if isinstance(settings['kickrules'], list):
                if len(settings['kickrules']) >= 1:
                    rules = [eval(rule) for rule in settings['kickrules']]
                    for rule in rules:
                        kick_description += f"**Rule #{rules.index(rule) + 1}**\n**Type: **{types[rule['type']]}\n"
                        if rule['type'] == 'status':
                            words = []
                            bl = rule['statuses']
                            kick_description += f"**Blacklisted statuses: **"
                            for word in bl:
                                if bl[word] == 'NoSubstring':
                                    words.append(word)
                                else:
                                    words.append(f"**{word}**")
                            kick_description += f" {', '.join(words)}"
                        if rule['type'] == 'username':
                            words = []
                            bl = rule['usernames']
                            kick_description += f"**Blacklisted usernames: **"
                            for word in bl:
                                if bl[word] == 'NoSubstring':
                                    words.append(word)
                                else:
                                    words.append(f"**{word}**")
                            kick_description += f" {', '.join(words)}"
                        if rule['type'] == 'accountAge':
                            t = rule['timeVal']
                            u = rule['timeUnit']
                            kick_description += f"**Mininum account age: **{t} {u}"
                        kick_description += '\n\n'
            else:
                kick_description += 'None set at the moment'
            embed.add_field(name="Kick rules", value=kick_description)

        if "banrules" in settings:
            if isinstance(settings['banrules'], list):
                if len(settings['banrules']) >= 1:
                    rules = [eval(rule) for rule in settings['banrules']]
                    for rule in rules:
                        ban_description += f"**Rule #{rules.index(rule) + 1}**\n**Type: **{types[rule['type']]}\n"
                        if rule['type'] == 'status':
                            words = []
                            bl = rule['statuses']
                            ban_description += f"**Blacklisted statuses: **"
                            for word in bl:
                                if bl[word] == 'NoSubstring':
                                    words.append(word)
                                else:
                                    words.append(f" **{word}**")
                            ban_description += f"{', '.join(words)}"
                        if rule['type'] == 'username':
                            words = []
                            bl = rule['usernames']
                            ban_description += f"**Blacklisted usernames: **"
                            for word in bl:
                                if bl[word] == 'NoSubstring':
                                    words.append(word)
                                else:
                                    words.append(f" **{word}**")
                            ban_description += f"{', '.join(words)}"
                        if rule['type'] == 'accountAge':
                            t = rule['timeVal']
                            u = rule['timeUnit']
                            ban_description += f"**Mininum account age: **{t} {u}"
                        ban_description += '\n\n'
            else:
                ban_description += 'None set at the moment'
            embed.add_field(name="Ban rules", value=ban_description)
            embed.set_footer(text="NOTE: blacklisted words in bold will be checked in substrings, meaning that if the word written as part of another word, the user will be punished. For example, if the word 'lol' was bold, having the word 'lollipop' will have you punished. Otherwise it won't have you punished.")
    if autotype == 'blacklist':
        embed.title = setting_stuff[ind]
        for category in settings:
            c = eval(category)
            pn = c['punishments']
            title = c['title']
            p = ', '.join(pn)
            d = str(c['timeval']) + ' ' + str(c['timeunit'])
            spec_p = ''
            if 'Warn' in pn:
                spec_p += f"**Points: **{c['points']}\n"
            if 'Mute' in pn:
                spec_p += f"**Mute duration: **{d}\n"
            if 'Tempban' in pn:
                spec_p += f"**Tempban duration: **{d}\n"
            words = c['words']
            w = []
            for word in words:
                if words[word] == 'Substring':
                    w.append(f"**{word}**")
                else:
                    w.append(word)
            wr_str = ', '.join(w)
            ch = ''
            if 'whitelistedChannels' in c:
                ids = list(c['whitelistedChannels'].values())
                channels = [f"<#{ch_id}>" for ch_id in ids]
                cha = ', '.join(channels)
                ch = f'**Whitelisted channels:** {cha}\n'

            rl_ids = list(c['whitelistedRoles'].values())
            roles = [f"<@&{rl_id}>" for rl_id in rl_ids]
            rla = ', '.join(roles)
            rl = f'**Whitelisted roles:** {rla}'
            desc = f'**Punishments:** {p}\n{spec_p}**{s[table]}:** {wr_str}\n{ch}{rl}'

            embed.add_field(name=f"Category '{title}'", value=desc)
            embed.set_footer(text="NOTE: blacklisted words in bold will be checked in substrings, meaning that if the word written as part of another word, the user will be punished. For example, if the word 'lol' was bold, the word 'lollipop' will have you punished. Otherwise it won't have you punished.")

    return embed


async def unwarn(bot, member, amount, channel, who):
    key = f"{member.guild.id}_{member.id}"
    info = await warn_conn.fetchrow('SELECT * FROM user_infraction_points WHERE memberkey=$1', key)
    if info is None:
        await channel.send('no points to remove!')
    else:
        user = dict(info)['points']
        if user == 0:
            await channel.send('no points to remove!')
        elif user - amount < 0:
            await warn_conn.execute('UPDATE user_infraction_points SET memberkey=$1, points=$2 where memberkey=$1', key, 0)
            await log_unwarn(bot, member, amount, 0, who)
            await channel.send(f"<:check:1009915788762812487> **{member}** has been unwarned")

        elif amount == 0:
            await warn_conn.execute('UPDATE user_infraction_points SET memberkey=$1, points=$2 where memberkey=$1', key,
                                    0)
            await log_unwarn(bot, member, user, 0, who)
            await channel.send(f"<:check:1009915788762812487> **{member}** has been unwarned")

        else:
            await warn_conn.execute('UPDATE user_infraction_points SET memberkey=$1, points=$2 where memberkey=$1', key, user - amount)
            await log_unwarn(bot, member, amount, user - amount, who)
            await channel.send(f"<:check:1009915788762812487> **{member}** has been unwarned")


async def log_unwarn(bot, member, amount, new, who):
    guild = member.guild
    if new != 0:
        await handle_send(member, embed=discord.Embed(title='Someone removed some of your infraction points!', description=f"**Points removed:** {amount}\n**Removed by:** {who}", color=0x08bf1d))
        settings = await warn_conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            mod_channel = dict(settings)['moderation_channel']
            actions = dict(settings)['moderations']
            if isinstance(mod_channel, int) and 'Infraction Removed' in actions:
                embed = discord.Embed(title="Infraction points removed",description=f"**Points removed:** {amount}\n**Current points:** {new}\n**Moderator: ** {who}", color=0x68f286)
                url = ''
                if str(member.avatar) != 'None':
                    url += str(member.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(member), icon_url=url)
                embed.set_footer(text=f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                await bot.get_channel(mod_channel).send(embed=embed)
    else:
        await handle_send(member, embed=discord.Embed(title='Someone removed all of your infraction points!',
                                                      description=f"**Points removed:** {amount}\n**Removed by:** {who}", color=0x33f25c))
        settings = await warn_conn.fetchrow('SELECT * FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            mod_channel = dict(settings)['moderation_channel']
            actions = dict(settings)['moderations']
            if isinstance(mod_channel, int) and 'Infraction Removed' in actions:
                embed = discord.Embed(title="Infraction points removed",
                                      description=f"**Points removed:** {amount}\n**Current points:** {new}\n**Moderator: ** {who} ({who.mention})", color=0x68f286)
                url = ''
                if str(member.avatar) != 'None':
                    url += str(member.avatar)
                else:
                    url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
                embed.set_author(name=str(member), icon_url=url)
                embed.set_footer(text=f"Member ID: {member.id} · {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                await bot.get_channel(mod_channel).send(embed=embed)

    await log_infraction(member, member.guild, {"type": "Unwarn", "Points removed": amount, "Moderator": str(who)}, warn_conn)


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


def divide_array(nums, k):
    ans = []
    temp = []
    for i in range(0, len(nums)):
        temp.append(nums[i])
        if ((i + 1) % k) == 0:
            ans.append(temp.copy())
            temp.clear()

    if len(temp) != 0:
        ans.append(temp)

    return ans


async def get_infractions(guild, user):
    url = ''
    if str(user.avatar) != 'None':
        url += str(user.avatar)
    else:
        url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
    non_infraction_embed = discord.Embed(title=f'Infractions for {user}', description='This user has no infractions.', color=0x00ff00)
    non_infraction_embed.set_author(name=str(user), icon_url=url)
    info = await warn_conn.fetchrow('select infractions from infractions where guild_id=$1 and member_id=$2', guild.id, user.id)
    if info is not None:
        infractions = [eval(infraction.replace('null', 'None')) for infraction in dict(info)['infractions']]
        if len(infractions) == 0:
            return [non_infraction_embed]
        else:
            embeds = []
            divided = divide_array(infractions, 10)
            pages = len(infractions)//10 + 1
            if len(infractions)%10 == 0:
                pages -= 1

            for i in range(pages):
                e = discord.Embed(color=0xff0000, title=f'Infractions for {user}', description=f'Total infractions: {len(infractions)}')
                for inf in divided[i]:
                    desc = []
                    for k in [key for key in list(inf.keys()) if key != 'type']:
                        desc.append(f"**{k}:** {inf[k]}")
                    e.add_field(name=inf['type'], value='\n'.join(desc), inline=False)
                e.set_author(name=str(user), icon_url=url)
                e.set_footer(text=f"Page {i+1}/{pages}")
                embeds.append(e)
            return embeds
    else:
        return [non_infraction_embed]


def most_similar(word, words):
    ws = {}
    for w in words:
        ws[w] = sm(None, word, w).ratio()
    return [W for W in words if ws[W] == max(list(ws.values()))][0]


def two_weeks(msg):
    return (datetime.datetime.now(tz=datetime.timezone.utc) - msg.created_at).total_seconds() <= 1209600 and not \
        re.match('.*purge \d*\s*', msg.content)


class Punishing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command()
    @commands.has_permissions(kick_members=True, ban_members=True)
    async def warn(self, ctx, member: discord.Member, amount: int, reason=None):
        await handle_send(member, embed=discord.Embed(title=f"You've been warned in {member.guild}",
                                                      description=f"**Points added:** {amount}\n**Reason:** {reason}\n**Moderator: ** {ctx.author}", color=0xf54254))
        await ctx.send(f"<:check:1009915788762812487> **{member}** has been warned.")
        await warn(self.bot, member, member.guild, amount, warn_conn, reason, ctx.author)


    @warn.error
    async def handle_warn_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
            await ctx.send(f'<:xmark:1009919995297415190> Argument `{error.param.name}` is missing.')
        if isinstance(error, discord.ext.commands.errors.MemberNotFound):
            await ctx.send(f'<:xmark:1009919995297415190> Member not found. Check someone else.')
        if isinstance(error, discord.ext.commands.errors.BadArgument):
            await ctx.send(f"<:xmark:1009919995297415190> Invalid value for parameter `amount`")
        if isinstance(error, discord.ext.commands.errors.MissingPermissions):
            await ctx.send(f"<:xmark:1009919995297415190> You don't have permissions to run this command: requires `kick_members` and `ban_members`.")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        if amount > 500:
            await ctx.send('Too many messages.')
        else:
            msgs = await ctx.channel.purge(limit=amount, bulk=True, check=two_weeks)
            if len(msgs) == 0:
                await ctx.send('No messages were purged, as none under two weeks old were found.')
            else:
                await ctx.send(f"<:check:1009915788762812487> purged {len(msgs)} messages.")


    @purge.error
    async def purge_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
            await ctx.send(f'<:xmark:1009919995297415190> Argument `{error.param.name}` is missing.')
        if isinstance(error, discord.ext.commands.errors.BadArgument):
            await ctx.send(f"<:xmark:1009919995297415190> Invalid value for parameter `amount`.")
        if isinstance(error, discord.ext.commands.errors.MissingPermissions):
            await ctx.send(f"<:xmark:1009919995297415190> You don't have permissions to run this command: requires `manage_messages`.)")


    @commands.command()
    @commands.has_permissions(kick_members=True, ban_members=True)
    async def unwarn(self, ctx, member: discord.Member, amount: int):
        await unwarn(self.bot, member, amount, ctx.channel, ctx.author)

    @unwarn.error
    async def handle_unwarn_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
            await ctx.send(f'<:xmark:1009919995297415190> Argument `{error.param.name}` is missing.')
        if isinstance(error, discord.ext.commands.errors.MemberNotFound):
            await ctx.send(f'<:xmark:1009919995297415190> Member not found. Check someone else.')
        if isinstance(error, discord.ext.commands.errors.BadArgument):
            await ctx.send(f"<:xmark:1009919995297415190> Invalid value for parameter `amount.")
        if isinstance(error, discord.ext.commands.errors.MissingPermissions):
            await ctx.send(f"<:xmark:1009919995297415190> You don't have permissions to run this command: requires `kick_members` and `ban_members`.")

    @commands.command()
    async def warns(self, ctx, *, member: discord.Member = None):
        info = await warn_conn.fetchrow('SELECT * FROM user_infraction_points WHERE memberkey=$1', f"{ctx.guild.id}_{member.id}")
        if info is None:
            await ctx.send(f'**{member}** has 0 points')
        else:
            if member.id != ctx.author.id:
                p = dict(info)['points']
                await ctx.send(f"**{member}** has {p} points")
            elif member.id == ctx.author.id:
                p = dict(info)['points']
                await ctx.send(f"you have {p} points")

    @warns.error
    async def sendWho(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.CommandInvokeError):
            info = await warn_conn.fetchrow('SELECT * FROM user_infraction_points WHERE memberkey=$1',f"{ctx.guild.id}_{ctx.author.id}")
            if info is None:
                await ctx.send('you have 0 points')
            else:
                await ctx.send(f"you have {dict(info)['points']} points")
        if isinstance(error, discord.ext.commands.errors.MemberNotFound):
            await ctx.send('<:xmark:1009919995297415190> Member not found. Check someone else.')

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: int, *, reason=None):
        await member.timeout(
            until=datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=duration))
        await ctx.send(f"<:check:1009915788762812487> **{member}** has been muted")
        await log_mute(self.bot, member.guild, member, t(duration), f"{reason} (action requested by {ctx.author} ({ctx.author.mention}))", ctx.author, warn_conn)
        await handle_send(member, embed=discord.Embed(title=f"You've been muted in {ctx.guild}",
                                              description=f"**Duration:** {t(duration)}\n**Reason:** {reason}\n**Moderator: ** {ctx.author}", color=0xf54254))


    @mute.error
    async def handle_mute_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
            await ctx.send(f'<:xmark:1009919995297415190> Argument `{error.param.name}` is missing.')
        if isinstance(error, discord.ext.commands.errors.MemberNotFound):
            await ctx.send(f'<:xmark:1009919995297415190> Member not found. Check someone else.')
        if isinstance(error, discord.ext.commands.errors.BadArgument):
            await ctx.send(f"<:xmark:1009919995297415190> Invalid value for parameter `duration`.")
        if isinstance(error, discord.ext.commands.errors.MissingPermissions):
            await ctx.send(f"<:xmark:1009919995297415190> You don't have permissions to run this command: requires `moderate_members`.")
        if str(error) == "Command raised an exception: Forbidden: 403 Forbidden (error code: 50013): Missing Permissions":
            await ctx.send("<:xmark:1009919995297415190> I don't have permissions to mute this member.")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        await handle_send(member,
                          embed=discord.Embed(title=f"You've been kicked from {member.guild}",
                                              description=f"**Reason:** {reason}\n**Moderator: ** {ctx.author}", color=0xf54254))
        await member.kick(reason=f"{reason} (action requested by {ctx.author} ({ctx.author.mention}))")
        await ctx.send(f"<:check:1009915788762812487> **{member}** has been kicked")



    @kick.error
    async def handle_kick_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
            await ctx.send(f'<:xmark:1009919995297415190> Argument `{error.param.name}` is missing.')
        if isinstance(error, discord.ext.commands.errors.MemberNotFound):
            await ctx.send(f'<:xmark:1009919995297415190> Member not found. Check someone else.')
        if isinstance(error, discord.ext.commands.errors.MissingPermissions):
            await ctx.send(f"<:xmark:1009919995297415190> You don't have permissions to run this command: requires `kick_members`.")
        if str(error) == "Command raised an exception: Forbidden: 403 Forbidden (error code: 50013): Missing Permissions":
            await ctx.send("<:xmark:1009919995297415190> I don't have permissions to kick this member.")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def tempban(self, ctx, member: discord.Member, duration: int, *, reason=None):
        await handle_send(member, embed=discord.Embed(title=f"You've been temporarily banned from {member.guild}",
                                                      description=f"**Duration: **{t(duration)}\n**Reason:** {reason}\n**Moderator: ** {ctx.author}", color=0xf54254))
        await member.ban(reason=reason, delete_message_days=0)
        await ctx.send(f"<:check:1009915788762812487> **{member}** has been tempbanned")

        await log_tempban(self.bot, member.guild, member, t(duration), f"{reason} (action requested by {ctx.author} ({ctx.author.mention}))", ctx.author, warn_conn)


        await asyncio.sleep(duration)
        await member.unban()

    @tempban.error
    async def handle_tempban_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
            await ctx.send(f'<:xmark:1009919995297415190> Argument `{error.param.name}` is missing.')
        if isinstance(error, discord.ext.commands.errors.MemberNotFound):
            await ctx.send(f'<:xmark:1009919995297415190> Member not found. Check someone else.')
        if isinstance(error, discord.ext.commands.errors.BadArgument):
            await ctx.send(f"<:xmark:1009919995297415190> Invalid value for parameter `duration`.")
        if isinstance(error, discord.ext.commands.errors.MissingPermissions):
            await ctx.send(f"<:xmark:1009919995297415190> You don't have permissions to run this command: requires `ban_members`.")
        if str(error) == "Command raised an exception: Forbidden: 403 Forbidden (error code: 50013): Missing Permissions":
            await ctx.send("<:xmark:1009919995297415190> I don't have permissions to ban this member.")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        await handle_send(member,
                          embed=discord.Embed(title=f"You've been banned from {member.guild}",
                                              description=f"**Reason:** {reason}\n**Moderator: ** {ctx.author}", color=0xf54254))
        await member.ban(reason=reason, delete_message_days=0)
        await ctx.send(f"<:check:1009915788762812487> **{member}** has been banned")
        await log_ban(self.bot, ctx.guild, member, f"{reason} (action requested by {ctx.author} ({ctx.author.mention}))", ctx.author, warn_conn)


    @ban.error
    async def handle_ban_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
            await ctx.send(f'<:xmark:1009919995297415190> Argument `{error.param.name}` is missing.')
        if isinstance(error, discord.ext.commands.errors.MemberNotFound):
            await ctx.send(f'<:xmark:1009919995297415190> Member not found. Check someone else.')
        if isinstance(error, discord.ext.commands.errors.MissingPermissions):
            await ctx.send(f"<:xmark:1009919995297415190> You don't have permissions to run this command: requires `ban_member`.")
        if str(error) == "Command raised an exception: Forbidden: 403 Forbidden (error code: 50013): Missing Permissions":
            await ctx.send("<:xmark:1009919995297415190> I don't have permissions to ban this member.")
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        await member.timeout(until=None)
        await ctx.send(f"<:check:1009915788762812487> **{member}** has been unmuted")
        await log_unmute(self.bot, member.guild, member, warn_conn, ctx.author)
        await handle_send(member, embed=discord.Embed(title=f"You've been unmuted in {ctx.guild}",
                                             description=f"**Moderator: **{ctx.author}", color=0x33f25c))

    @unmute.error
    async def handle_unmute_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
            await ctx.send(f'<:xmark:1009919995297415190> Argument `{error.param.name}` is missing.')
        if isinstance(error, discord.ext.commands.errors.MemberNotFound):
            await ctx.send(f'<:xmark:1009919995297415190> Member not found. Check someone else.')
        if isinstance(error, discord.ext.commands.errors.MissingPermissions):
            await ctx.send(f"<:xmark:1009919995297415190> You don't have permissions to run this command: requires `moderate_members`.")
        if str(error) == "Command raised an exception: Forbidden: 403 Forbidden (error code: 50013): Missing Permissions":
            await ctx.send("<:xmark:1009919995297415190> I don't have permissions to unmute this member.")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, member: discord.User):
        bans = await ctx.guild.bans().flatten()
        for ban in bans:
            if ban.user.id == member.id:
                await ctx.guild.unban(ban.user)
        await ctx.send(f"<:check:1009915788762812487> **{member}** has been unbanned.")


    @unban.error
    @commands.has_permissions(ban_members=True)
    async def handle_unban_error(self, ctx, error):
        print(error)
        if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
            await ctx.send(f'<:xmark:1009919995297415190> Argument `{error.param.name}` is missing.')
        if isinstance(error, discord.ext.commands.errors.MemberNotFound):
            await ctx.send(f'<:xmark:1009919995297415190> Member not found. Check someone else.')
        if isinstance(error, discord.ext.commands.errors.MissingPermissions):
            await ctx.send(f"<:xmark:1009919995297415190> You don't have permissions to run this command: requires `ban_members`.")
        if str(error) == "Command raised an exception: Forbidden: 403 Forbidden (error code: 50013): Missing Permissions":
            await ctx.send("<:xmark:1009919995297415190> I don't have permissions to unban this member.")
    @commands.command()
    async def prefix(self, ctx):
        prefix = await warn_conn.execute('SELECT * FROM bot_settings WHERE guild_id=$1', ctx.guild.id)
        if prefix is not None:
            await ctx.send(
                f"The current prefix is `{dict(prefix)['bot_prefix']}`")
        else:
            await ctx.send(f"The current prefix is `a!`")

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def changeprefix(self, ctx, newprefix):
        info = await warn_conn.fetchrow('SELECT * FROM bot_settings where guild_id=$1', ctx.guild.id)
        if info is None:
            await warn_conn.execute('INSERT INTO bot_settings (guild_id, bot_name, bot_prefix) VALUES ($1, $2, $3)',
                                     ctx.guild.id, f"{self.bot.user.name}", newprefix)
        else:
            await warn_conn.execute('UPDATE bot_settings SET bot_prefix=$1 WHERE guild_id=$2', newprefix, ctx.guild.id)
        await ctx.send(f'<:check:1009915788762812487> Changed the prefix to `{newprefix}`')


    @changeprefix.error
    async def chp_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
            await ctx.send(f'<:xmark:1009919995297415190> Argument `{error.param.name}` is missing.')
        if isinstance(error, discord.ext.commands.errors.MissingPermissions):
            await ctx.send(f"<:xmark:1009919995297415190> You don't have permissions to run this command: requires `manage_guild`.")

    


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command()
    async def amsettings(self, ctx, table=None):
        if table is None:
            await ctx.send('which table do you want to check? available are `modlogs`, `messagespam`, `emojispam`, `mentionspam`, `stickerspam`, `attachmentspam`, `linkspam`, `duplicatecharacters`, `duplicatemessages`, `linebreaks`, `toomanycaps`, `invites`, `selfbot`, `nsfwcontent`, `hatespeech`, `badwords`, `badlinks`, `badnicks`, `badnames`, `badstatuses`, `nsfwpfp`, `autopunish`, `autokickban`, `automodgeneral`')
        elif table not in tables:
            await ctx.send(f'table not found. did you mean `{most_similar(table, tables)}`?')
        else:
            settings = await warn_conn.fetchrow(f"SELECT * FROM {table} WHERE guild_id=$1", ctx.guild.id)
            if settings is None:
                if table in ['messagespam', 'emojispam', 'mentionspam', 'stickerspam', 'attachmentspam', 'linkspam']:
                    await ctx.send(embed=settings_to_embed(default_settings[table], 'spam',
                                                           tables.index(table)))
                elif table in ['duplicatecharacters', 'duplicatemessages', 'linebreaks', 'toomanycaps']:
                    await ctx.send(
                        embed=settings_to_embed(default_settings[table], 'toomuch',
                                                tables.index(table)))
                elif table in ['invites', 'hatespeech', 'selfbot', 'nsfwcontent', 'nsfwpfp']:
                    await ctx.send(
                        embed=settings_to_embed(default_settings[table], 'unacceptable',
                                                tables.index(table)))
                elif table in ['badnicks', 'badlinks', 'badnames', 'badwords', 'badstatuses']:
                    await ctx.send(
                        embed=multi_settings_to_embed(default_settings[table],
                                                      'blacklist',
                                                      tables.index(table), table))
                elif table == 'automodgeneral':
                    await ctx.send(embed=settings_to_embed({'channel_whitelists': str({}), 'role_whitelists': str({})} ,'general', len(setting_stuff)-1))
                elif table == 'modlogs':
                    await ctx.send(embed=settings_to_embed(default_modlogs, 'modlogs',tables.index(table)))
                elif table == 'autopunish':
                    await ctx.send(
                        embed=multi_settings_to_embed(default_autopunish, 'autokb', tables.index(table), 't'))
                elif table == 'autokickban':
                    await ctx.send(
                        embed=multi_settings_to_embed(default_autokb, 'autokb', tables.index(table), 't'))
            else:
                if table in ['messagespam','emojispam', 'mentionspam', 'stickerspam','attachmentspam','linkspam']:
                    await ctx.send(embed=settings_to_embed(dict(settings), 'spam', tables.index(table)))
                elif table in ['duplicatecharacters','duplicatemessages','linebreaks','toomanycaps']:
                    await ctx.send(
                        embed=settings_to_embed(dict(settings), 'toomuch', tables.index(table)))
                elif table in ['invites', 'hatespeech','selfbot','nsfwcontent','nsfwpfp']:
                    await ctx.send(
                        embed=settings_to_embed(dict(settings), 'unacceptable',
                                                tables.index(table)))
                elif table == 'modlogs':
                    await ctx.send(
                        embed=settings_to_embed(dict(settings), 'modlogs', tables.index(table)))
                elif table == 'autopunish':
                    await ctx.send(embed=multi_settings_to_embed(dict(settings)['rules'], 'autopunish',tables.index(table), 't'))
                elif table == 'autokickban':
                    await ctx.send(embed=multi_settings_to_embed(dict(settings), 'autokb', tables.index(table), 't'))
                elif table in ['badnicks', 'badlinks', 'badnames', 'badwords', 'badstatuses']:
                    await ctx.send(embed=multi_settings_to_embed(dict(settings)['categories'], 'blacklist',
                                                                 tables.index(table), table))
                elif table == 'automodgeneral':
                    await ctx.send(embed=settings_to_embed(dict(settings), 'general',
                                                           len(setting_stuff) - 1))

    @commands.command()
    async def infractions(self, ctx, member:discord.Member = None, page: int = 1):
        if member == None:
            await ctx.send(embed=(await get_infractions(ctx.guild, ctx.author))[page - 1])
        else:
            await ctx.send(embed=(await get_infractions(ctx.guild, member))[page - 1])



    @infractions.error
    async def inf_err(self, ctx, error):
        if isinstance(error, discord.ext.commands.errors.MemberNotFound):
            await ctx.send('member not found. check someone else')



def setup(bot):
    bot.add_cog(Punishing(bot))
    bot.add_cog(Settings(bot))


asyncio.get_event_loop().run_until_complete(connections())