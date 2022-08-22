import datetime
from itertools import islice
import emojis
import requests
from urlextract import URLExtract
import discord
from discord.ext import commands
import asyncio
from features.hatespeech import hate_speech_detection
from features.punishing import warn, log_tempban, log_mute, punish_nsfw, log_ban
from features.spellchecking import check
import asyncpg

dbpass = 'mysecretpassword'
import re
from difflib import SequenceMatcher as sm

tables = ['modlogs','messagespam', 'emojispam', 'mentionspam', 'stickerspam', 'attachmentspam', 'linkspam','duplicatecharacters','duplicatemessages','linebreaks','toomanycaps','invites','selfbot','nsfwcontent','hatespeech','badwords','badlinks','badnicks','badnames','badstatuses','nsfwpfp','autopunish','autokickban']

setting_stuff = ["Modlog settings","Message spam settings","Emoji spam settings","Mention spam settings","Sticker spam settings","Attachment spam settings","Link spam settings", "Duplicate character settings", "Duplicate message settings", "Line break settings", "Capitals settings", "Invite settings", "Selfbot settings", "NSFW content settings", "Hate speech settings",'Bad word settings','Bad link settings','Bad nickname settings','Bad username settings','Bad custom status settings','NSFW avatar settings', 'Autopunish settings',' Auto kick/ban settings']
s = {'badlinks': 'Blacklisted links','badwords': 'Blacklisted words','badnicks': 'Blacklisted nicknames','badnames': 'Blacklisted usernames','badstatuses': 'Blacklisted custom statuses'}

default_settings = {'messagespam': {"punishments":["Delete message","Mute","Warn"],"maxes":[5,2],"channel_whitelists":'{}',"role_whitelists":'{}',"points":5,"timeval":40,"timeunit":"minutes"}, 'emojispam': {"punishments":["Delete message","Mute"],"maxes":[5,2],"channel_whitelists":'{}',"role_whitelists":'{}',"points":0,"timeval":20,"timeunit":"minutes"}, 'mentionspam': {"punishments":["Delete message","Mute","Warn"],"maxes":[8,2],"channel_whitelists":'{}',"role_whitelists":'{}',"points":6,"timeval":3,"timeunit":"hours"}, 'stickerspam': {"punishments":["Delete message","Mute"],"maxes":[5,2],"channel_whitelists":'{}',"role_whitelists":'{}',"points":0,"timeval":2,"timeunit":"hours"}, 'attachmentspam': {"punishments":["Delete message","Mute","Warn"],"maxes":[5,2],"channel_whitelists":'{}',"role_whitelists":'{}',"points":5,"timeval":3,"timeunit":"hours"}, 'linkspam': {"punishments":["Delete message","Mute"],"maxes":[6,2],"channel_whitelists":'{}',"role_whitelists":'{}',"points":0,"timeval":2,"timeunit":"hours"}, 'linebreaks': {"punishments":["Delete message","Mute"],"top":6,"points":0,"timeunit":"minutes","timeval":30,"channel_whitelists":'{}',"role_whitelists":'{}'}, 'toomanycaps': {"punishments":["Delete message","Mute","Warn"],"top":90,"points":5,"timeunit":"minutes","timeval":45,"channel_whitelists":'{}',"role_whitelists":'{}'}, 'duplicatemessages': {"punishments":["Delete message","Mute","Warn"],"top":5,"points":4,"timeunit":"hours","timeval":2,"channel_whitelists":'{}',"role_whitelists":'{}'}, 'duplicatecharacters': {"punishments":["Delete message","Mute","Warn"],"top":10,"points":5,"timeunit":"minutes","timeval":45,"channel_whitelists":'{}',"role_whitelists":'{}'}, 'invites': {"punishments":["Delete message","Warn"],"points":5,"timeunit":"minutes","timeval":0,"channel_whitelists":'{}',"role_whitelists":'{}'}, 'nsfwcontent': {"punishments":["Delete message","Ban"],"points":0,"timeunit":"minutes","timeval":0,"channel_whitelists":'{}',"role_whitelists":'{}'}, 'hatespeech': {"punishments":["Delete message","Warn","Tempban"],"points":15,"timeunit":"days","timeval":3,"channel_whitelists":'{}',"role_whitelists":'{}'}, 'selfbot': {"punishments":["Delete message","Ban"],"points":0,"timeunit":"minutes","timeval":0,"role_whitelists":'{}'},

'badwords': [str({"title":"slurs","punishments":["Delete message","Warn"],"words":{"nigger":"Substring","fag":"Substring","tranny":"Substring","trannies":"Substring","chingchong":"Substring","ching chang":"Substring"},"points":20,"timeval":0,"timeunit":"minutes","whitelistedRoles":{},"whitelistedChannels":{},"duration":0})],

'badlinks': [str({"title":"nsfw","punishments":["Delete message","Ban"],"words":{"pornhub":"Substring","xvideos":"Substring","spankbang":"Substring","xnxx":"Substring","xhamster":"Substring","chaturbate":"Substring","youporn":"Substring","tnaflix":"Substring","nuvid":"Substring","drtuber":"Substring","xxxbunker":"Substring","xxxvideo":"Substring","fapvidhd":"Substring","xxxvideos247":"Substring","pornhd":"Substring","redtube":"Substring","fapster":"Substring","tastyblacks":"Substring","hclips":"Substring","tube8":"Substring"},"points":0,"timeval":0,"timeunit":"minutes","whitelistedRoles":{},"whitelistedChannels":{},"duration":0}),str({"title":"gory","punishments":["Delete message","Ban"],"words":{"bestgore":"Substring","theync":"Substring","kaotic":"Substring","goregrish":"Substring","crazyshit":"Substring","efukt":"Substring","runthegauntlet":"Substring","ogrishforum":"Substring"},"points":0,"timeval":0,"timeunit":"minutes","whitelistedRoles":{},"whitelistedChannels":{},"duration":0})],

'badnicks': [str({"title":"triggering","punishments":["Ban"],"words":{"hitler":"Substring","nazi":"Substring","adolf":"Substring","holocaust":"Substring","auschwitz":"Substring","rapist":"Substring","porn":"Substring","molest":"Substring","traffick":"Substring","rape":"NoSubstring","raping":"NoSubstring","pedo":"Substring","paedo":"Substring","sex":"NoSubstring"},"points":0,"timeval":0,"timeunit":"minutes","whitelistedRoles":{},"whitelistedChannels":{},"duration":0}),str({"title":"slurs","punishments":["Warn","Tempban"],"words":{"nigger":"Substring","fag":"Substring","tranny":"Substring","trannies":"Substring","chingchong":"Substring","ching chang":"Substring"},"points":20,"timeval":3,"timeunit":"days","whitelistedRoles":{},"whitelistedChannels":{},"duration":0})],

'badnames': [str({"title":"triggering","punishments":["Ban"],"words":{"hitler":"Substring","nazi":"Substring","adolf":"Substring","holocaust":"Substring","auschwitz":"Substring","rapist":"Substring","porn":"Substring","molest":"Substring","traffick":"Substring","rape":"NoSubstring","raping":"NoSubstring","pedo":"Substring","paedo":"Substring","sex":"NoSubstring"},"points":0,"timeval":0,"timeunit":"minutes","whitelistedRoles":{},"whitelistedChannels":{},"duration":0}),str({"title":"slurs","punishments":["Warn","Tempban"],"words":{"nigger":"Substring","fag":"Substring","tranny":"Substring","trannies":"Substring","chingchong":"Substring","ching chang":"Substring"},"points":20,"timeval":3,"timeunit":"days","whitelistedRoles":{},"whitelistedChannels":{},"duration":0})],

'badstatuses': [str({"title":"triggering","punishments":["Ban"],"words":{"hitler":"Substring","nazi":"Substring","adolf":"Substring","holocaust":"Substring","auschwitz":"Substring","rapist":"Substring","porn":"Substring","molest":"Substring","traffick":"Substring","rape":"NoSubstring","raping":"NoSubstring","pedo":"Substring","paedo":"Substring","sex":"NoSubstring"},"points":0,"timeval":0,"timeunit":"minutes","whitelistedRoles":{},"whitelistedChannels":{},"duration":0}),str({"title":"slurs","punishments":["Warn","Tempban"],"words":{"nigger":"Substring","fag":"Substring","tranny":"Substring","trannies":"Substring","chingchong":"Substring","ching chang":"Substring"},"points":20,"timeval":3,"timeunit":"days","whitelistedRoles":{},"whitelistedChannels":{},"duration":0})],


'nsfwpfp': {"punishments":["Ban"],"points":0,"timeunit":"minutes","timeval":0,"role_whitelists":'{}'}}

def total_s(msg1, msg2):
    return (msg1.created_at - msg2.created_at).total_seconds()


def msg_within_time(arr, low, high, now, limit):
    most_recent_msg = arr[0]
    if high >= low:
        mid = (high + low) // 2

        mid_total_s = total_s(most_recent_msg, arr[mid])
        # print(f"length: {len(arr)}, mid: {mid}, higher: {mid+1}")
        # If element is present at the middle itself
        if high == low:
            return mid

        elif mid_total_s < limit <= total_s(most_recent_msg, arr[mid+1]):
            return mid

        # If element is smaller than mid, then it can only
        # be present in left subarray
        elif mid_total_s > limit:
            return msg_within_time(arr, low, mid - 1, now, limit)

        # Else the element can only be present in right subarray
        else:
            return msg_within_time(arr, mid + 1, high, now, limit)


def get_default_emoji(sentence):
    return emojis.count(sentence)


def get_message_emojis(m: discord.Message):
    """ Returns a list of custom emojis in a message. """
    emojis = re.findall('<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>', m.content)
    return len([discord.PartialEmoji(animated=bool(animated), name=name, id=id) for animated, name, id in emojis]) + get_default_emoji(m.content)


def get_someone_msgs(messages,author):
    msgs = []
    for message in messages:
        if message.author == author:
            msgs.append(message)
    return msgs


def get_feature(messages, ty):
    features = 0
    extract = URLExtract()
    if ty == 'mentions':
        for message in messages:
            features += len(re.findall('<@\d{18}>', message.content)) + len(re.findall('<@\d{19}>', message.content))
    if ty == 'stickers':
        for message in messages:
            features += len(message.stickers)
    if ty == 'attachments':
        for message in messages:
            features += len(message.attachments)
    if ty == 'links':
        for message in messages:
            features += len(extract.find_urls(message.content.replace('http', ' http').replace('www.', ' www.')))
    if ty == 'emojis':
        for message in messages:
            features += get_message_emojis(message)

    return features


def similarity(messages):
    match_ratios = []
    if messages[0].content != '':
        for i in range(1, len(messages)):
            match_ratios.append(sm(None, messages[0].content, messages[i].content).ratio())

    return match_ratios


def similar(n):
    return n >= 0.85


def time(amount, units):
    if isinstance(amount, int) and isinstance(units, str):
        if units == 'seconds':
            return amount
        if units == 'minutes':
            return 60 * amount
        if units == 'hours':
            return 3600 * amount
        if units == 'days':
            return 86400 * amount
    return 0


async def msg_automod(guild_id):
    d = {}
    for table in ['messagespam', 'emojispam', 'mentionspam', 'stickerspam', 'attachmentspam', 'linkspam','duplicatecharacters','duplicatemessages','linebreaks','toomanycaps','invites','selfbot','nsfwcontent','hatespeech','badwords','badlinks']:
        record = await warn_conn.fetchrow(f'SELECT * FROM {table} WHERE guild_id=$1', guild_id)
        if record is not None:
            r = dict(record)
            d[table] = {}
            for k in [key for key in list(r.keys()) if key != 'guild_id']:
                d[table][k] = r[k]

    return d


async def message_punishments(message, guild, bot):
    final_punishments = {'mute': 0, 'warn': 0, 'kick': False, 'tempban': 0, 'ban': False, 'mute_reason': [], 'warn_reason': [], 'kick_reason': [], 'tempban_reason': [], 'ban_reason': [], 'deletes': []}

    def handle(mesgs, punishmts, table, reason):
        if "Delete message" in punishmts:
            final_punishments['deletes'] += mesgs
        if "Ban" in punishmts:
            final_punishments['ban'] = True
            final_punishments['ban_reason'].append(reason)
        if "Warn" in punishmts and table['points'] not in [None, 0]:
            final_punishments['warn'] += table['points']
            final_punishments['warn_reason'].append(reason)
        if "Tempban" in punishmts:
            final_punishments['tempban'] += time(table['timeval'], table['timeunit'])
            final_punishments['tempban_reason'].append(reason)
        if "Kick" in punishmts:
            final_punishments['kick'] = True
            final_punishments['kick_reason'].append(reason)
        if "Mute" in punishmts:
            final_punishments['mute'] += time(table['timeval'], table['timeunit'])
            final_punishments['mute_reason'].append(reason)
    settings = await msg_automod(message.guild.id)

    if guild is not None and not message.author.bot:
        cache = list(bot.cached_messages)[::-1]
        if 'messagespam' in settings:
            message_spam_settings = settings['messagespam']
        else:
            message_spam_settings = default_settings['messagespam']
        ms = msg_within_time(cache, 0, len(cache)-1, message.created_at, message_spam_settings['maxes'][1]) + 1
        punishments = message_spam_settings['punishments']
        role_whitelists = list(set(eval(message_spam_settings['role_whitelists']).values()))
        channel_whitelists = list(eval(message_spam_settings['channel_whitelists']).values())
        if message_spam_settings['maxes'][1] not in [None, 0] and message_spam_settings['maxes'][0] not in [None, 0,1]:
            limit = message_spam_settings['maxes'][0]

            messages = [msg for msg in cache[0:ms] if msg.guild == message.guild and msg.author == message.author]
            if len(messages) >= limit and str(message.channel.id) not in channel_whitelists and len(set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                handle(messages, punishments, message_spam_settings, f"sending messages too quickly: {len(messages)} messages in {message_spam_settings['maxes'][1]} seconds")


        if 'mentionspam' in settings:
            mention_spam_settings = settings['mentionspam']
        else:
            mention_spam_settings = default_settings['mentionspam']
        me = msg_within_time(cache, 0, len(cache) - 1, message.created_at, mention_spam_settings['maxes'][1]) + 1
        punishments = mention_spam_settings['punishments']
        role_whitelists = set(eval(mention_spam_settings['role_whitelists']).values())
        channel_whitelists = list(eval(mention_spam_settings['channel_whitelists']).values())
        if mention_spam_settings['maxes'][1] not in [None, 0] and mention_spam_settings['maxes'][0] not in [None, 0,1]:
            limit = mention_spam_settings['maxes'][0]
            messages = [msg for msg in cache[0:me] if msg.guild == message.guild and msg.author == message.author]
            msgs_channels = set([msg.channel.id for msg in messages])
            if get_feature(messages, 'mentions') >= limit and not len(msgs_channels.intersection(set(channel_whitelists))) == len(msgs_channels) and len(set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                handle(messages, punishments, mention_spam_settings, f"sending mentions too quickly: {get_feature(messages,'mentions')} mentions in {mention_spam_settings['maxes'][1]} seconds")


        if 'attachmentspam' in settings:
            attach_spam_settings = settings['attachmentspam']
        else:
            attach_spam_settings = default_settings['attachmentspam']
        at = msg_within_time(cache, 0, len(cache) - 1, message.created_at, attach_spam_settings['maxes'][1]) + 1
        punishments = attach_spam_settings['punishments']
        role_whitelists = set(eval(attach_spam_settings['role_whitelists']).values())
        channel_whitelists = list(eval(attach_spam_settings['channel_whitelists']).values())
        if attach_spam_settings['maxes'][1] not in [None, 0] and attach_spam_settings['maxes'][0] not in [None, 0,1]:
            limit = attach_spam_settings['maxes'][0]
            messages = [msg for msg in cache[0:at] if msg.guild == message.guild and msg.author == message.author]
            if get_feature(messages, 'attachments') >= limit and str(
                    message.channel.id) not in channel_whitelists and len(
                    set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                handle(messages, punishments, attach_spam_settings, f"sending attachments too quickly: {get_feature(messages,'attachments')} attachments in {attach_spam_settings['maxes'][1]} seconds")


        if 'linkspam' in settings:
            link_spam_settings = settings['linkspam']
        else:
            link_spam_settings = default_settings['linkspam']
        ln = msg_within_time(cache, 0, len(cache) - 1, message.created_at, link_spam_settings['maxes'][1]) + 1
        punishments = link_spam_settings['punishments']
        role_whitelists = set(eval(link_spam_settings['role_whitelists']).values())
        channel_whitelists = list(eval(link_spam_settings['channel_whitelists']).values())
        if link_spam_settings['maxes'][1] not in [None, 0] and link_spam_settings['maxes'][0] not in [None, 0,1]:
            limit = link_spam_settings['maxes'][0]
            messages = [msg for msg in cache[0:ln] if msg.guild == message.guild and msg.author == message.author]
            if get_feature(messages, 'links') >= limit and str(
                    message.channel.id) not in channel_whitelists and len(
                    set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                handle(messages, punishments, link_spam_settings, f"sending links too quickly: {get_feature(messages,'links')} links in {link_spam_settings['maxes'][1]} seconds")


        if 'stickerspam' in settings:
            sticker_spam_settings = settings['stickerspam']
        else:
            sticker_spam_settings = default_settings['stickerspam']
        st = msg_within_time(cache, 0, len(cache) - 1, message.created_at, sticker_spam_settings['maxes'][1]) + 1
        punishments = sticker_spam_settings['punishments']
        role_whitelists = set(eval(sticker_spam_settings['role_whitelists']).values())
        channel_whitelists = list(eval(sticker_spam_settings['channel_whitelists']).values())
        if sticker_spam_settings['maxes'][1] not in [None, 0] and sticker_spam_settings['maxes'][0] not in [None, 0,1]:
            limit = sticker_spam_settings['maxes'][0]
            messages = [msg for msg in cache[0:st] if msg.guild == message.guild and msg.author == message.author]
            if get_feature(messages, 'stickers') >= limit and str(
                    message.channel.id) not in channel_whitelists and len(
                    set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                handle(messages, punishments, sticker_spam_settings, f"sending stickers too quickly: {get_feature(messages,'stickers')} stickers in {sticker_spam_settings['maxes'][1]} seconds")


        if 'emojispam' in settings:
            emoji_spam_settings = settings['emojispam']
        else:
            emoji_spam_settings = default_settings['emojispam']
        em = msg_within_time(cache, 0, len(cache) - 1, message.created_at, emoji_spam_settings['maxes'][1]) + 1
        punishments = emoji_spam_settings['punishments']
        role_whitelists = set(eval(emoji_spam_settings['role_whitelists']).values())
        channel_whitelists = list(eval(emoji_spam_settings['channel_whitelists']).values())
        if emoji_spam_settings['maxes'][1] not in [None, 0] and emoji_spam_settings['maxes'][0] not in [None,0, 1]:
            limit = emoji_spam_settings['maxes'][0]
            messages = [msg for msg in cache[0:em] if msg.guild == message.guild and msg.author == message.author]
            if get_feature(messages, 'emojis') >= limit and str(
                    message.channel.id) not in channel_whitelists and len(
                set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                handle(messages, punishments, emoji_spam_settings, f"sending emojis too quickly: {get_feature(messages,'emojis')} emojis in {emoji_spam_settings['maxes'][1]} seconds")


        if 'duplicatemessages' in settings:
            dupe_msg_settings = settings['duplicatemessages']
        else:
            dupe_msg_settings = default_settings['duplicatemessages']
        if dupe_msg_settings['top'] not in [0, 1, None]:
            dp = msg_within_time(cache, 0, len(cache) - 1, message.created_at, 90) + 1
            ret_messages = (list([msg for msg in cache[0:dp] if
                                          msg.author == message.author and msg.channel == message.channel])[::-1])[
                           0:dupe_msg_settings['top']]
            msgs = list(islice(ret_messages, dict(dupe_msg_settings)['top']))
            amount_similar = list(map(similar, similarity(msgs))).count(True) + 1
            punishments = dupe_msg_settings['punishments']
            role_whitelists = set(eval(dupe_msg_settings['role_whitelists']).values())
            channel_whitelists = list(eval(dupe_msg_settings['channel_whitelists']).values())
            if amount_similar >= dict(dupe_msg_settings)['top'] and str(message.channel.id) not in channel_whitelists and len(set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                handle(msgs, punishments, dupe_msg_settings, f"sending the same message {amount_similar}x in a row")


        if 'toomanycaps' in settings:
            caps_settings = settings['toomanycaps']
        else:
            caps_settings = default_settings['toomanycaps']
        content = message.content
        if len([c for c in content if c.isalpha()]) > 0:
            caps_percent = 100 * sum(1 for c in content if c.isupper()) / (len([c for c in content if c.isalpha()]))
            if caps_settings['top'] not in [0, None]:
                punishments = caps_settings['punishments']
                role_whitelists = set(eval(caps_settings['role_whitelists']).values())
                channel_whitelists = list(eval(caps_settings['channel_whitelists']).values())

                if caps_percent >= dict(caps_settings)['top'] and len(
                        [c for c in content if c.isalpha()]) >= 60 and str(
                        message.channel.id) not in channel_whitelists and len(
                        set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                    handle([message], punishments, caps_settings, f"sending a message with {caps_percent}% caps")


        if 'linebreaks' in settings:
            linebreak_settings = settings['linebreaks']
        else:
            linebreak_settings = default_settings['linebreaks']
        if linebreak_settings['top'] not in [0, 1, None]:
            punishments = linebreak_settings['punishments']
            role_whitelists = set(eval(linebreak_settings['role_whitelists']).values())
            channel_whitelists = list(eval(linebreak_settings['channel_whitelists']).values())
            if message.content.count('\n') >= dict(linebreak_settings)['top'] and str(
                    message.channel.id) not in channel_whitelists and len(
                    set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                n = message.content.count('\n')
                handle([message], punishments, linebreak_settings, f"sending a message with {n} line breaks")


        if 'duplicatecharacters' in settings:
            repeat_char_settings = settings['duplicatecharacters']
        else:
            repeat_char_settings = default_settings['duplicatecharacters']
        if repeat_char_settings['top'] not in [0, 1, None]:
            punishments = repeat_char_settings['punishments']
            role_whitelists = set(eval(repeat_char_settings['role_whitelists']).values())
            channel_whitelists = list(eval(repeat_char_settings['channel_whitelists']).values())
            top = dict(repeat_char_settings)['top']

            if (bool(re.findall(r"(.+)\1" + '{' + f"{top - 1}," + "}", message.content.lower().replace(' ','')))) and str(
                    message.channel.id) not in channel_whitelists and len(
                    set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                handle([message], punishments, repeat_char_settings, f"sending a message that repeats the same characters {repeat_char_settings['top']}+ times in a row")


        if 'invites' in settings:
            invite_settings = settings['invites']
        else:
            invite_settings = default_settings['invites']
        punishments = invite_settings['punishments']
        role_whitelists = set(eval(invite_settings['role_whitelists']).values())
        channel_whitelists = list(eval(invite_settings['channel_whitelists']).values())
        if bool(re.findall(r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?',message.content)) and str(message.channel.id) not in channel_whitelists and len(set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
            handle([message], punishments, invite_settings, 'sending a message with invites')


        if 'selfbot' in settings:
            selfbot_settings = settings['selfbot']
        else:
            selfbot_settings = default_settings['selfbot']
        punishments = selfbot_settings['punishments']
        role_whitelists = set(eval(selfbot_settings['role_whitelists']).values())
        if len([embed for embed in message.embeds if embed.type == 'rich']) >= 1 and not message.author.bot and len(set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
            handle([message], punishments, selfbot_settings, 'selfbotting')


        if 'nsfwcontent' in settings:
            nsfw_settings = settings['nsfwcontent']
        else:
            nsfw_settings = default_settings['nsfwcontent']
        images = [embed.url for embed in message.embeds if embed.type == 'image'] + [attachment.url for attachment
                                                                                     in message.attachments if
                                                                                      attachment.url.endswith(
                                                                                         'jpg') or attachment.url.endswith(
                                                                                         'jpeg') or attachment.url.endswith(
                                                                                         'png')]
        nsfw = []
        for image in images:
            nsfw.append(
                requests.post(
                    "https://api.deepai.org/api/nsfw-detector",
                    data={
                        'image': image,
                    },
                    headers={'api-key': '0c25ca40-f09f-45d2-8546-8bd867cc32fd'}
                ).json()['output']['nsfw_score'] >= 0.9)
        punishments = nsfw_settings['punishments']
        role_whitelists = set(eval(nsfw_settings['role_whitelists']).values())
        channel_whitelists = list(eval(nsfw_settings['channel_whitelists']).values())
        if nsfw.count(True) >= 1 and str(message.channel.id) not in channel_whitelists and len(
                set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
            handle([message], punishments, nsfw_settings, 'sending a message with NSFW content')


        if 'hatespeech' in settings:
            hate_settings = settings['hatespeech']
        else:
            hate_settings = default_settings['hatespeech']
        punishments = hate_settings['punishments']
        role_whitelists = set(eval(hate_settings['role_whitelists']).values())
        channel_whitelists = list(eval(hate_settings['channel_whitelists']).values())
        hateful = 'Hate Speech' in hate_speech_detection(check(message.content.lower()))
        if hateful and str(message.channel.id) not in channel_whitelists and len(set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
            handle([message], punishments, hate_settings, 'sending a message with hate speech')

        if 'badwords' in settings:
            punishments = msg_punishments(message.author, settings['badwords']['categories'], message, message.content, 'word')
        else:
            punishments = msg_punishments(message.author, default_settings['badwords'], message, message.content, 'word')
        if punishments['delete']:
            final_punishments['deletes'].append(message)
        if punishments['mute'] > 0:
            final_punishments['mute'] += punishments['mute']
            final_punishments['mute_reason'].append(to_punish_reason(punishments['mute_words'], 'word'))
        if punishments['warn'] > 0:
            final_punishments['warn'] += punishments['warn']
            final_punishments['warn_reason'].append(to_punish_reason(punishments['warn_words'], 'word'))
        if punishments['kick']:
            final_punishments['kick'] = True
            final_punishments['warn_reason'].append(to_punish_reason(punishments['warn_words'], 'word'))
        if punishments['tempban'] > 0:
            final_punishments['tempban'] += punishments['tempban']
            final_punishments['tempban_reason'].append(to_punish_reason(punishments['tempban_words'], 'word'))
        if punishments['ban']:
            final_punishments['ban'] = True
            final_punishments['ban_reason'].append(to_punish_reason(punishments['ban_words'], 'word'))

        if 'badlinks' in settings:
            punishments = msg_punishments(message.author, settings['badlinks']['categories'], message, message.content, 'link')
        else:
            punishments = msg_punishments(message.author, default_settings['badlinks'], message, message.content, 'link')
        if punishments['delete']:
            final_punishments['deletes'].append(message)
        if punishments['mute'] > 0:
            final_punishments['mute'] += punishments['mute']
            final_punishments['mute_reason'].append(to_punish_reason(punishments['mute_words'], 'word'))
        if punishments['warn'] > 0:
            final_punishments['warn'] += punishments['warn']
            final_punishments['warn_reason'].append(to_punish_reason(punishments['warn_words'], 'word'))
        if punishments['kick']:
            final_punishments['kick'] = True
            final_punishments['warn_reason'].append(to_punish_reason(punishments['warn_words'], 'word'))
        if punishments['tempban'] > 0:
            final_punishments['tempban'] += punishments['tempban']
            final_punishments['tempban_reason'].append(to_punish_reason(punishments['tempban_words'], 'word'))
        if punishments['ban']:
            final_punishments['ban'] = True
            final_punishments['ban_reason'].append(to_punish_reason(punishments['ban_words'], 'word'))

        final_punishments['deletes'] = list(set(final_punishments['deletes']))

    return final_punishments


def msg_punishments(user, categories, message, content, cttype):
    default_punishments = {'delete': False, 'mute':0,'warn':0,'kick':False,'tempban':0,'ban':False, 'mute_words':{}, 'warn_words':{}, 'kick_words':{}, 'tempban_words':{}, 'ban_words':{}}
    if cttype == 'word' and not user.bot:
        for category in categories:
            c = eval(category)
            role_whitelists = set(c['whitelistedRoles'].values())
            channel_whitelists = list((c['whitelistedChannels']).values())
            words = c['words'].keys()
            substring = [word for word in words if c['words'][word] == 'Substring']
            non_substring = [word for word in words if c['words'][word] == 'NoSubstring']
            cat_punishments = c['punishments']
            if str(message.channel.id) not in channel_whitelists and len(set([str(role.id) for role in user.roles]).intersection(role_whitelists)) == 0:
                for word in substring:
                    if word in content:
                        if "Delete message" in cat_punishments:
                            default_punishments['delete'] = True
                        if "Mute" in cat_punishments:
                            default_punishments['mute'] = default_punishments['mute'] + time(c['timeval'], c['timeunit'])
                            if c['title'] not in default_punishments['mute_words']:
                                default_punishments['mute_words'][c['title']] = []
                            default_punishments['mute_words'][c['title']].append(word)
                        if "Warn" in cat_punishments:
                            default_punishments['warn'] = default_punishments['warn'] + c['points']
                            if c['title'] not in default_punishments['warn_words']:
                                default_punishments['warn_words'][c['title']] = []
                            default_punishments['warn_words'][c['title']].append(word)
                        if "Kick" in cat_punishments:
                            default_punishments['kick'] = True
                            if c['title'] not in default_punishments['kick_words']:
                                default_punishments['kick_words'][c['title']] = []
                            default_punishments['kick_words'][c['title']].append(word)
                        if "Tempban" in cat_punishments:
                            default_punishments['tempban'] = default_punishments['tempban'] + time(c['timeval'], c['timeunit'])
                            if c['title'] not in default_punishments['tempban_words']:
                                default_punishments['tempban_words'][c['title']] = []
                            default_punishments['tempban_words'][c['title']].append(word)
                        if "Ban" in cat_punishments:
                            default_punishments['ban'] = True
                            if c['title'] not in default_punishments['ban_words']:
                                default_punishments['ban_words'][c['title']] = []
                            default_punishments['ban_words'][c['title']].append(word)
                for word in non_substring:
                    if f" {word} " in content or content.strip() == word:
                        if "Delete message" in cat_punishments:
                            default_punishments['delete'] = True
                        if "Mute" in cat_punishments:
                            default_punishments['mute'] = default_punishments['mute'] + time(c['timeval'], c['timeunit'])
                            if c['title'] not in default_punishments['mute_words']:
                                default_punishments['mute_words'][c['title']] = []
                            default_punishments['mute_words'][c['title']].append(word)
                        if "Warn" in cat_punishments:
                            default_punishments['warn'] = default_punishments['warn'] + c['points']
                            if c['title'] not in default_punishments['warn_words']:
                                default_punishments['warn_words'][c['title']] = []
                            default_punishments['warn_words'][c['title']].append(word)
                        if "Kick" in cat_punishments:
                            default_punishments['kick'] = True
                            if c['title'] not in default_punishments['kick_words']:
                                default_punishments['kick_words'][c['title']] = []
                            default_punishments['kick_words'][c['title']].append(word)
                        if "Tempban" in cat_punishments:
                            default_punishments['tempban'] = default_punishments['tempban'] + time(c['timeval'], c['timeunit'])
                            if c['title'] not in default_punishments['tempban_words']:
                                default_punishments['tempban_words'][c['title']] = []
                            default_punishments['tempban_words'][c['title']].append(word)
                        if "Ban" in cat_punishments:
                            default_punishments['ban'] = True
                            if c['title'] not in default_punishments['ban_words']:
                                default_punishments['ban_words'][c['title']] = []
                            default_punishments['ban_words'][c['title']].append(word)

    if cttype == 'link' and not user.bot:
        extract = URLExtract()
        found_urls = extract.find_urls(message.content.replace('http', ' http').replace('www.', ' www.'))
        for i in range(len(found_urls)):
            if found_urls[i].startswith('www'):
                found_urls[i] = f"https://{found_urls[i]}"

        for category in categories:
            c = eval(category)
            role_whitelists = set(c['whitelistedRoles'].values())
            channel_whitelists = list((c['whitelistedChannels']).values())
            links = c['words'].keys()
            cat_punishments = c['punishments']
            if str(message.channel.id) not in channel_whitelists and len(set([str(role.id) for role in user.roles]).intersection(role_whitelists)) == 0:
                for link in links:
                    urls = [url for url in found_urls if f".{link}." in url]
                    if len(urls) >= 1:
                        if "Delete message" in cat_punishments:
                            default_punishments['delete'] = True
                        if "Mute" in cat_punishments:
                            default_punishments['mute'] = default_punishments['mute'] + time(c['timeval'], c['timeunit'])
                            if c['title'] not in default_punishments['mute_words']:
                                default_punishments['mute_words'][c['title']] = []
                            default_punishments['mute_words'][c['title']].append(link)
                        if "Warn" in cat_punishments:
                            default_punishments['warn'] = default_punishments['warn'] + c['points']
                            if c['title'] not in default_punishments['warn_words']:
                                default_punishments['warn_words'][c['title']] = []
                            default_punishments['warn_words'][c['title']].append(link)
                        if "Kick" in cat_punishments:
                            default_punishments['kick'] = True
                            if c['title'] not in default_punishments['kick_words']:
                                default_punishments['kick_words'][c['title']] = []
                            default_punishments['kick_words'][c['title']].append(link)
                        if "Tempban" in cat_punishments:
                            default_punishments['tempban'] = default_punishments['tempban'] + time(c['timeval'], c['timeunit'])
                            if c['title'] not in default_punishments['tempban_words']:
                                default_punishments['tempban_words'][c['title']] = []
                            default_punishments['tempban_words'][c['title']].append(link)
                        if "Ban" in cat_punishments:
                            default_punishments['ban'] = True
                            if c['title'] not in default_punishments['ban_words']:
                                default_punishments['ban_words'][c['title']] = []
                            default_punishments['ban_words'][c['title']].append(link)

    return default_punishments


def to_punish_reason(violated, ty):
    wds = []
    string = f'violating {ty} categories: '
    for violate in violated:
        s = ', '.join(violated[violate])
        str_to_add = f"**{violate}**({s})"
        wds.append(str_to_add)
    vlt = ', '.join(wds)
    string += ','.join(wds)
    if vlt != '':
        return string
    else:
        return ''


async def connections():
    global warn_conn
    warn_conn = await asyncpg.create_pool(host='botdb.cjcygiqxnebe.ca-central-1.rds.amazonaws.com', port=5432, user='botworker',password='DiScOrDsTeV3!2#', database='botdb')


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


async def profile_punishments(user, categories, content, type):
    default_punishments = {'delete': False, 'mute':0,'warn':0,'kick':False,'tempban':0,'ban':False, 'mute_words':{}, 'warn_words':{}, 'kick_words':{}, 'tempban_words':{}, 'ban_words':{}}
    if type == 'namestatus':
        for category in categories:
            c = eval(category)
            role_whitelists = set(c['whitelistedRoles'].values())
            words = c['words'].keys()
            substring = [word for word in words if c['words'][word] == 'Substring']
            non_substring = [word for word in words if c['words'][word] == 'NoSubstring']
            cat_punishments = c['punishments']
            if len(set([str(role.id) for role in user.roles]).intersection(role_whitelists)) == 0:
                for word in substring:
                    if word in content:
                        if "Mute" in cat_punishments:
                            default_punishments['mute'] = default_punishments['mute'] + time(c['timeval'], c['timeunit'])
                            if c['title'] not in default_punishments['mute_words']:
                                default_punishments['mute_words'][c['title']] = []
                            default_punishments['mute_words'][c['title']].append(word)
                        if "Warn" in cat_punishments:
                            default_punishments['warn'] = default_punishments['warn'] + c['points']
                            if c['title'] not in default_punishments['warn_words']:
                                default_punishments['warn_words'][c['title']] = []
                            default_punishments['warn_words'][c['title']].append(word)
                        if "Kick" in cat_punishments:
                            default_punishments['kick'] = True
                            if c['title'] not in default_punishments['kick_words']:
                                default_punishments['kick_words'][c['title']] = []
                            default_punishments['kick_words'][c['title']].append(word)
                        if "Tempban" in cat_punishments:
                            default_punishments['tempban'] = default_punishments['tempban'] + time(c['timeval'], c['timeunit'])
                            if c['title'] not in default_punishments['tempban_words']:
                                default_punishments['tempban_words'][c['title']] = []
                            default_punishments['tempban_words'][c['title']].append(word)
                        if "Ban" in cat_punishments:
                            default_punishments['ban'] = True
                            if c['title'] not in default_punishments['ban_words']:
                                default_punishments['ban_words'][c['title']] = []
                            default_punishments['ban_words'][c['title']].append(word)
                for word in non_substring:
                    if f" {word} " in content or content.strip() == word:
                        if "Mute" in cat_punishments:
                            default_punishments['mute'] = default_punishments['mute'] + time(c['timeval'], c['timeunit'])
                            if c['title'] not in default_punishments['mute_words']:
                                default_punishments['mute_words'][c['title']] = []
                            default_punishments['mute_words'][c['title']].append(word)
                        if "Warn" in cat_punishments:
                            default_punishments['warn'] = default_punishments['warn'] + c['points']
                            if c['title'] not in default_punishments['warn_words']:
                                default_punishments['warn_words'][c['title']] = []
                            default_punishments['warn_words'][c['title']].append(word)
                        if "Kick" in cat_punishments:
                            default_punishments['kick'] = True
                            if c['title'] not in default_punishments['kick_words']:
                                default_punishments['kick_words'][c['title']] = []
                            default_punishments['kick_words'][c['title']].append(word)
                        if "Tempban" in cat_punishments:
                            default_punishments['tempban'] = default_punishments['tempban'] + time(c['timeval'], c['timeunit'])
                            if c['title'] not in default_punishments['tempban_words']:
                                default_punishments['tempban_words'][c['title']] = []
                            default_punishments['tempban_words'][c['title']].append(word)
                        if "Ban" in cat_punishments:
                            default_punishments['ban'] = True
                            if c['title'] not in default_punishments['ban_words']:
                                default_punishments['ban_words'][c['title']] = []
                            default_punishments['ban_words'][c['title']].append(word)

    if type == 'nick':
        for category in categories:
            c = eval(category)
            role_whitelists = set(c['whitelistedRoles'].values())
            words = c['words'].keys()
            substring = [word for word in words if c['words'][word] == 'Substring']
            non_substring = [word for word in words if c['words'][word] == 'NoSubstring']
            cat_punishments = c['punishments']
            if len(set([str(role.id) for role in user.roles]).intersection(role_whitelists)) == 0:
                for word in substring:
                    if word in content:
                        if "Mute" in cat_punishments:
                            default_punishments['mute'] = default_punishments['mute'] + time(c['timeval'], c['timeunit'])
                            if c['title'] not in default_punishments['mute_words']:
                                default_punishments['mute_words'][c['title']] = []
                            default_punishments['mute_words'][c['title']].append(word)
                        if "Warn" in cat_punishments:
                            default_punishments['warn'] = default_punishments['warn'] + c['points']
                            if c['title'] not in default_punishments['warn_words']:
                                default_punishments['warn_words'][c['title']] = []
                            default_punishments['warn_words'][c['title']].append(word)
                        if "Kick" in cat_punishments:
                            default_punishments['kick'] = True
                            if c['title'] not in default_punishments['kick_words']:
                                default_punishments['kick_words'][c['title']] = []
                            default_punishments['kick_words'][c['title']].append(word)
                        if "Tempban" in cat_punishments:
                            default_punishments['tempban'] = default_punishments['tempban'] + time(c['timeval'], c['timeunit'])
                            if c['title'] not in default_punishments['tempban_words']:
                                default_punishments['tempban_words'][c['title']] = []
                            default_punishments['tempban_words'][c['title']].append(word)
                        if "Ban" in cat_punishments:
                            default_punishments['ban'] = True
                            if c['title'] not in default_punishments['ban_words']:
                                default_punishments['ban_words'][c['title']] = []
                            default_punishments['ban_words'][c['title']].append(word)
                for word in non_substring:
                    if f" {word} " in content or content.strip() == word:
                        if "Mute" in cat_punishments:
                            default_punishments['mute'] = default_punishments['mute'] + time(c['timeval'], c['timeunit'])
                            if c['title'] not in default_punishments['mute_words']:
                                default_punishments['mute_words'][c['title']] = []
                            default_punishments['mute_words'][c['title']].append(word)
                        if "Warn" in cat_punishments:
                            default_punishments['warn'] = default_punishments['warn'] + c['points']
                            if c['title'] not in default_punishments['warn_words']:
                                default_punishments['warn_words'][c['title']] = []
                            default_punishments['warn_words'][c['title']].append(word)
                        if "Kick" in cat_punishments:
                            default_punishments['kick'] = True
                            if c['title'] not in default_punishments['kick_words']:
                                default_punishments['kick_words'][c['title']] = []
                            default_punishments['kick_words'][c['title']].append(word)
                        if "Tempban" in cat_punishments:
                            default_punishments['tempban'] = default_punishments['tempban'] + time(c['timeval'], c['timeunit'])
                            if c['title'] not in default_punishments['tempban_words']:
                                default_punishments['tempban_words'][c['title']] = []
                            default_punishments['tempban_words'][c['title']].append(word)
                        if "Ban" in cat_punishments:
                            default_punishments['ban'] = True
                            if c['title'] not in default_punishments['ban_words']:
                                default_punishments['ban_words'][c['title']] = []
                            default_punishments['ban_words'][c['title']].append(word)

    return default_punishments


async def handle_send(member, embed):
    try:
        await member.send(embed=embed)
    except:
        print('a')


class Automod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None



    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is not None:
            general = await warn_conn.fetchrow('SELECT * FROM automodgeneral WHERE guild_id=$1', message.guild.id)
            if general is not None:
                wh = dict(general)
                channel_whitelists = list(set(eval(wh['channel_whitelists']).values()))
                role_whitelists = list(set(eval(wh['role_whitelists']).values()))
            else:
                channel_whitelists = {}
                role_whitelists = {}
            if str(message.channel.id) not in channel_whitelists and len(set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                bot_user = f"{self.bot.user.name}#{self.bot.user.discriminator}"
                user = message.author
                guild = message.guild
                punishments = await message_punishments(message, message.guild, self.bot)
                for msg in punishments['deletes']:
                    if msg in self.bot.cached_messages:
                        await msg.delete()
                if punishments['ban']:
                    await handle_send(user, discord.Embed(title=f"You've been banned from {guild}", description=f"**Reason:** {', '.join(punishments['ban_reason'])}\n**Moderator: **{bot_user}", color=0xf54254))
                    await user.ban(delete_message_days=0)
                    await log_ban(self.bot, guild, user, ', '.join(punishments['ban_reason']), self.bot, warn_conn)

                if punishments['warn'] > 0:
                    await handle_send(user, discord.Embed(title=f"You've been warned in {guild}", description=f"**Points added:** {punishments['warn']}\n**Reason:** {', '.join(punishments['warn_reason'])}\n**Moderator: **{bot_user}", color=0xf54254))
                    await warn(self.bot, user, guild, punishments['warn'], warn_conn, ', '.join(punishments['warn_reason']), self.bot)

                if punishments['tempban'] > 0:
                    reason = ', '.join(punishments['tempban_reason'])
                    await handle_send(user, discord.Embed(title=f"You've been temporarily banned from {guild}", description=f"**Duration: **{t(punishments['tempban'])}\n**Reason:** {reason}\n**Moderator: **{bot_user}", color=0xf54254))
                    await user.ban(reason=reason, delete_message_days=0)
                    await log_tempban(self.bot, guild, user, t(punishments['tempban']), reason, self.bot, warn_conn)
                    await asyncio.sleep(punishments['tempban'])
                    await user.unban()
                if punishments['kick']:
                    await handle_send(user, discord.Embed(title=f"You've been kicked from {guild}", description=f"**Reason:** {', '.join(punishments['kick_reason'])}\n**Moderator: **{bot_user}", color=0xf54254))
                    await user.kick(reason=', '.join(punishments['kick_reason']))
                if punishments['mute'] > 0:
                    reason = ', '.join(punishments['mute_reason'])
                    await user.timeout(
                        until=datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=punishments['mute']))
                    await handle_send(user, discord.Embed(title=f"You've been muted in {guild}", description=f"**Duration:** {t(punishments['mute'])}\n**Reason:** {reason}\n**Moderator: **{bot_user}", color=0xf54254))

                    await log_mute(self.bot, guild, user, f"{t(punishments['mute'])}", reason, self.bot, warn_conn)

    @commands.Cog.listener()
    async def on_presence_update(self,before,after):
        settings = await warn_conn.fetchrow('SELECT * FROM badstatuses where guild_id=$1', after.guild.id)
        general = await warn_conn.fetchrow('SELECT * FROM automodgeneral WHERE guild_id=$1', after.guild.id)
        if general is not None:
            wh = dict(general)
            role_whitelists = list(set(eval(wh['role_whitelists']).values()))
        else:
            role_whitelists = {}
        if len(set([str(role.id) for role in after.roles]).intersection(role_whitelists)) == 0:
            bot_user = f"{self.bot.user.name}#{self.bot.user.discriminator}"
            guild = after.guild
            if len([activity for activity in after.activities if isinstance(activity, discord.CustomActivity)]) > 0:
                new_status = [activity for activity in after.activities if isinstance(activity, discord.CustomActivity)][0].name
                if settings is not None:
                    categories = dict(settings)['categories']
                else:
                    categories = default_settings['badstatuses']
                punishments = await profile_punishments(after, categories, check(new_status.lower().strip()),'namestatus')
                if punishments['ban']:
                    await handle_send(after,
                                      embed=discord.Embed(title=f"You've been banned from {after.guild}",
                                                          description=f"**Reason:** {to_punish_reason(punishments['ban_words'], 'status')}\n**Moderator: **{bot_user}", color=0xf54254))
                    await after.ban(reason=f"Automatic action for {to_punish_reason(punishments['ban_words'], 'status')}")
                    await log_ban(self.bot, guild, after, to_punish_reason(punishments['ban_words'], 'status'), self.bot, warn_conn)


                if punishments['warn'] > 0:
                    await handle_send(after, embed=discord.Embed(title=f"You've been warned in {after.guild}",
                                                                 description=f"**Points added:** {punishments['warn']}\n**Reason:** Automatic action for {to_punish_reason(punishments['warn_words'], 'status')}\n**Moderator: **{bot_user}", color=0xf54254))
                    await warn(self.bot, after, after.guild, punishments['warn'], warn_conn,
                               to_punish_reason(punishments['warn_words'], 'status'), self.bot)

                if punishments['tempban'] > 0:
                    await handle_send(after, embed=discord.Embed(title=f"You've been temporarily banned from {after.guild}", description=f"**Duration: **{t(punishments['tempban'])}\n**Reason:** Automatic action for {to_punish_reason(punishments['tempban_words'], 'status')}\n**Moderator: **{bot_user}", color=0xf54254))
                    await after.ban(
                        reason=f"Automatic action for {to_punish_reason(punishments['tempban_words'], 'status')}")


                    await log_tempban(self.bot, after.guild, after, t(punishments['tempban']),
                                      f"Automatic action for {to_punish_reason(punishments['tempban_words'], 'status')}", self.bot, warn_conn)
                    await asyncio.sleep(punishments['tempban'] - 10)
                    await after.unban()

                if punishments['kick']:
                    await handle_send(after,
                                      embed=discord.Embed(title=f"You've been kicked from {after.guild}",
                                                          description=f"**Reason:** Automatic action for {to_punish_reason(punishments['kick_words'], 'status')}\n**Moderator: **{bot_user}", color=0xf54254))
                    await after.kick(
                        reason=f"Automatic action for {to_punish_reason(punishments['kick_words'], 'status')}")

                if punishments['mute'] > 0:
                    await after.timeout(
                        until=datetime.datetime.now() + datetime.timedelta(seconds=punishments['status']))
                    await handle_send(after, embed=discord.Embed(title=f"You've been muted in {after.guild}",
                                                             description=f"**Duration:** {t(punishments['mute'])}\n**Reason:** Automatic action for {to_punish_reason(punishments['mute_words'], 'status')}\n**Moderator: **{bot_user}", color=0xf54254))

                    await log_mute(self.bot, after.guild, after, t(punishments['mute']),
                                   f"Automatic action for {to_punish_reason(punishments['mute_words'], 'status')}", self.bot, warn_conn)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        bot_user = f"{self.bot.user.name}#{self.bot.user.discriminator}"
        if before.name != after.name:
            new_name = after.name
            for guild in after.mutual_guilds:
                member = guild.get_member(after.id)
                guild_id = guild.id
                settings = await warn_conn.fetchrow('SELECT * FROM badstatuses where guild_id=$1', guild_id)
                general = await warn_conn.fetchrow('SELECT * FROM automodgeneral WHERE guild_id=$1', after.guild.id)
                if general is not None:
                    wh = dict(general)
                    role_whitelists = list(set(eval(wh['role_whitelists']).values()))
                else:
                    role_whitelists = {}
                if len(set([str(role.id) for role in member.roles]).intersection(role_whitelists)) == 0:
                    if settings is not None:
                        categories = dict(settings)['categories']
                    else:
                        categories = default_settings['badnames']
                    punishments = await profile_punishments(member, categories, check(new_name.lower().strip()), 'namestatus')
                    if punishments['ban']:
                        await handle_send(member,
                                          embed=discord.Embed(title=f"You've been banned from {guild}",
                                                              description=f"**Reason:** {to_punish_reason(punishments['ban_words'], 'username')}\n**Moderator: **{bot_user}", color=0xf54254))
                        await member.ban(
                            reason=f"Automatic action for {to_punish_reason(punishments['ban_words'], 'username')}")
                        await log_ban(self.bot, guild, after, to_punish_reason(punishments['ban_words'], 'username'),
                                      self.bot, warn_conn)


                    if punishments['warn'] > 0:
                        await handle_send(member, embed=discord.Embed(title=f"You've been warned in {guild}",
                                                                      description=f"**Points added:** {punishments['warn']}\n**Reason:** Automatic action for {to_punish_reason(punishments['warn_words'], 'username')}\n**Moderator: **{bot_user}", color=0xf54254))
                        await warn(self.bot, member, guild, punishments['warn'], warn_conn,
                                   to_punish_reason(punishments['warn_words'], 'username'), self.bot)

                    if punishments['tempban'] > 0:
                        await handle_send(member,
                                          embed=discord.Embed(title=f"You've been temporarily banned from {guild}",
                                                              description=f"**Duration: **{t(punishments['tempban'])}\n**Reason:** Automatic action for {to_punish_reason(punishments['tempban_words'], 'username')}\n**Moderator: **{bot_user}", color=0xf54254))

                        await member.ban(
                            reason=f"Automatic action for {to_punish_reason(punishments['tempban_words'], 'username')}")

                        await log_tempban(self.bot, guild, member, t(punishments['tempban']),
                                          f"Automatic action for {to_punish_reason(punishments['tempban_words'], 'username')}", self.bot, warn_conn)
                        await asyncio.sleep(punishments['tempban'] - 10)
                        await member.unban()
                    if punishments['kick']:
                        await handle_send(member,
                                          embed=discord.Embed(title=f"You've been kicked from {guild}",
                                                              description=f"**Reason:** Automatic action for {to_punish_reason(punishments['kick_words'], 'username')}\n**Moderator: **{bot_user}", color=0xf54254))
                        await member.kick(
                            reason=f"Automatic action for {to_punish_reason(punishments['kick_words'], 'username')}")

                    if punishments['mute'] > 0:
                        await member.timeout(
                            until=datetime.datetime.now() + datetime.timedelta(seconds=punishments['mute']))

                        await handle_send(member, embed=discord.Embed(title=f"You've been muted in {guild}",
                                                              description=f"**Duration:** {t(punishments['mute'])}\n**Reason:** Automatic action for {to_punish_reason(punishments['mute_words'], 'username')}\n**Moderator: **{bot_user}", color=0xf54254))


                        await log_mute(self.bot, guild, member, t(punishments['mute']),
                                       f"Automatic action for {to_punish_reason(punishments['mute_words'], 'username')}", self.bot, warn_conn)

        if before.avatar != after.avatar:
            for guild in after.mutual_guilds:
                member = guild.get_member(after.id)
                guild_id = guild.id
                nsfw_settings = await warn_conn.fetchrow('SELECT * FROM nsfwpfp WHERE guild_id=$1', guild_id)
                if nsfw_settings is not None:
                    nsfw_pfp_settings = dict(nsfw_settings)
                else:
                    nsfw_pfp_settings = default_settings['nsfwpfp']
                role_whitelists = set(eval(nsfw_pfp_settings['whitelistedRoles']).values())
                if requests.post("https://api.deepai.org/api/nsfw-detector",data={'image': str(after.avatar),},headers={'api-key': '0c25ca40-f09f-45d2-8546-8bd867cc32fd'}).json()['output']['nsfw_score'] >= 0.9 and len(set([str(role.id) for role in member.roles]).intersection(role_whitelists)) == 0:
                    await punish_nsfw(self.bot,member,guild,nsfw_pfp_settings['punishments'],nsfw_pfp_settings,warn_conn,'having a NSFW avatar')

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        settings = await warn_conn.fetchrow('SELECT * FROM badnicks where guild_id=$1', after.guild.id)
        general = await warn_conn.fetchrow('SELECT * FROM automodgeneral WHERE guild_id=$1', after.guild.id)
        if general is not None:
            wh = dict(general)
            role_whitelists = list(set(eval(wh['role_whitelists']).values()))
        else:
            role_whitelists = {}
        if len(set([str(role.id) for role in after.roles]).intersection(role_whitelists)) == 0:
            bot_user = f"{self.bot.user.name}#{self.bot.user.discriminator}"
            if before.nick != after.nick:
                new_nick = after.nick
                guild_id = after.guild.id
                if settings is not None:
                    categories = dict(settings)['categories']
                else:
                    categories = default_settings['badnicks']
                punishments = await profile_punishments(after, categories, check(new_nick.lower().strip()), 'nick')
                if punishments['ban']:
                    await handle_send(after,
                                      embed=discord.Embed(title=f"You've been banned from {after.guild}",
                                                          description=f"**Reason:** {to_punish_reason(punishments['ban_words'], 'nickname')}\n**Moderator: ** {bot_user}", color=0xf54254))
                    await after.ban(
                        reason=f"Automatic action for {to_punish_reason(punishments['ban_words'], 'nickname')}")
                    await log_ban(self.bot, after.guild, after, to_punish_reason(punishments['ban_words'], 'nickname'), self.bot, warn_conn)


                if punishments['warn'] > 0:
                    await after.edit(nick=after.name)
                    await handle_send(after, embed=discord.Embed(title=f"You've been warned in {after.guild}",
                                                                 description=f"**Points added:** {punishments['warn']}\n**Reason:** Automatic action for {to_punish_reason(punishments['warn_words'], 'nickname')}\n**Moderator: ** {bot_user}", color=0xf54254))
                    await warn(self.bot, after, after.guild, punishments['warn'], warn_conn,
                               to_punish_reason(punishments['warn_words'], 'nickname'), self.bot)

                if punishments['tempban'] > 0:
                    await handle_send(after,
                                      embed=discord.Embed(title=f"You've been temporarily banned from {after.guild}",
                                                          description=f"**Duration: **{t(punishments['tempban'])}\n**Reason:** Automatic action for {to_punish_reason(punishments['tempban_words'], 'nickname')}\n**Moderator: ** {bot_user}", color=0xf54254))
                    await after.ban(
                        reason=f"Automatic action for {to_punish_reason(punishments['tempban_words'], 'nickname')}")
                    await log_tempban(self.bot, after.guild, after, t(punishments['tempban']),
                                      f"Automatic action for {to_punish_reason(punishments['tempban_words'], 'nickname')}", self.bot, warn_conn)
                    await asyncio.sleep(punishments['tempban'] - 10)
                    await after.unban()
                if punishments['kick']:
                    await handle_send(after,
                                      embed=discord.Embed(title=f"You've been kicked from {after.guild}",
                                                          description=f"**Reason:** Automatic action for {to_punish_reason(punishments['kick_words'], 'nickname')}\n**Moderator: **{bot_user}", color=0xf54254))
                    await after.kick(
                        reason=f"Automatic action for {to_punish_reason(punishments['kick_words'], 'nickname')}")
                if punishments['mute'] > 0:
                    await after.edit(nick=after.name)
                    await after.timeout(
                        until=datetime.datetime.now() + datetime.timedelta(seconds=punishments['status']))
                    await handle_send(after, embed=discord.Embed(title=f"You've been muted in {after.guild}",
                                                             description=f"**Duration:** {t(punishments['mute'])}\n**Reason:** Automatic action for {to_punish_reason(punishments['mute_words'], 'nickname')}\n**Moderator: **{bot_user}", color=0xf54254))

                    await log_mute(self.bot, after.guild, after, t(punishments['mute']),
                                   f"Automatic action for {to_punish_reason(punishments['mute_words'], 'nickname')}", self.bot, warn_conn)

def setup(bot):
    bot.add_cog(Automod(bot))


asyncio.get_event_loop().run_until_complete(connections())