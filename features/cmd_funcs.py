import discord
from discord.ext import commands
import asyncio
import datetime
from datetime import timezone
from features.punishing import warn, log_mute, log_unmute, log_tempban, log_ban, log_infraction, tempban
import aiohttp

tables = ['modlogs', 'messagespam', 'emojispam', 'mentionspam', 'stickerspam', 'attachmentspam', 'linkspam',
          'duplicatecharacters', 'duplicatemessages', 'linebreaks', 'toomanycaps', 'invites', 'selfbot', 'nsfwcontent',
          'hatespeech', 'badwords', 'badlinks', 'badnicks', 'badnames', 'badstatuses', 'nsfwpfp', 'autopunish',
          'autokickban', 'automodgeneral']
setting_stuff = ["Modlog settings", "Message spam settings", "Emoji spam settings", "Mention spam settings",
                 "Sticker spam settings", "Attachment spam settings", "Link spam settings",
                 "Duplicate character settings", "Duplicate message settings", "Line break settings",
                 "Capitals settings", "Invite settings", "Selfbot settings", "NSFW content settings",
                 "Hate speech settings", 'Bad word settings', 'Bad link settings', 'Bad nickname settings',
                 'Bad username settings', 'Bad custom status settings', 'NSFW avatar settings', 'Autopunish settings',
                 ' Auto kick/ban settings', 'Whitelist settings']
table_dict = {'Action logging': 'modlogs', 'Message spam': 'messagespam', 'Emoji spam': 'emojispam',
              'Mention spam': 'mentionspam', 'Sticker spam': 'stickerspam', 'Attachment spam': 'attachmentspam',
              'Link spam': 'linkspam', 'Duplicate characters': 'duplicatecharacters',
              'Duplicate messages': 'duplicatemessages', 'Line breaks': 'linebreaks', 'Capitals': 'toomanycaps',
              'Invites': 'invites', 'Selfbotting': 'selfbot', 'NSFW content': 'nsfwcontent',
              'Hate speech': 'hatespeech', 'Bad words': 'badwords', 'Bad links': 'badlinks',
              'Bad nicknames': 'badnicks', 'Bad usernames': 'badnames', 'Bad custom statuses': 'badstatuses',
              'NSFW avatars': 'nsfwpfp', 'Autopunish': 'autopunish', ' Auto kick/ban': 'autokickban',
              'General settings': 'automodgeneral'}

s = {'badlinks': 'Blacklisted links', 'badwords': 'Blacklisted words', 'badnicks': 'Blacklisted nicknames',
     'badnames': 'Blacklisted usernames', 'badstatuses': 'Blacklisted custom statuses'}
overusing_types = {'duplicatemessages': 'repeated messages', 'linebreaks': 'line breaks', 'toomanycaps': '% caps',
                   'duplicate characters': 'repeated character(s)'}
msg_tables = ['automodgeneral', 'messagespam', 'emojispam', 'mentionspam', 'stickerspam', 'attachmentspam', 'linkspam',
              'duplicatecharacters', 'duplicatemessages', 'linebreaks', 'toomanycaps', 'invites', 'selfbot',
              'nsfwcontent', 'hatespeech', 'badwords', 'badlinks', 'badnicks', 'badnames', 'badstatuses']
bad_profile = [
    str({'title': 'triggering (substring)', 'punishments': ['Ban'], 'points': 0, 'timeval': 0, 'timeunit': 'minutes',
         'whitelistedRoles': {}, 'whitelistedChannels': {}, 'duration': 0,
         'words': ['hitler', 'nazi', 'adolf', 'holocaust', 'auschwitz', 'rapist', 'porn', 'molest', 'pedo', 'paedo'],
         'substring': 1}),
    str({'title': 'triggering (no substring)', 'punishments': ['Ban'], 'points': 0, 'timeval': 0, 'timeunit': 'minutes',
         'whitelistedRoles': {}, 'whitelistedChannels': {}, 'duration': 0, 'words': ['rape', 'raping', 'sex'],
         'substring': 0}),
    str({'title': 'slurs (substring)', 'punishments': ['Warn', 'Tempban'], 'points': 20, 'timeval': 3,
         'timeunit': 'days',
         'whitelistedRoles': {}, 'whitelistedChannels': {}, 'duration': 0,
         'words': ['nigger', 'fag', 'tranny', 'trannies', 'chingchong', 'ching chang'], 'substring': 1})]
default_settings = {
    'messagespam': {"punishments": [], "maxes": [5, 2], "channel_whitelists": {}, "role_whitelists": {},
                    "points": 5, "timeval": 40, "timeunit": "minutes"},
    'emojispam': {"punishments": [], "maxes": [5, 2], "channel_whitelists": {}, "role_whitelists": {}, "points": 0,
                  "timeval": 20, "timeunit": "minutes"},
    'mentionspam': {"punishments": ["Delete message", "Mute", "Warn"], "maxes": [8, 2], "channel_whitelists": {},
                    "role_whitelists": {}, "points": 6, "timeval": 3, "timeunit": "hours"},
    'stickerspam': {"punishments": [], "maxes": [5, 2], "channel_whitelists": {}, "role_whitelists": {},
                    "points": 0, "timeval": 2, "timeunit": "hours"},
    'attachmentspam': {"punishments": [], "maxes": [5, 2], "channel_whitelists": {}, "role_whitelists": {},
                       "points": 5, "timeval": 3, "timeunit": "hours"},
    'linkspam': {"punishments": [], "maxes": [6, 2], "channel_whitelists": {}, "role_whitelists": {}, "points": 0,
                 "timeval": 2, "timeunit": "hours"},
    'linebreaks': {"punishments": [], "top": 15, "points": 0, "timeunit": "minutes", "timeval": 30,
                   "channel_whitelists": {}, "role_whitelists": {}},
    'toomanycaps': {"punishments": [], "top": 99, "points": 5, "timeunit": "minutes", "timeval": 45,
                    "channel_whitelists": {}, "role_whitelists": {}},
    'duplicatemessages': {"punishments": [], "top": 5, "points": 4, "timeunit": "hours", "timeval": 2,
                          "channel_whitelists": {}, "role_whitelists": {}},
    'duplicatecharacters': {"punishments": [], "top": 30, "points": 5, "timeunit": "minutes", "timeval": 45,
                            "channel_whitelists": {}, "role_whitelists": {}},
    'invites': {"punishments": [], "points": 5, "timeunit": "minutes", "timeval": 0, "channel_whitelists": {},
                "role_whitelists": {}},
    'selfbot': {"punishments": ["Delete message", "Ban"], "points": 0, "timeunit": "minutes", "timeval": 0,
                "role_whitelists": {}},
    'badwords': {'categories': [{"title": "slurs", "punishments": ["Delete message", "Warn"],
                                 "words": ['chingchong', 'ching chang', 'nigger', 'trannies', 'tranny', 'fag'],
                                 "points": 20,
                                 "timeval": 0, "timeunit": "minutes", "whitelistedRoles": {}, "whitelistedChannels": {},
                                 "duration": 0, 'substring': 1}]},
    'badlinks': {'categories': [{"title": "nsfw", "punishments": ["Delete message", "Ban"],
                                 "words": ['pornhub', 'xvideos', 'spankbang', 'xnxx', 'xhamster', 'chaturbate',
                                           'youporn',
                                           'tnaflix', 'nuvid', 'drtuber', 'xxxbunker', 'xxxvideo', 'fapvidhd',
                                           'xxxvideos247',
                                           'pornhd', 'redtube', 'fapster', 'tastyblacks', 'hclips', 'tube8'],
                                 "points": 0,
                                 "timeval": 0, "timeunit": "minutes", "whitelistedRoles": {}, "whitelistedChannels": {},
                                 "duration": 0, 'substring': 1},
                                {"title": "gory", "punishments": ["Delete message", "Ban"],
                                 "words": ['bestgore', 'theync', 'kaotic', 'goregrish', 'crazyshit', 'efukt',
                                           'runthegauntlet',
                                           'ogrishforum'], "points": 0, "timeval": 0, "timeunit": "minutes",
                                 "whitelistedRoles": {}, "whitelistedChannels": {}, "duration": 0, 'substring': 1}]},
    'badnicks': bad_profile,
    'badnames': bad_profile,
    'badstatuses': bad_profile,
    'nsfwpfp': {"punishments": ["Ban"], "points": 0, "timeunit": "minutes", "timeval": 0, "role_whitelists": {}},
    'automodgeneral': {'channel_whitelists': {}, 'role_whitelists': {}}
}

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

bad_profiles_sub = ['hitler', 'nazi', 'adolf', 'holocaust', 'auschwitz', 'rapist', 'porn', 'molest', 'traffick', 'pedo',
                    'paedo']
bad_profiles_nosub = ['rape', 'raping', 'sex']

default_modlogs = {'message_channel': '', 'member_channel': '', 'moderation_channel': '', 'server_channel': '',
                   'voicestate_channel': '',
                   'message_actions': ['Message Deleted', 'Message Edited', 'Message Bulk Deletion'],
                   'member_actions': ['Username Changed', 'Avatar Changed', 'Custom Status Changed', 'Member Joined',
                                      'Roles Changed', 'Nickname Changed', 'Member Left'],
                   'moderations': ['Member Warned', 'Member Kicked', 'Infraction Removed', 'Member Tempbanned',
                                   'Member Muted', 'Member Unbanned', 'Member Unmuted', 'Member Banned'],
                   'server_actions': ['Emoji Added', 'Emoji Updated', 'Emoji Deleted', 'Channel Deleted',
                                      'Channel Updated', 'Channel Created', 'Role Created', 'Role Updated',
                                      'Role Deleted', 'Server Icon Changed', 'Discovery Splash Changed',
                                      'Server Name Changed', 'AFK Channel Changed', 'System Channel Changed',
                                      'Default Notifications Changed', 'Bot Removed', 'Bot Added',
                                      'AFK Timeout Changed', 'Invite Splash Changed', 'Banner Changed',
                                      'Explicit Filter Changed', 'Invite Deleted', 'Invite Created',
                                      'Server Owner Changed', 'MFA Changed', 'Verification Level Changed'],
                   'vc_actions': ['Member Joined VC', 'Member Left VC', 'Member Moved']}
default_autopunish = [{'type': "mute", "durationType": "hours", "duration": 6, "threshold": 15},
                      {'type': "kick", "durationType": "minutes", "duration": 1, "threshold": 30},
                      {'type': "tempban", "durationType": "days", "duration": 3, "threshold": 45},
                      {'type': "ban", "durationType": "minutes", "duration": 1, "threshold": 60}]
default_autokb = {
    'banrules': [str({"type": "username", "timeVal": 24, "timeUnit": "hours", "usernames": bad_profiles_sub,
                      "statuses": [], 'substring': 1}),
                 str({"type": "username", "timeVal": 24, "timeUnit": "hours", "usernames": bad_profiles_nosub,
                      "statuses": [], 'substring': 0}),
                 str({"type": "status", "timeVal": 24, "timeUnit": "hours", "usernames": [],
                      "statuses": bad_profiles_sub, 'substring': 1}),
                 str({"type": "status", "timeVal": 24, "timeUnit": "hours", "usernames": [],
                      "statuses": bad_profiles_nosub, 'substring': 0})], 'kickrules': []}

webhook_pfp = "https://cdn.discordapp.com/attachments/1274041694018469980/1356831963679293481/MndBTSfgkAAAAASUVORK5CYII.png?ex=67edffbc&is=67ecae3c&hm=22564715d61ff337cce22605cfed5a817e79930a8efac9538aa0af153042cfad&"


d = {}
me = 825455379424739388
with open('tk.json', 'r+') as f:
    info = eval(f.read())['db']
    for key in list(info.keys()):
        d[key] = info[key]


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


async def has_permissions(b, member, permission):
    guild = member.guild
    bot_perms = dict(list(b.guild_permissions))
    if bot_perms[permission] and not guild.owner_id == member.id and member.top_role.position < b.top_role.position:
        return True
    return False


def int_to_yesno(n):
    if n > 0:
        return 'Yes'
    return 'No'


async def handle_send(member, embed):
    try:
        await member.send(embed=embed)
    except:
        pass


def embed_len(embed):
    total = sum([len(f.name) for f in embed.fields]) + sum([len(f.value) for f in embed.fields])
    if embed.title is not None:
        total += len(embed.title)
    if embed.description is not None:
        total += len(embed.description)
    if embed.footer is not None:
        total += len(embed.footer)
    if embed.author is not None:
        total += len(embed.author.name)
    return total


def split_embed(embed, autotype, bl_type):
    embeds = []

    if autotype == 'autokb':
        sections = embed.description.split("\n\n\n\n")
        kick_section, ban_section = sections[0].split("\n\n"), sections[1].split("\n\n")
        all_parts = kick_section + ban_section

        cur_section = {"section": ""}
        while len(all_parts) > 0:
            if len(cur_section["section"]) + len(all_parts[0]) <= 4096:
                if len(all_parts) > 1:
                    if "None set at the moment" not in all_parts[0] and "BAN RULES" in all_parts[1]:
                        cur_section["section"] += all_parts[0] + "\n"
                    elif "None set at the moment" in cur_section["section"] and "BAN RULES" in all_parts[0]:
                        cur_section["section"] += "\n" + all_parts[0] + "\n\n"
                    else:
                        cur_section["section"] += all_parts[0] + "\n\n"
                else:
                    cur_section["section"] += all_parts[0] + "\n\n"
                all_parts = all_parts[1:]
                if len(all_parts) == 0:
                    embeds.append(discord.Embed(title="Auto kick/ban settings" if len(embeds) == 0 else "",
                                                description=cur_section["section"].strip(), color=0x5797f7))
                    cur_section["section"] = ""
            else:
                embeds.append(discord.Embed(title="Auto kick/ban settings" if len(embeds) == 0 else "",
                                            description=cur_section["section"].strip(), color=0x5797f7))
                cur_section["section"] = ""
        return embeds

    if autotype == 'blacklist':
        sections = embed.description.split("\n\n")
        cur_section = {"section": ""}
        while len(sections) > 0:
            if len(cur_section["section"]) + len(sections[0]) <= 4096:
                cur_section["section"] += sections[0] + "\n\n"
                sections = sections[1:]
                if len(sections) == 0:
                    embeds.append(discord.Embed(title=bl_type if len(embeds) == 0 else "",
                                                description=cur_section["section"].strip(), color=0x5797f7))
                    cur_section["section"] = ""
            else:
                embeds.append(discord.Embed(title=bl_type if len(embeds) == 0 else "",
                                            description=cur_section["section"].strip(), color=0x5797f7))
                cur_section["section"] = ""
        return embeds


async def settings_to_embed(settings, autotype, ind):
    tba = []
    if autotype == 'spam':
        punishments = settings['punishments']
        m = 'maxes'
        p = settings['points']
        timeval = settings['timeval']
        unit = settings['timeunit']
        tba.append(f"**Punishments: **{', '.join(punishments)}")
        tba.append(f"**Maxes: **{settings[m][0]} in {settings[m][1]} seconds")
        if 'Warn' in punishments:
            tba.append(f'**Warn points: **{p}')
        if 'Mute' in punishments and timeval not in [0, 1, None]:
            tba.append(f"**Mute duration: **{timeval} {unit}")
        if 'Tempban' in punishments and timeval not in [0, 1, None]:
            tba.append(f"**Tempban duration: **{timeval} {unit}")
        channel_whitelists = settings['channel_whitelists']
        ch_wl = ", ".join([f"<#{ch}>" for ch in list(channel_whitelists.values())])
        role_whitelists = settings['role_whitelists']
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
        channel_whitelists = settings['channel_whitelists']
        ch_wl = ", ".join([f"<#{ch}>" for ch in list(channel_whitelists.values())])
        role_whitelists = settings['role_whitelists']
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
            channel_whitelists = settings['channel_whitelists']
            ch_wl = ", ".join([f"<#{ch}>" for ch in list(channel_whitelists.values())])
            role_whitelists = settings['channel_whitelists']
            rl_wl = (", ".join([f"<@&{rl}>" for rl in list(role_whitelists.values())]))
            tba.append(f"**Channel whitelists: **{ch_wl}")
            tba.append(f"**Role whitelists: **{rl_wl}")
        role_whitelists = settings['channel_whitelists']
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
        for i in range(len(channels)):
            ch = channels[i]
            if isinstance(ch, int):
                tba.append(f"**{chs[i]}: **<#{ch}>")
            else:
                tba.append(f"**{chs[i]}**:")
        for k in a:
            if isinstance(settings[k], list):
                tba.append(f"**{actions[a.index(k)]}: **{', '.join(settings[k])}")
            else:
                tba.append(f"**{actions[a.index(k)]}: **")

    if autotype == 'general':
        channel_whitelists = settings['channel_whitelists']
        ch_wl = ", ".join([f"<#{ch}>" for ch in list(channel_whitelists.values())])
        role_whitelists = settings['role_whitelists']
        rl_wl = (", ".join([f"<@&{rl}>" for rl in list(role_whitelists.values())]))
        tba.append(f"**Channel whitelists:** {ch_wl}")
        tba.append(f"**Role whitelists:** {rl_wl}")
        if "ignored_words" in list(settings.keys()):
            tba.append(f"**Ignored words:** " + ", ".join(settings["ignored_words"]))
        else:
            tba.append(f"**Ignored words:** none")
        if "caps_threshold" in list(settings.keys()):
            tba.append(f"**Caps detection length threshold:** {settings['caps_threshold']}")
        else:
            tba.append(f"**Caps detection length threshold:** 120")

    return discord.Embed(title=setting_stuff[ind], description="\n".join(tba), color=0x5797f7)


async def multi_settings_to_embed(settings, autotype, ind, table):
    embed = discord.Embed(color=0x5797f7, description="")
    if autotype == 'autopunish':
        embed.title = setting_stuff[ind]
        rules = [eval(rule) if isinstance(rule, str) else rule for rule in settings]
        if len(rules) > 0:
            for rule in rules:
                description = ""
                if rule['type'] in ['mute', 'tempban']:
                    d = rule['duration']
                    u = rule['durationType']
                    description += f"**Action: ** {rule['type']} for {d} {u}\n"
                else:
                    description += f"**Action: **{rule['type']}\n"
                description += f"**Threshold: **{rule['threshold']} warn points\n"
                embed.add_field(name=f"Rule #{rules.index(rule) + 1}", value=description, inline=False)
        else:
            embed.description += "There are no rules set."
        return [embed]

    if autotype == 'autokb':
        phder = "\*"
        embed.title = 'Auto kick/ban settings'
        types = {'accountAge': 'account age', 'status': 'blacklisted statuses', 'nsfwpfp': 'NSFW avatars',
                 'promoName': 'invite links in username/status', 'username': 'blacklisted usernames'}

        embed.title = 'Auto kick/ban settings'
        types = {'accountAge': 'account age', 'status': 'blacklisted statuses', 'nsfwpfp': 'NSFW avatars',
                 'promoName': 'invite links in username/status', 'username': 'blacklisted usernames'}
        kick_description = ''
        ban_description = ''
        if "kickrules" in settings:
            if isinstance(settings['kickrules'], list):
                if len(settings['kickrules']) >= 1:
                    rules = [eval(kick_rule) if isinstance(kick_rule, str) else kick_rule for kick_rule in
                             settings['kickrules']]
                    for rule in rules:
                        kick_description += f"### __**Rule #{rules.index(rule) + 1}**__\n**Type: **{types[rule['type']]}\n"
                        if rule['type'] == 'status':
                            kick_description += f"**Blacklisted statuses: ** {', '.join(rule['statuses']).replace('*', phder)}\n"
                            kick_description += f"**Search for substrings: **{int_to_yesno(rule['substring'])}"
                        if rule['type'] == 'username':
                            kick_description += f"**Blacklisted usernames: **{', '.join(rule['usernames']).replace('*', phder)}\n"
                            kick_description += f"**Search for substrings: **{int_to_yesno(rule['substring'])}"
                        if rule['type'] == 'accountAge':
                            t = rule['timeVal']
                            u = rule['timeUnit']
                            kick_description += f"**Minimum account age: **{t} {u}"
                        kick_description += '\n\n'
                else:
                    kick_description += '### **None set at the moment.**\n'
            else:
                kick_description += '### **None set at the moment.**'
            embed.description += f'## **__KICK RULES:__**\n\n{kick_description}\n\n\n\n'

        if "banrules" in settings:
            if isinstance(settings['banrules'], list):
                if len(settings['banrules']) >= 1:
                    rules = [eval(ban_rule) if isinstance(ban_rule, str) else ban_rule for ban_rule in
                             settings['banrules']]
                    for rule in rules:
                        ban_description += f"### __**Rule #{rules.index(rule) + 1}**__\n**Type: **{types[rule['type']]}\n"
                        if rule['type'] == 'status':
                            ban_description += f"**Blacklisted statuses: ** {', '.join(rule['statuses']).replace('*', phder)}\n"
                            ban_description += f"**Search for substrings: **{int_to_yesno(rule['substring'])}"
                        if rule['type'] == 'username':
                            ban_description += f"**Blacklisted usernames: **{', '.join(rule['usernames']).replace('*', phder)}\n"
                            ban_description += f"**Search for substrings: **{int_to_yesno(rule['substring'])}"
                        if rule['type'] == 'accountAge':
                            t = rule['timeVal']
                            u = rule['timeUnit']
                            ban_description += f"**Minimum account age: **{t} {u}"
                        ban_description += '\n\n'
                else:
                    ban_description += '### **None set at the moment.**\n'
            else:
                ban_description += '### **None set at the moment.**\n'
            embed.description += f'## **__BAN RULES:__**\n\n{ban_description}'

        return split_embed(embed, autotype, '')
        # return [embed]

    if autotype == 'blacklist':
        embed.title = setting_stuff[ind]
        if len(settings) > 0:
            for category in settings:
                c = category
                if isinstance(c, str):
                    c = eval(c)
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

                wr_str = ', '.join(words).replace("*", "\*")
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
                desc = f"### __**Category '{title}'**__\n**Punishments:** {p}\n{spec_p}**{s[table]}:** {wr_str}\n{ch}{rl}\n**Search for substrings: **{int_to_yesno(c['substring'])}\n\n"
                embed.description += desc
        else:
            embed.description = '### **No categories set at the moment.**'
        return split_embed(embed, 'blacklist', setting_stuff[ind])


async def unwarn(connection, bot, member, amount, ctx, who):

    key = f"{member.guild.id}_{member.id}"
    info = await connection.fetchrow('SELECT * FROM user_infraction_points WHERE memberkey=$1', key)
    if info is None:
        await ctx.respond('no points to remove!')
    else:
        points = dict(info)['points']
        if points == 0:
            await ctx.respond('no points to remove!')
        elif points - amount < 0:
            await connection.execute('UPDATE user_infraction_points SET memberkey=$1, points=$2 where memberkey=$1',
                                     key, 0)
            await log_unwarn(connection, bot, member, 'all', 0, who)
            await ctx.respond(f"<:amgx_success:1045162009903243294> **{member}** has been unwarned")

        elif amount == 0:
            await connection.execute('UPDATE user_infraction_points SET memberkey=$1, points=$2 where memberkey=$1',
                                     key,
                                     0)
            await log_unwarn(connection, bot, member, 'all', 0, who)
            await connection.execute('UPDATE infractions SET infractions=$3 where guild_id=$1 and member_id=$2',
                                     member.guild.id,
                                     member.id, [])
            await ctx.respond(f"<:amgx_success:1045162009903243294> **{member}** has been unwarned")

        else:
            await connection.execute('UPDATE user_infraction_points SET memberkey=$1, points=$2 where memberkey=$1',
                                     key, points - amount)
            await log_unwarn(connection, bot, member, amount, points - amount, who)
            await ctx.respond(f"<:amgx_success:1045162009903243294> **{member}** has been unwarned")


async def log_unwarn(connection, bot, member, amount, new, who):
    guild = member.guild
    if new != 0:
        await handle_send(member, embed=discord.Embed(title='Someone removed some of your infraction points!',
                                                      description=f"**Points removed:** {amount}\n**Removed by:** {who}",
                                                      color=0x08bf1d))
        settings = await connection.fetchrow(
            'SELECT moderation_channel, moderations, mod_webhook FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['moderations'] is not None
            mod_channel = dict(settings)['moderation_channel'] if actions_not_empty else None
            actions = dict(settings)['moderations'] if actions_not_empty else None
            wh_url = dict(settings)['mod_webhook'] if actions_not_empty else None
            if isinstance(mod_channel, int) and isinstance(actions, list):
                if'Infraction Removed' in actions:
                    embed = discord.Embed(title="Infraction points removed",
                                          description=f"**Points removed:** {amount}\n**Current points:** {new}\n**Moderator: ** {who}",
                                          color=0x68f286)
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
    else:
        await handle_send(member, embed=discord.Embed(title='Someone removed all of your infraction points!',
                                                      description=f"**Points removed:** {amount}\n**Removed by:** {who}",
                                                      color=0x33f25c))
        settings = await connection.fetchrow(
            'SELECT moderation_channel, moderations, mod_webhook FROM modlogs WHERE guild_id=$1', guild.id)
        if settings is not None:
            actions_not_empty = dict(settings)['moderations'] is not None
            mod_channel = dict(settings)['moderation_channel'] if actions_not_empty else None
            actions = dict(settings)['moderations'] if actions_not_empty else None
            wh_url = dict(settings)['mod_webhook'] if actions_not_empty else None
            if isinstance(mod_channel, int) and isinstance(actions, list):
                if 'Infraction Removed' in actions:
                    embed = discord.Embed(title="Infraction points removed",
                                          description=f"**Points removed:** {amount}\n**Current points:** {new}\n**Moderator: ** {who.name} ({who.mention})",
                                          color=0x68f286)
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

    await log_infraction(member, member.guild, {"type": "Unwarn", "Points removed": amount, "Moderator": str(who)},
                         connection)


async def t(time):
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


async def divide_array(nums, k):
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


async def get_infractions(connection, guild, user):
    url = ''
    if str(user.avatar) != 'None':
        url += str(user.avatar)
    else:
        url += 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQY-apNmlwrLUW0vk44GvoQd513FynuObVCo-p8Yb0KYQ&s'
    non_infraction_embed = discord.Embed(title=f'Infractions for {user}', description='This user has no infractions.',
                                         color=0x00ff00)
    non_infraction_embed.set_author(name=str(user), icon_url=url)
    info = await connection.fetchrow('select infractions from infractions where guild_id=$1 and member_id=$2', guild.id,
                                     user.id)
    if info is not None:
        infractions = [eval(infraction.replace('null', 'None')) for infraction in dict(info)['infractions']]
        if len(infractions) == 0:
            return [non_infraction_embed]
        else:
            embeds = []
            divided = await divide_array(infractions, 10)
            pages = len(infractions) // 10 + 1
            if len(infractions) % 10 == 0:
                pages -= 1

            for i in range(pages):
                e = discord.Embed(color=0xff0000, title=f'Infractions for {user}',
                                  description=f'Total infractions: {len(infractions)}')
                for inf in divided[i]:
                    desc = []
                    for k in [key for key in list(inf.keys()) if key != 'type']:
                        desc.append(f"**{k}:** {inf[k]}")
                    e.add_field(name=inf['type'], value='\n'.join(desc), inline=False)
                e.set_author(name=str(user), icon_url=url)
                e.set_footer(text=f"Page {i + 1}/{pages}")
                embeds.append(e)
            return embeds
    else:
        return [non_infraction_embed]


def two_weeks(msg):
    return (datetime.datetime.now(tz=datetime.timezone.utc) - msg.created_at).total_seconds() <= 1209600


async def handle_warn(connection, bot, ctx, member: discord.Member, amount: int, reason):
    bot_user = f"{bot.user.name}#{bot.user.discriminator}"
    await handle_send(member, embed=discord.Embed(title=f"You've been warned in {member.guild}",
                                                  description=f"**Points added:** {amount}\n**Reason:** {reason}\n**Moderator: ** {ctx.author}",
                                                  color=0xf54254))
    await ctx.respond(f"<:amgx_success:1045162009903243294> **{member}** has been warned.")
    punishments = await warn(bot, member, member.guild, amount, connection, reason, ctx.author)

    if "reason" in punishments:
        threshold_reason = punishments['reason']
    else:
        threshold_reason = ""

    if punishments['punishment'] == "ban" and await has_permissions(member.guild.me, member, 'ban_members'):
        await member.ban(
            reason=threshold_reason)
        await handle_send(member,
                          embed=discord.Embed(title=f"You've been banned from {member.guild}",
                                              description=f"**Reason:** {threshold_reason}\n**Moderator: **{bot_user}",
                                              color=0xf54254))
        await log_ban(bot, member.guild, member, threshold_reason,
                      bot, connection)

    if punishments['punishment'] == "tempban" and await has_permissions(member.guild.me, member, 'ban_members'):
        await tempban(bot, member, threshold_reason, punishments['amount'], member.guild,
                      bot_user, connection)

    if punishments['punishment'] == 'kick' and await has_permissions(member.guild.me, member, 'kick_members'):
        await member.kick(
            reason=f"Automatic action for {threshold_reason}")
        await handle_send(member,
                          embed=discord.Embed(title=f"You've been kicked from {member.guild}",
                                              description=f"**Reason:** {threshold_reason}\n**Moderator: **{bot_user}",
                                              color=0xf54254))

    if punishments['punishment'] == 'mute' and await has_permissions(member.guild.me, member, 'moderate_members'):
        await member.timeout(
            until=datetime.datetime.now() + datetime.timedelta(seconds=punishments['amount']))
        await handle_send(member, embed=discord.Embed(title=f"You've been muted in {member.guild}",
                                                      description=f"**Duration:** {await t(punishments['amount'])}\n**Reason:** {threshold_reason}\n**Moderator: **{bot_user}",
                                                      color=0xf54254))


async def handle_warn_error(ctx, error):
    if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Argument `{error.param.name}` is missing.')
    if isinstance(error, discord.ext.commands.errors.MemberNotFound):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Member not found. Check someone else.')
    if isinstance(error, discord.ext.commands.errors.BadArgument):
        await ctx.respond(f"<:amgx_error:1045162027737415751> Invalid value for parameter `amount`")
    if isinstance(error, discord.ext.commands.errors.MissingPermissions):
        await ctx.respond(
            f"<:amgx_error:1045162027737415751> You don't have permissions to run this command: requires `kick_members` and `ban_members`.")


async def handle_purge(ctx, amount: int):
    if amount > 500:
        await ctx.respond('Too many messages.')
    else:
        msgs = await ctx.channel.purge(limit=amount, bulk=True, check=two_weeks)
        if len(msgs) == 0:
            await ctx.respond('No messages were purged, as none under two weeks old were found.')
        else:
            await ctx.respond(f"<:amgx_success:1045162009903243294> purged {len(msgs)} messages.")


async def handle_purge_error(ctx, error):
    if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Argument `{error.param.name}` is missing.')
    if isinstance(error, discord.ext.commands.errors.BadArgument):
        await ctx.respond(f"<:amgx_error:1045162027737415751> Invalid value for parameter `amount`.")
    if isinstance(error, discord.ext.commands.errors.MissingPermissions):
        await ctx.respond(
            f"<:amgx_error:1045162027737415751> You don't have permissions to run this command: requires `manage_messages`.)")


async def handle_unwarn_error(ctx, error):
    if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Argument `{error.param.name}` is missing.')
    if isinstance(error, discord.ext.commands.errors.MemberNotFound):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Member not found. Check someone else.')
    if isinstance(error, discord.ext.commands.errors.BadArgument):
        await ctx.respond(f"<:amgx_error:1045162027737415751> Invalid value for parameter `amount.")
    if isinstance(error, discord.ext.commands.errors.MissingPermissions):
        await ctx.respond(
            f"<:amgx_error:1045162027737415751> You don't have permissions to run this command: requires `kick_members` and `ban_members`.")


async def handle_warns(connection, ctx, member: discord.Member = None):
    uid = 0
    if member is None:
        uid += ctx.author.id
    else:
        uid += member.id
    pts = await connection.fetchrow('SELECT * FROM user_infraction_points WHERE memberkey=$1', f"{ctx.guild.id}_{uid}")
    if pts is None:
        if uid != ctx.author.id:
            await ctx.respond(f"**{member}** has 0 points")
        else:
            await ctx.respond(f'you have 0 points')
    else:
        if uid != ctx.author.id:
            p = dict(pts)['points']
            await ctx.respond(f"**{member}** has {p} points")
        else:
            p = dict(pts)['points']
            await ctx.respond(f"you have {p} points")


async def handle_send_who(connection, ctx, error):
    if isinstance(error, discord.ext.commands.errors.CommandInvokeError):
        info = await connection.fetchrow('SELECT * FROM user_infraction_points WHERE memberkey=$1',
                                         f"{ctx.guild.id}_{ctx.author.id}")
        if info is None:
            await ctx.respond('you have 0 points')
        else:
            await ctx.respond(f"you have {dict(info)['points']} points")
    if isinstance(error, discord.ext.commands.errors.MemberNotFound):
        await ctx.respond('<:amgx_error:1045162027737415751> Member not found. Check someone else.')


async def handle_mute(connection, bot, ctx, member: discord.Member, duration: int, reason=None):
    if member.communication_disabled_until is None or (
            member.communication_disabled_until - datetime.datetime.now(tz=timezone.utc)).total_seconds() < 0:
        await member.timeout(
            until=datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=duration))
        await ctx.respond(f"<:amgx_success:1045162009903243294> **{member}** has been muted")
        await log_mute(bot, member.guild, member, await t(duration),
                       f"{reason} (action requested by {ctx.author.name} ({ctx.author.mention}))", ctx.author, connection)
        await handle_send(member, embed=discord.Embed(title=f"You've been muted in {ctx.guild}",
                                                      description=f"**Duration:** {await t(duration)}\n**Reason:** {reason}\n**Moderator: ** {ctx.author}",
                                                      color=0xf54254))
    else:
        await ctx.respond(f"**{member}** is already muted!")


async def handle_mute_error(ctx, error):
    if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Argument `{error.param.name}` is missing.')
    if isinstance(error, discord.ext.commands.errors.MemberNotFound):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Member not found. Check someone else.')
    if isinstance(error, discord.ext.commands.errors.BadArgument):
        await ctx.respond(f"<:amgx_error:1045162027737415751> Invalid value for parameter `duration`.")
    if isinstance(error, discord.ext.commands.errors.MissingPermissions):
        await ctx.respond(
            f"<:amgx_error:1045162027737415751> You don't have permissions to run this command: requires `moderate_members`.")
    if str(error) == "Command raised an exception: Forbidden: 403 Forbidden (error code: 50013): Missing Permissions":
        await ctx.respond("<:amgx_error:1045162027737415751> I don't have permissions to mute this member.")


async def handle_kick(ctx, member: discord.Member, reason=None):
    await member.kick(reason=f"{reason} (action requested by {ctx.author.name} ({ctx.author.mention}))")
    await handle_send(member,
                      embed=discord.Embed(title=f"You've been kicked from {member.guild}",
                                          description=f"**Reason:** {reason}\n**Moderator: ** {ctx.author}",
                                          color=0xf54254))
    await ctx.respond(f"<:amgx_success:1045162009903243294> **{member}** has been kicked")


async def handle_kick_error(ctx, error):
    if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Argument `{error.param.name}` is missing.')
    if isinstance(error, discord.ext.commands.errors.MemberNotFound):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Member not found. Check someone else.')
    if isinstance(error, discord.ext.commands.errors.MissingPermissions):
        await ctx.respond(
            f"<:amgx_error:1045162027737415751> You don't have permissions to run this command: requires `kick_members`.")
    if str(error) == "Command raised an exception: Forbidden: 403 Forbidden (error code: 50013): Missing Permissions":
        await ctx.respond("<:amgx_error:1045162027737415751> I don't have permissions to kick this member.")


async def unban_tempbanned(user, duration):
    await asyncio.sleep(duration)
    await user.unban()


async def handle_tempban(connection, bot, ctx, member: discord.Member, duration: int, reason, who):
    await member.ban(reason=reason)
    await ctx.respond(f"<:amgx_success:1045162009903243294> **{member}** has been tempbanned")
    await handle_send(member, discord.Embed(title=f"You've been temporarily banned from {member.guild}",
                                            description=f"**Duration: **{await t(duration)}\n**Reason:** {reason}\n**Moderator: **{who}",
                                            color=0xf54254))
    await log_tempban(bot, member.guild, member, duration,
                      f"{reason} (action requested by {ctx.author.name} ({ctx.author.mention}))", who, connection)
    unban_task = asyncio.create_task(unban_tempbanned(member, duration))
    try:
        await unban_task
    except:
        return


async def handle_tempban_error(ctx, error):
    if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Argument `{error.param.name}` is missing.')
    if isinstance(error, discord.ext.commands.errors.MemberNotFound):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Member not found. Check someone else.')
    if isinstance(error, discord.ext.commands.errors.BadArgument):
        await ctx.respond(f"<:amgx_error:1045162027737415751> Invalid value for parameter `duration`.")
    if isinstance(error, discord.ext.commands.errors.MissingPermissions):
        await ctx.respond(
            f"<:amgx_error:1045162027737415751> You don't have permissions to run this command: requires `ban_members`.")
    if str(error) == "Command raised an exception: Forbidden: 403 Forbidden (error code: 50013): Missing Permissions":
        await ctx.respond("<:amgx_error:1045162027737415751> I don't have permissions to ban this member.")


async def handle_ban(connection, bot, ctx, member: discord.Member, reason):
    await member.ban(reason=reason)
    await handle_send(member,
                      embed=discord.Embed(title=f"You've been banned from {member.guild}",
                                          description=f"**Reason:** {reason}\n**Moderator: ** {ctx.author}",
                                          color=0xf54254))
    await ctx.respond(f"<:amgx_success:1045162009903243294> **{member}** has been banned")
    await log_ban(bot, ctx.guild, member, f"{reason} (action requested by {ctx.author.name} ({ctx.author.mention}))",
                  ctx.author, connection)


async def handle_ban_error(ctx, error):
    if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Argument `{error.param.name}` is missing.')
    if isinstance(error, discord.ext.commands.errors.MemberNotFound):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Member not found. Check someone else.')
    if isinstance(error, discord.ext.commands.errors.MissingPermissions):
        await ctx.respond(
            f"<:amgx_error:1045162027737415751> You don't have permissions to run this command: requires `ban_members`.")
    # if isinstance(error, discord.ext.commands.errors.Forbidden):
    #     await ctx.respond("<:amgx_error:1045162027737415751> I don't have permissions to ban this member.")


async def handle_unmute(connection, bot, ctx, member: discord.Member):
    if member.communication_disabled_until is not None:
        if (member.communication_disabled_until - datetime.datetime.now(tz=timezone.utc)).total_seconds() > 0:
            await member.timeout(until=None)
            await ctx.respond(f"<:amgx_success:1045162009903243294> **{member}** has been unmuted")
            await log_unmute(bot, member.guild, member, connection, ctx.author)
            await handle_send(member, embed=discord.Embed(title=f"You've been unmuted in {ctx.guild}",
                                                          description=f"**Moderator: **{ctx.author}", color=0x33f25c))
        else:
            await ctx.respond(f"**{member}** is already unmuted!")
    else:
        await ctx.respond(f"**{member}** is already unmuted!")


async def handle_unmute_error(ctx, error):
    if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Argument `{error.param.name}` is missing.')
    if isinstance(error, discord.ext.commands.errors.MemberNotFound):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Member not found. Check someone else.')
    if isinstance(error, discord.ext.commands.errors.MissingPermissions):
        await ctx.respond(
            f"<:amgx_error:1045162027737415751> You don't have permissions to run this command: requires `moderate_members`.")
    if str(error) == "Command raised an exception: Forbidden: 403 Forbidden (error code: 50013): Missing Permissions":
        await ctx.respond("<:amgx_error:1045162027737415751> I don't have permissions to unmute this member.")


async def handle_unban(ctx, member: discord.User):
    bans = await ctx.guild.bans().flatten()
    for ban in bans:
        if ban.user.id == member.id:
            await ctx.guild.unban(ban.user)
            await ctx.respond(f"<:amgx_success:1045162009903243294> **{member}** has been unbanned.")
            return
    await ctx.respond(f"<:amgx_error:1045162027737415751> **{member}** is already unbanned!")


async def handle_unban_error(ctx, error):
    if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Argument `{error.param.name}` is missing.')
    if isinstance(error, discord.ext.commands.errors.MemberNotFound):
        await ctx.respond(f'<:amgx_error:1045162027737415751> Member not found. Check someone else.')
    if isinstance(error, discord.ext.commands.errors.MissingPermissions):
        await ctx.respond(
            f"<:amgx_error:1045162027737415751> You don't have permissions to run this command: requires `ban_members`.")
    if str(error) == "Command raised an exception: Forbidden: 403 Forbidden (error code: 50013): Missing Permissions":
        await ctx.respond("<:amgx_error:1045162027737415751> I don't have permissions to unban this member.")


async def handle_amsettings(connection, ctx, setting):
    if setting in msg_tables:
        settings = await connection.fetchrow(f"SELECT {setting} FROM msg_automod WHERE guild_id=$1", ctx.guild.id)
        if settings is None:
            if setting in ['messagespam', 'emojispam', 'mentionspam', 'stickerspam', 'attachmentspam', 'linkspam']:
                await ctx.respond(embed=await settings_to_embed(default_settings[setting], 'spam',
                                                                tables.index(setting)))
            elif setting in ['duplicatecharacters', 'duplicatemessages', 'linebreaks', 'toomanycaps']:
                await ctx.respond(
                    embed=await settings_to_embed(default_settings[setting], 'toomuch',
                                                  tables.index(setting)))
            elif setting in ['invites', 'hatespeech', 'selfbot', 'nsfwcontent']:
                await ctx.respond(
                    embed=await settings_to_embed(default_settings[setting], 'unacceptable',
                                                  tables.index(setting)))
            elif setting in ['badlinks', 'badwords', 'badnicks', 'badnames', 'badstatuses']:
                embeds = await multi_settings_to_embed(default_settings[setting]['categories'], 'blacklist', tables.index(setting), setting)
                embed_groups = []
                cur_group = {"group": []}
                while len(embeds) > 0:
                    if sum([embed_len(e) for e in cur_group["group"]]) + embed_len(embeds[0]) <= 6000:
                        cur_group["group"] += [embeds[0]]
                        embeds = embeds[1:]
                        if len(embeds) == 0:
                            embed_groups.append(cur_group["group"])
                            cur_group["group"] = []
                    else:
                        embed_groups.append(cur_group["group"])
                        cur_group["group"] = []

                for i in range(len(embed_groups)):
                    if i == 0:
                        await ctx.respond(embeds=embed_groups[i])
                    else:
                        await ctx.send(embeds=embed_groups[i])
            else:
                await ctx.respond(
                    embed=await settings_to_embed({'channel_whitelists': {}, 'role_whitelists': {}}, 'general',
                                                  len(setting_stuff) - 1))
        else:
            mod_settings = eval(dict(settings)[setting])
            if setting in ['messagespam', 'emojispam', 'mentionspam', 'stickerspam', 'attachmentspam', 'linkspam']:
                await ctx.respond(embed=await settings_to_embed(mod_settings, 'spam',
                                                                tables.index(setting)))
            elif setting in ['duplicatecharacters', 'duplicatemessages', 'linebreaks', 'toomanycaps']:
                await ctx.respond(
                    embed=await settings_to_embed(mod_settings, 'toomuch',
                                                  tables.index(setting)))
            elif setting in ['invites', 'hatespeech', 'selfbot', 'nsfwcontent']:
                await ctx.respond(
                    embed=await settings_to_embed(mod_settings, 'unacceptable',
                                                  tables.index(setting)))
            elif setting in ['badlinks', 'badwords', 'badnicks', 'badnames', 'badstatuses']:
                embeds = await multi_settings_to_embed(mod_settings['categories'], 'blacklist', tables.index(setting), setting)
                embed_groups = []
                cur_group = {"group": []}
                while len(embeds) > 0:
                    if sum([embed_len(e) for e in cur_group["group"]]) + embed_len(embeds[0]) <= 6000:
                        cur_group["group"] += [embeds[0]]
                        embeds = embeds[1:]
                        if len(embeds) == 0:
                            embed_groups.append(cur_group["group"])
                            cur_group["group"] = []
                    else:
                        embed_groups.append(cur_group["group"])
                        cur_group["group"] = []

                for i in range(len(embed_groups)):
                    if i == 0:
                        await ctx.respond(embeds=embed_groups[i])
                    else:
                        await ctx.send(embeds=embed_groups[i])
            else:
                await ctx.respond(
                    embed=await settings_to_embed(mod_settings, 'general',
                                                  len(setting_stuff) - 1))
    else:
        settings = await connection.fetchrow(f"SELECT * FROM {setting} WHERE guild_id=$1", ctx.guild.id)
        if settings is None:
            if setting in ['badnicks', 'badnames', 'badstatuses']:
                embeds = await multi_settings_to_embed(default_settings[setting], 'blacklist', tables.index(setting), setting)
                embed_groups = []
                cur_group = {"group": []}
                while len(embeds) > 0:
                    if sum([embed_len(e) for e in cur_group["group"]]) + embed_len(embeds[0]) <= 6000:
                        cur_group["group"] += [embeds[0]]
                        embeds = embeds[1:]
                        if len(embeds) == 0:
                            embed_groups.append(cur_group["group"])
                            cur_group["group"] = []
                    else:
                        embed_groups.append(cur_group["group"])
                        cur_group["group"] = []

                for i in range(len(embed_groups)):
                    if i == 0:
                        await ctx.respond(embeds=embed_groups[i])
                    else:
                        await ctx.send(embeds=embed_groups[i])
            elif setting == 'nsfwpfp':
                await ctx.respond(
                    embed=await settings_to_embed(default_settings[setting], 'unacceptable',
                                                  tables.index(setting)))
            elif setting == 'modlogs':
                await ctx.respond(embed=await settings_to_embed(default_modlogs, 'modlogs', tables.index(setting)))
            elif setting == 'autopunish':
                await ctx.respond(
                    embeds=await multi_settings_to_embed(default_autopunish, 'autopunish', tables.index(setting), 't'))
            else:
                embeds = await multi_settings_to_embed(default_autokb, 'autokb', tables.index(setting), 't')
                embed_groups = []
                cur_group = {"group": []}
                while len(embeds) > 0:
                    if sum([embed_len(e) for e in cur_group["group"]]) + embed_len(embeds[0]) <= 6000:
                        cur_group["group"] += [embeds[0]]
                        embeds = embeds[1:]
                        if len(embeds) == 0:
                            embed_groups.append(cur_group["group"])
                            cur_group["group"] = []
                    else:
                        embed_groups.append(cur_group["group"])
                        cur_group["group"] = []

                for i in range(len(embed_groups)):
                    if i == 0:
                        await ctx.respond(embeds=embed_groups[i])
                    else:
                        await ctx.send(embeds=embed_groups[i])
        else:
            if setting in ['badnicks', 'badnames', 'badstatuses']:
                embeds = await multi_settings_to_embed(dict(settings)['categories'], 'blacklist', tables.index(setting), setting)
                embed_groups = []
                cur_group = {"group": []}
                while len(embeds) > 0:
                    if sum([embed_len(e) for e in cur_group["group"]]) + embed_len(embeds[0]) <= 6000:
                        cur_group["group"] += [embeds[0]]
                        embeds = embeds[1:]
                        if len(embeds) == 0:
                            embed_groups.append(cur_group["group"])
                            cur_group["group"] = []
                    else:
                        embed_groups.append(cur_group["group"])
                        cur_group["group"] = []

                for i in range(len(embed_groups)):
                    if i == 0:
                        await ctx.respond(embeds=embed_groups[i])
                    else:
                        await ctx.send(embeds=embed_groups[i])
            elif setting == 'nsfwpfp':
                await ctx.respond(
                    embed=await settings_to_embed(dict(settings), 'unacceptable',
                                                  tables.index(setting)))
            elif setting == 'modlogs':
                await ctx.respond(embed=await settings_to_embed(dict(settings), 'modlogs', tables.index(setting)))
            elif setting == 'autopunish':
                await ctx.respond(embeds=await multi_settings_to_embed(dict(settings)['rules'], 'autopunish', tables.index(setting),
                                                        't'))
            else:
                embeds = await multi_settings_to_embed(dict(settings), 'autokb', tables.index(setting), 't')
                embed_groups = []
                cur_group = {"group": []}
                while len(embeds) > 0:
                    if sum([embed_len(e) for e in cur_group["group"]]) + embed_len(embeds[0]) <= 6000:
                        cur_group["group"] += [embeds[0]]
                        embeds = embeds[1:]
                        if len(embeds) == 0:
                            embed_groups.append(cur_group["group"])
                            cur_group["group"] = []
                    else:
                        embed_groups.append(cur_group["group"])
                        cur_group["group"] = []

                for i in range(len(embed_groups)):
                    if i == 0:
                        await ctx.respond(embeds=embed_groups[i])
                    else:
                        await ctx.send(embeds=embed_groups[i])


async def handle_infractions(connection, ctx, member: discord.Member = None, page: int = 1):
    if member is None:
        infs = await get_infractions(connection, ctx.guild, ctx.author)
        if page > len(infs):
            await ctx.respond(embed=infs[-1])
        else:
            await ctx.respond(embed=infs[page - 1])
    else:
        infs = await get_infractions(connection, ctx.guild, member)
        if page > len(infs):
            await ctx.respond(embed=infs[-1])
        else:
            await ctx.respond(embed=infs[page - 1])


async def handle_inf_err(ctx, error):
    if isinstance(error, discord.ext.commands.errors.MemberNotFound):
        await ctx.respond('<:amgx_error:1045162027737415751> Member not found. check someone else')


async def handle_feedback(bot, title, feedback):
    await bot.get_channel(1125957448365252649).send(embed=discord.Embed(title=f"New Feedback: {title}", description=feedback, color=0x40fc0c))
