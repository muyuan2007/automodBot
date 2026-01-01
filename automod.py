import datetime
import gc
import json
from collections import deque
from itertools import islice
import emojis
import psutil
from urlextract import URLExtract
import discord
from discord.ext import commands, tasks
import asyncio
from features.punishing import warn, log_mute, log_ban, tempban
from features.spellchecking import remove_ignored, check_for_word
import asyncpg
import re
from difflib import SequenceMatcher as sm

dbpass = 'mysecretpassword'

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

s = {'badlinks': 'Blacklisted links', 'badwords': 'Blacklisted words', 'badnicks': 'Blacklisted nicknames',
     'badnames': 'Blacklisted usernames', 'badstatuses': 'Blacklisted custom statuses'}

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


async def no_sub(text, target):  # done
    text_lower = text.lower()
    target_lower = target.lower()
    return f" {text_lower} " in target_lower or target_lower.strip() == text_lower or target_lower.strip().endswith(
        f" {text_lower}") or target_lower.strip().startswith(f"{text_lower} ")


d = {}

with open('tk.json', 'r') as f:
    info = json.load(f)['db']
    d.update(info)

messages_cache = {}


async def total_s(msg1, msg2):  # done
    return (msg1.created_at - msg2.created_at).total_seconds()


async def msg_within_time(arr, low, high, now, limit):  # done
    most_recent_msg = arr[0]

    while high >= low:
        mid = (high + low) // 2
        mid_total_s = await total_s(most_recent_msg, arr[mid])

        # If element is present at the middle itself
        if high == low:
            return mid

        if mid_total_s < limit <= await total_s(most_recent_msg, arr[mid + 1]):
            return mid

        # If element is smaller than mid, then it can only be present in left subarray
        elif mid_total_s > limit:
            high = mid - 1

        # Else the element can only be present in right subarray
        else:
            low = mid + 1

    return -1


async def get_default_emoji(sentence):  # done
    different_emojis = list(emojis.get(sentence))
    emoji_count = 0
    for emoji in different_emojis:
        emoji_count += sentence.count(emoji)

    return emoji_count


async def get_message_emojis(m: discord.Message):  # done
    """ Returns a list of custom emojis in a message. """
    emojis = re.findall('<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>', m.content)
    return len(emojis) + await get_default_emoji(m.content)


async def remove_emojis(text):
    s = re.sub('<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>', '', await remove_emoji(text))
    return s


emoj = re.compile("["
                  u"\U0001F600-\U0001F64F"  # emoticons
                  u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                  u"\U0001F680-\U0001F6FF"  # transport & map symbols
                  u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                  u"\U000024C2-\U0001F251"
                  u"\U0001f926-\U0001f937"
                  u"\U00010000-\U0010ffff"
                  u"\u2600-\u2B55"
                  u"\u200d"
                  u"\u23cf"
                  u"\u23e9"
                  u"\u231a"
                  u"\ufe0f"  # dingbats
                  u"\u3030"
                  "]+", re.UNICODE)


async def remove_emoji(data):
    return re.sub(emoj, '', data)


async def no_punc(string):
    return string.translate(str.maketrans('', '', '"#$%&*+,:;<=>?@[\\]^_`{|}~'))


extract = URLExtract()


async def get_feature(messages, ty):  # done
    features = 0
    if ty == 'mentions':
        for message in messages:
            features += len(re.findall('<@\d{18}>', message.content)) + len(re.findall('<@\d{19}>', message.content))
    if ty == 'stickers':
        for message in messages:
            features += len(message.stickers)
    if ty == 'attachments':
        for message in messages:
            features += int(bool(len(message.attachments)))
    if ty == 'links':
        for message in messages:
            urls = extract.find_urls(message.content.replace('http', ' http').replace('www.', ' www.'))
            for url in urls:
                if url.startswith("http") or url.startswith("www."):
                    features += 1
    if ty == 'emojis':
        for message in messages:
            features += await get_message_emojis(message)

    return features


async def similarity(messages):
    match_ratios = []
    if messages[0].content != '':
        for i in range(1, len(messages)):
            match_ratios.append(sm(None, messages[0].content.lower(), messages[i].content.lower()).ratio())

    return match_ratios


def similar(n):
    return n >= 0.85


async def time(amount, units):
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


async def add_message(message, settings):  # done
    channel = await get_actual_channel(message)
    channel_id = channel.id
    if channel_id not in messages_cache:
        messages_cache[channel_id] = deque(maxlen=120)
    messages_cache[channel_id].appendleft(message)


async def msg_automod(bot, guild_id):
    message_tables = ['automodgeneral', 'messagespam', 'emojispam', 'mentionspam', 'stickerspam', 'attachmentspam',
                      'linkspam',
                      'duplicatecharacters', 'duplicatemessages', 'linebreaks', 'toomanycaps', 'invites', 'selfbot',
                      'badwords', 'badlinks']

    am_settings = await bot.conn.fetchrow(f'SELECT * FROM msg_automod WHERE guild_id=$1', guild_id)

    if am_settings is not None:
        return {table: eval(dict(am_settings)[table].replace("null", "0")) for table in message_tables}
    else:
        return {table: default_settings[table] for table in message_tables}


async def change_words(words):  # done
    unique_words = set()
    for word in words:
        words_to_remove = set()
        substring = 0
        for found_word in unique_words:
            if found_word.lower() in word.lower():
                substring += 1
            if word.lower() in found_word.lower():
                words_to_remove.add(found_word.lower())
        if substring == 0:
            unique_words.add(word)
        unique_words = unique_words.difference(words_to_remove)

    return list(unique_words)


async def remove_duplicates(words):
    return list(set(eval(str(words).lower())))


async def get_actual_channel(message):
    return message.channel if not isinstance(message.channel, discord.threads.Thread) else message.channel.parent


async def message_punishments(message, guild, bot):
    final_punishments = {'mute': 0, 'warn': 0, 'kick': False, 'tempban': 0, 'ban': False, 'mute_reason': [],
                         'warn_reason': [], 'kick_reason': [], 'tempban_reason': [], 'ban_reason': [], 'deletes': []}

    async def handle(mesgs, punish, table, reason):  # done
        if "Delete message" in punish:
            final_punishments['deletes'] += mesgs
        if "Ban" in punish:
            final_punishments['ban'] = True
            final_punishments['ban_reason'].append(reason)
        if "Warn" in punish and table['points'] not in [None, 0]:
            final_punishments['warn'] += table['points']
            final_punishments['warn_reason'].append(reason)
        if "Tempban" in punish:
            final_punishments['tempban'] += await time(table['timeval'], table['timeunit'])
            final_punishments['tempban_reason'].append(reason)
        if "Kick" in punish:
            final_punishments['kick'] = True
            final_punishments['kick_reason'].append(reason)
        if "Mute" in punish:
            final_punishments['mute'] += await time(table['timeval'], table['timeunit'])
            final_punishments['mute_reason'].append(reason)

    settings = await msg_automod(bot, message.guild.id)

    whitelisted_channels_all = list(settings['automodgeneral']['channel_whitelists'].values())
    whitelisted_roles_all = list(settings['automodgeneral']['role_whitelists'].values())

    if "ignored_words" in list(settings['automodgeneral'].keys()):
        ignored_words = settings['automodgeneral']["ignored_words"]
    else:
        ignored_words = []

    if "caps_threshold" in list(settings['automodgeneral'].keys()):
        caps_threshold = settings['automodgeneral']["caps_threshold"]
    else:
        caps_threshold = 120

    await add_message(message, settings)

    channel = await get_actual_channel(message)

    if guild is not None and str(channel.id) not in whitelisted_channels_all and len(
            set([str(role.id) for role in message.author.roles]).intersection(whitelisted_roles_all)) == 0:
        global messages_cache
        cache = messages_cache[channel.id]

        message_spam_settings = settings['messagespam']
        if message_spam_settings['maxes'][1] not in [None, 0] and message_spam_settings['maxes'][0] not in [None, 0, 1]:
            ms = await msg_within_time(cache, 0, len(cache) - 1, message.created_at, message_spam_settings['maxes'][1]) + 1
            punishments = message_spam_settings['punishments']
            role_whitelists = list(set(message_spam_settings['role_whitelists'].values()))
            channel_whitelists = list(message_spam_settings['channel_whitelists'].values())
            limit = message_spam_settings['maxes'][0]

            messages = [msg for msg in islice(cache, 0, ms) if msg.author == message.author]
            if len(messages) >= limit and str(channel.id) not in channel_whitelists and len(
                    set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                await handle(messages, punishments, message_spam_settings,
                             f"sending messages too quickly: {len(messages)} messages in {message_spam_settings['maxes'][1]} seconds")

        mention_spam_settings = settings['mentionspam']
        if mention_spam_settings['maxes'][1] not in [None, 0] and mention_spam_settings['maxes'][0] not in [None, 0, 1]:
            me = await msg_within_time(cache, 0, len(cache) - 1, message.created_at, mention_spam_settings['maxes'][1]) + 1
            punishments = mention_spam_settings['punishments']
            role_whitelists = set(mention_spam_settings['role_whitelists'].values())
            channel_whitelists = list(mention_spam_settings['channel_whitelists'].values())

            limit = mention_spam_settings['maxes'][0]
            messages = [msg for msg in islice(cache, 0, me) if msg.author == message.author]
            mention_count = await get_feature(messages, 'mentions')
            msgs_channels = set([await get_actual_channel(msg) for msg in messages])
            if mention_count >= limit and not len(
                    msgs_channels.intersection(set(channel_whitelists))) == len(msgs_channels) and len(
                set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                await handle(messages, punishments, mention_spam_settings,
                             f"sending mentions too quickly: {mention_count} mentions in {mention_spam_settings['maxes'][1]} seconds")

        attach_spam_settings = settings['attachmentspam']
        if attach_spam_settings['maxes'][1] not in [None, 0] and attach_spam_settings['maxes'][0] not in [None, 0, 1]:
            at = await msg_within_time(cache, 0, len(cache) - 1, message.created_at, attach_spam_settings['maxes'][1]) + 1
            punishments = attach_spam_settings['punishments']
            role_whitelists = set(attach_spam_settings['role_whitelists'].values())
            channel_whitelists = list(attach_spam_settings['channel_whitelists'].values())

            limit = attach_spam_settings['maxes'][0]
            messages = [msg for msg in islice(cache, 0, at) if msg.author == message.author]
            att_count = await get_feature(messages, 'attachments')
            if att_count >= limit and str(
                    channel.id) not in channel_whitelists and len(
                set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                await handle(messages, punishments, attach_spam_settings,
                         f"sending attachments too quickly: {att_count} attachments in {attach_spam_settings['maxes'][1]} seconds")

        link_spam_settings = settings['linkspam']
        if link_spam_settings['maxes'][1] not in [None, 0] and link_spam_settings['maxes'][0] not in [None, 0, 1]:
            ln = await msg_within_time(cache, 0, len(cache) - 1, message.created_at, link_spam_settings['maxes'][1]) + 1
            punishments = link_spam_settings['punishments']
            role_whitelists = set(link_spam_settings['role_whitelists'].values())
            channel_whitelists = list(link_spam_settings['channel_whitelists'].values())
            limit = link_spam_settings['maxes'][0]
            messages = [msg for msg in islice(cache, 0, ln) if msg.author == message.author]
            link_count = await get_feature(messages, 'links')
            if link_count >= limit and str(
                    channel.id) not in channel_whitelists and len(
                set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                await handle(messages, punishments, link_spam_settings,
                             f"sending links too quickly: {link_count} links in {link_spam_settings['maxes'][1]} seconds")

        sticker_spam_settings = settings['stickerspam']
        if sticker_spam_settings['maxes'][1] not in [None, 0] and sticker_spam_settings['maxes'][0] not in [None, 0, 1]:
            st = await msg_within_time(cache, 0, len(cache) - 1, message.created_at, sticker_spam_settings['maxes'][1]) + 1
            punishments = sticker_spam_settings['punishments']
            role_whitelists = set(sticker_spam_settings['role_whitelists'].values())
            channel_whitelists = list(sticker_spam_settings['channel_whitelists'].values())
            limit = sticker_spam_settings['maxes'][0]
            messages = [msg for msg in islice(cache, 0, st) if msg.author == message.author]
            sticker_count = await get_feature(messages, 'stickers')
            if sticker_count >= limit and str(
                    channel.id) not in channel_whitelists and len(
                set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                await handle(messages, punishments, sticker_spam_settings,
                                 f"sending stickers too quickly: {sticker_count} stickers in {sticker_spam_settings['maxes'][1]} seconds")

        emoji_spam_settings = settings['emojispam']
        if emoji_spam_settings['maxes'][1] not in [None, 0] and emoji_spam_settings['maxes'][0] not in [None, 0, 1]:
            em = await msg_within_time(cache, 0, len(cache) - 1, message.created_at, emoji_spam_settings['maxes'][1]) + 1
            punishments = emoji_spam_settings['punishments']
            role_whitelists = set(emoji_spam_settings['role_whitelists'].values())
            channel_whitelists = list(emoji_spam_settings['channel_whitelists'].values())

            limit = emoji_spam_settings['maxes'][0]
            messages = [msg for msg in islice(cache, 0, em) if msg.author == message.author]
            emoji_count = await get_feature(messages, 'emojis')
            if emoji_count >= limit and str(
                     channel.id) not in channel_whitelists and len(
                set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                await handle(messages, punishments, emoji_spam_settings,
                             f"sending emojis too quickly: {emoji_count} emojis in {emoji_spam_settings['maxes'][1]} seconds")

        dupe_msg_settings = settings['duplicatemessages']
        if dupe_msg_settings['top'] not in [0, 1, None]:
            dp = await msg_within_time(cache, 0, len(cache) - 1, message.created_at, 20) + 1
            ret_messages = (list([msg for msg in islice(cache, 0, dp) if
                                  msg.author == message.author])[::-1])[
                           0:dupe_msg_settings['top']]
            msgs = list(islice(ret_messages, dict(dupe_msg_settings)['top']))
            amount_similar = list(map(similar, await similarity(msgs))).count(True) + 1
            punishments = dupe_msg_settings['punishments']
            role_whitelists = set(dupe_msg_settings['role_whitelists'].values())
            channel_whitelists = list(dupe_msg_settings['channel_whitelists'].values())
            if amount_similar >= dict(dupe_msg_settings)['top'] and str(
                    channel.id) not in channel_whitelists and len(
                set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                await handle(msgs, punishments, dupe_msg_settings,
                             f"sending the same message {amount_similar}x in a row")

        caps_settings = settings['toomanycaps']
        content = message.content
        alphas = [c for c in content if c.isalpha()]
        if len(alphas) > 0:
            caps_percent = 100 * sum(1 for c in content if c.isupper()) / (len(alphas))
            if caps_settings['top'] not in [0, None]:
                punishments = caps_settings['punishments']
                role_whitelists = set(caps_settings['role_whitelists'].values())
                channel_whitelists = list(caps_settings['channel_whitelists'].values())

                if caps_percent >= dict(caps_settings)['top'] and len(alphas) >= caps_threshold and str(
                        channel.id) not in channel_whitelists and len(
                    set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                    await handle([message], punishments, caps_settings, f"sending a message with {caps_percent}% caps")

        linebreak_settings = settings['linebreaks']
        if linebreak_settings['top'] not in [0, 1, None]:
            punishments = linebreak_settings['punishments']
            role_whitelists = set(linebreak_settings['role_whitelists'].values())
            channel_whitelists = list(linebreak_settings['channel_whitelists'].values())
            if message.content.count('\n') >= dict(linebreak_settings)['top'] and str(
                    channel.id) not in channel_whitelists and len(
                set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                n = message.content.count('\n')
                await handle([message], punishments, linebreak_settings, f"sending a message with {n} line breaks")

        repeat_char_settings = settings['duplicatecharacters']
        if repeat_char_settings['top'] not in [0, 1, None]:
            punishments = repeat_char_settings['punishments']
            role_whitelists = set(repeat_char_settings['role_whitelists'].values())
            channel_whitelists = list(repeat_char_settings['channel_whitelists'].values())
            top = dict(repeat_char_settings)['top']

            if (
                    bool(re.findall(r"(.+)\1" + '{' + f"{top - 1}," + "}",
                                    message.content.lower().replace(' ', '')))) and str(
                channel.id) not in channel_whitelists and len(
                set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
                await handle([message], punishments, repeat_char_settings,
                             f"sending a message that repeats the same characters {repeat_char_settings['top']}+ times in a "
                             f"row")

        invite_settings = settings['invites']
        punishments = invite_settings['punishments']
        role_whitelists = set(invite_settings['role_whitelists'].values())
        channel_whitelists = list(invite_settings['channel_whitelists'].values())
        if bool(re.findall(r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)/?[a-zA-Z0-9]+/?',
                           message.content)) and str(channel.id) not in channel_whitelists and len(
            set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
            await handle([message], punishments, invite_settings, 'sending a message with invites')

        selfbot_settings = settings['selfbot']
        punishments = selfbot_settings['punishments']
        role_whitelists = set(selfbot_settings['role_whitelists'].values())
        if len([embed for embed in message.embeds if embed.type == 'rich']) >= 1 and await get_feature(
                [message], 'links') == 0 and not message.author.bot and len(
            set([str(role.id) for role in message.author.roles]).intersection(role_whitelists)) == 0:
            await handle([message], punishments, selfbot_settings, 'selfbotting')

        w_punishments = await word_punishments(message.author, settings['badwords']['categories'], message,
                                               message.content,
                                               'word', ignored_words)
        if w_punishments['delete']:
            final_punishments['deletes'].append(message)
        if w_punishments['mute'] > 0:
            final_punishments['mute'] += w_punishments['mute']
            final_punishments['mute_reason'].append(await to_punish_reason(w_punishments['mute_words'], 'word'))
        if w_punishments['warn'] > 0:
            final_punishments['warn'] += w_punishments['warn']
            final_punishments['warn_reason'].append(await to_punish_reason(w_punishments['warn_words'], 'word'))
        if w_punishments['kick']:
            final_punishments['kick'] = True
            final_punishments['warn_reason'].append(await to_punish_reason(w_punishments['kick_words'], 'word'))
        if w_punishments['tempban'] > 0:
            final_punishments['tempban'] += w_punishments['tempban']
            final_punishments['tempban_reason'].append(await to_punish_reason(w_punishments['tempban_words'], 'word'))
        if w_punishments['ban']:
            final_punishments['ban'] = True
            final_punishments['ban_reason'].append(await to_punish_reason(w_punishments['ban_words'], 'word'))

        l_punishments = await word_punishments(message.author, settings['badlinks']['categories'], message,
                                               message.content,
                                               'link', ignored_words)
        if l_punishments['delete']:
            final_punishments['deletes'].append(message)
        if l_punishments['mute'] > 0:
            final_punishments['mute'] += l_punishments['mute']
            final_punishments['mute_reason'].append(await to_punish_reason(l_punishments['mute_words'], 'word'))
        if l_punishments['warn'] > 0:
            final_punishments['warn'] += l_punishments['warn']
            final_punishments['warn_reason'].append(await to_punish_reason(l_punishments['warn_words'], 'word'))
        if l_punishments['kick']:
            final_punishments['kick'] = True
            final_punishments['warn_reason'].append(await to_punish_reason(l_punishments['kick_words'], 'word'))
        if l_punishments['tempban'] > 0:
            final_punishments['tempban'] += l_punishments['tempban']
            final_punishments['tempban_reason'].append(await to_punish_reason(l_punishments['tempban_words'], 'word'))
        if l_punishments['ban']:
            final_punishments['ban'] = True
            final_punishments['ban_reason'].append(await to_punish_reason(l_punishments['ban_words'], 'word'))

    final_punishments['deletes'] = list(set(final_punishments['deletes']))

    return final_punishments


async def word_punishments(user, categories, message, content, cttype, ignored_words):
    remove_zalgo = lambda s: re.sub("(?i)([aeiouy]̈)|[̀-ͯ҉]", "\\1", s)


    default_punishments = {'delete': False, 'mute': 0, 'warn': 0, 'kick': False, 'tempban': 0, 'ban': False,
                           'mute_words': {}, 'warn_words': {}, 'kick_words': {}, 'tempban_words': {}, 'ban_words': {}}

    channel = await get_actual_channel(message)

    if cttype == 'word':
        trimmed_content = re.sub(r'https?:\/\/.*[\r\n]*', '', await remove_ignored(content, ignored_words))
        new_content = (await remove_emojis(await no_punc(remove_zalgo(trimmed_content)))) \
            .replace("\u200b", "").casefold().strip().lower().replace("…", "...")
        for category in categories:
            c = category
            role_whitelists = set(c['whitelistedRoles'].values())
            channel_whitelists = list((c['whitelistedChannels']).values())
            words = c['words']
            cat_punishments = c['punishments']
            if str(channel.id) not in channel_whitelists and len(
                    set([str(role.id) for role in user.roles]).intersection(role_whitelists)) == 0:
                if c['substring'] == 1:
                    words = await change_words(words)
                    for word in words:
                        if await check_for_word(new_content, word, 1):
                            if "Delete message" in cat_punishments:
                                default_punishments['delete'] = True
                            if "Mute" in cat_punishments:
                                default_punishments['mute'] = default_punishments['mute'] + await time(c['timeval'],
                                                                                                       c['timeunit'])
                                if c['title'] not in default_punishments['mute_words']:
                                    default_punishments['mute_words'][c['title']] = [word]
                                else:
                                    default_punishments['mute_words'][c['title']].append(word)
                            if "Warn" in cat_punishments:
                                print('uh oh')
                                default_punishments['warn'] = default_punishments['warn'] + c['points']
                                if c['title'] not in default_punishments['warn_words']:
                                    default_punishments['warn_words'][c['title']] = [word]
                                else:
                                    default_punishments['warn_words'][c['title']].append(word)
                            if "Kick" in cat_punishments:
                                default_punishments['kick'] = True
                                if c['title'] not in default_punishments['kick_words']:
                                    default_punishments['kick_words'][c['title']] = [word]
                                else:
                                    default_punishments['kick_words'][c['title']].append(word)
                            if "Tempban" in cat_punishments:
                                default_punishments['tempban'] = default_punishments['tempban'] + await time(
                                    c['timeval'],
                                    c['timeunit'])
                                if c['title'] not in default_punishments['tempban_words']:
                                    default_punishments['tempban_words'][c['title']] = [word]
                                else:
                                    default_punishments['tempban_words'][c['title']].append(word)
                            if "Ban" in cat_punishments:
                                default_punishments['ban'] = True
                                if c['title'] not in default_punishments['ban_words']:
                                    default_punishments['ban_words'][c['title']] = [word]
                                else:
                                    default_punishments['ban_words'][c['title']].append(word)
                else:
                    words = await remove_duplicates(words)
                    for word in words:
                        if await check_for_word(new_content, word, 0):
                            if "Delete message" in cat_punishments:
                                default_punishments['delete'] = True
                            if "Mute" in cat_punishments:
                                default_punishments['mute'] = default_punishments['mute'] + await time(c['timeval'],
                                                                                                       c['timeunit'])
                                if c['title'] not in default_punishments['mute_words']:
                                    default_punishments['mute_words'][c['title']] = [word]
                                else:
                                    default_punishments['mute_words'][c['title']].append(word)
                            if "Warn" in cat_punishments:
                                default_punishments['warn'] = default_punishments['warn'] + c['points']
                                if c['title'] not in default_punishments['warn_words']:
                                    default_punishments['warn_words'][c['title']] = [word]
                                else:
                                    default_punishments['warn_words'][c['title']].append(word)
                            if "Kick" in cat_punishments:
                                default_punishments['kick'] = True
                                if c['title'] not in default_punishments['kick_words']:
                                    default_punishments['kick_words'][c['title']] = [word]
                                else:
                                    default_punishments['kick_words'][c['title']].append(word)
                            if "Tempban" in cat_punishments:
                                default_punishments['tempban'] = default_punishments['tempban'] + await time(
                                    c['timeval'],
                                    c['timeunit'])
                                if c['title'] not in default_punishments['tempban_words']:
                                    default_punishments['tempban_words'][c['title']] = [word]
                                else:
                                    default_punishments['tempban_words'][c['title']].append(word)
                            if "Ban" in cat_punishments:
                                default_punishments['ban'] = True
                                if c['title'] not in default_punishments['ban_words']:
                                    default_punishments['ban_words'][c['title']] = [word]
                                else:
                                    default_punishments['ban_words'][c['title']].append(word)

    if cttype == 'link':
        found_urls = extract.find_urls(message.content.replace('http', ' http').replace('www.', ' www.'))
        for i in range(len(found_urls)):
            if found_urls[i].startswith('www'):
                found_urls[i] = f"https://{found_urls[i]}"

        for category in categories:
            c = category
            role_whitelists = set(c['whitelistedRoles'].values())
            channel_whitelists = list((c['whitelistedChannels']).values())
            links = c['words']
            cat_punishments = c['punishments']
            if str(channel.id) not in channel_whitelists and len(
                    set([str(role.id) for role in user.roles]).intersection(role_whitelists)) == 0:
                for link in links:
                    urls = [url for url in found_urls if f".{link}." in url]
                    if len(urls) >= 1:
                        if "Delete message" in cat_punishments:
                            default_punishments['delete'] = True
                        if "Mute" in cat_punishments:
                            default_punishments['mute'] = default_punishments['mute'] + await time(c['timeval'],
                                                                                                   c['timeunit'])
                            if c['title'] not in default_punishments['mute_words']:
                                default_punishments['mute_words'][c['title']] = [link]
                            else:
                                default_punishments['mute_words'][c['title']].append(link)
                        if "Warn" in cat_punishments:
                            default_punishments['warn'] = default_punishments['warn'] + c['points']
                            if c['title'] not in default_punishments['warn_words']:
                                default_punishments['warn_words'][c['title']] = [link]
                            else:
                                default_punishments['warn_words'][c['title']].append(link)
                        if "Kick" in cat_punishments:
                            default_punishments['kick'] = True
                            if c['title'] not in default_punishments['kick_words']:
                                default_punishments['kick_words'][c['title']] = [link]
                            else:
                                default_punishments['kick_words'][c['title']].append(link)
                        if "Tempban" in cat_punishments:
                            default_punishments['tempban'] = default_punishments['tempban'] + await time(c['timeval'],
                                                                                                         c['timeunit'])
                            if c['title'] not in default_punishments['tempban_words']:
                                default_punishments['tempban_words'][c['title']] = [link]
                            else:
                                default_punishments['tempban_words'][c['title']].append(link)
                        if "Ban" in cat_punishments:
                            default_punishments['ban'] = True
                            if c['title'] not in default_punishments['ban_words']:
                                default_punishments['ban_words'][c['title']] = [link]
                            else:
                                default_punishments['ban_words'][c['title']].append(link)

    return default_punishments


async def to_punish_reason(violated, ty):
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

#
# async def connections():
#     global bot.conn
#     bot.conn = await asyncpg.create_pool(host=d['host'], port=d['port'], user=d['user'], password=d['pwd'],
#                                           database=d['db'])

async def t(secs):  # done
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


async def profile_punishments(user, categories, content, type, ignored_words):
    default_punishments = {'delete': False, 'mute': 0, 'warn': 0, 'kick': False, 'tempban': 0, 'ban': False,
                           'mute_words': {}, 'warn_words': {}, 'kick_words': {}, 'tempban_words': {}, 'ban_words': {}}
    remove_zalgo = lambda s: re.sub("(?i)([aeiouy]̈)|[̀-ͯ҉]", "\\1", s)


    trimmed_content = re.sub(r'https?:\/\/.*[\r\n]*', '', await remove_ignored(content, ignored_words))
    new_content = (await remove_emojis(await no_punc(remove_zalgo(trimmed_content)))) \
        .replace("\u200b", "").casefold().strip().lower().replace("…", "...")

    if type == 'namestatus':
        for category in categories:

            if isinstance(category, str):
                c = eval(category)
            else:
                c = category
            role_whitelists = set(c['whitelistedRoles'].values())
            words = c['words']
            cat_punishments = c['punishments']
            if len(set([str(role.id) for role in user.roles]).intersection(role_whitelists)) == 0:
                if c['substring'] == 1:
                    words = await change_words(words)
                    for word in words:
                        if await check_for_word(new_content, word, 1):
                            if "Mute" in cat_punishments:
                                default_punishments['mute'] = default_punishments['mute'] + await time(c['timeval'],
                                                                                                       c['timeunit'])
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
                                default_punishments['tempban'] = default_punishments['tempban'] + await time(
                                    c['timeval'],
                                    c['timeunit'])
                                if c['title'] not in default_punishments['tempban_words']:
                                    default_punishments['tempban_words'][c['title']] = []
                                default_punishments['tempban_words'][c['title']].append(word)
                            if "Ban" in cat_punishments:
                                default_punishments['ban'] = True
                                if c['title'] not in default_punishments['ban_words']:
                                    default_punishments['ban_words'][c['title']] = []
                                default_punishments['ban_words'][c['title']].append(word)
                else:
                    words = await remove_duplicates(words)
                    for word in words:
                        if await check_for_word(new_content, word, 0):
                            if "Mute" in cat_punishments:
                                default_punishments['mute'] = default_punishments['mute'] + await time(c['timeval'],
                                                                                                       c['timeunit'])
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
                                default_punishments['tempban'] = default_punishments['tempban'] + await time(
                                    c['timeval'],
                                    c['timeunit'])
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
            if isinstance(category, str):
                c = eval(category)
            else:
                c = category
            role_whitelists = set(c['whitelistedRoles'].values())
            words = c['words']
            cat_punishments = c['punishments']
            if len(set([str(role.id) for role in user.roles]).intersection(role_whitelists)) == 0:
                if c['substring'] == 1:
                    words = await change_words(words)

                    for word in words:
                        if await check_for_word(new_content, word, 1):
                            if "Mute" in cat_punishments:
                                default_punishments['mute'] = default_punishments['mute'] + await time(c['timeval'],
                                                                                                       c['timeunit'])
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
                                default_punishments['tempban'] = default_punishments['tempban'] + await time(
                                    c['timeval'],
                                    c['timeunit'])
                                if c['title'] not in default_punishments['tempban_words']:
                                    default_punishments['tempban_words'][c['title']] = []
                                default_punishments['tempban_words'][c['title']].append(word)
                            if "Ban" in cat_punishments:
                                default_punishments['ban'] = True
                                if c['title'] not in default_punishments['ban_words']:
                                    default_punishments['ban_words'][c['title']] = []
                                default_punishments['ban_words'][c['title']].append(word)
                else:
                    words = await remove_duplicates(words)

                    for word in words:
                        if await check_for_word(new_content, word, 0):
                            if "Mute" in cat_punishments:
                                default_punishments['mute'] = default_punishments['mute'] + await time(c['timeval'],
                                                                                                       c['timeunit'])
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
                                default_punishments['tempban'] = default_punishments['tempban'] + await time(
                                    c['timeval'],
                                    c['timeunit'])
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
        pass


async def status(member):
    a = [activity for activity in member.activities if isinstance(activity, discord.CustomActivity)]
    if len(a) == 0:
        return ''
    else:
        if a[0].name is not None:
            return a[0].name
        else:
            return ''


async def has_permissions(b, member, permission):
    guild = member.guild
    bot_perms = dict(list(b.guild_permissions))
    if bot_perms[permission] and not guild.owner_id == member.id and member.top_role.position < b.top_role.position:
        return True
    return False


async def has_guild_permissions(b, permission):
    bot_perms = dict(list(b.guild_permissions))
    if bot_perms[permission]:
        return True
    return False


async def msg_handler(bot, message):
    if message.guild is None:
        if message.author.id == 825455379424739388:
            if message.content.lower().strip() == 'user':
                users = bot.users
                humans = []
                bots = []

                for user in users:
                    if len(user.mutual_guilds) > 0:
                        if user.bot:
                            bots.append(user)
                        else:
                            humans.append(user)

                await message.author.send(f"**Humans:** {len(humans)}\n**Bots:** {len(bots)}\n**Total:** {len(humans) + len(bots)}")
            if message.content.lower().strip() == 'guild':
                await message.author.send(str(len(bot.guilds)))
            if message.content.lower().strip() == 'maintain':
                await bot.change_presence(status=discord.Status.online, activity=discord.CustomActivity(name="Under maintenance! May not work as intended"))
            if message.content.lower().strip() == 'msgcount':
                await message.author.send(
                    f"**In dict:** {str(sum([len(messages_cache[channel]) for channel in messages_cache]))}\n**Cached: **{len(bot.cached_messages)}")
            if message.content.lower().strip() == 'mbc':
                member_counts = [len(guild.members) for guild in bot.guilds]
                member_counts.sort()
                stuff = ", ".join([str(n) for n in member_counts])
                await message.author.send(embed=discord.Embed(title="Guild member counts", description=stuff))
            if message.content.lower().strip() == 'minutes':
                await message.author.send(
                    str(int((datetime.datetime.now() - start_timestamp['time']).total_seconds() // 60)))
            if message.content.lower().strip() == 'memory':
                await message.author.send(f"{round(psutil.Process().memory_info().rss / (1024 * 1024), 2)} MB")
    else:
        if message.guild is not None and message.author.id != 834072169507848273 and isinstance(message.author,
                                                                                                discord.Member):

            bot_user = f"{bot.user.name}#{bot.user.discriminator}"
            user = message.author
            guild = message.guild
            punishments = await message_punishments(message, message.guild, bot)

            if await has_guild_permissions(user.guild.me, 'manage_messages'):
                await message.channel.delete_messages(punishments['deletes'])
            if punishments['warn'] > 0:
                await handle_send(user, discord.Embed(title=f"You've been warned in {guild}",
                                                      description=f"**Points added:** {punishments['warn']}\n**Reason:** {', '.join(punishments['warn_reason'])}\n**Moderator: **{bot_user}",
                                                      color=0xf54254))
                warn_punishments = await warn(bot, user, guild, punishments['warn'], bot.conn,
                                              ', '.join(punishments['warn_reason']), bot)

                if warn_punishments['punishment'] == 'ban':
                    punishments['ban'] = True
                    punishments['ban_reason'].append(warn_punishments['reason'])
                elif warn_punishments['punishment'] == 'kick':
                    punishments['kick'] = True
                    punishments['kick_reason'].append(warn_punishments['reason'])
                elif warn_punishments['punishment'] == 'mute':
                    punishments['mute'] += warn_punishments['amount']
                    punishments['mute_reason'].append(warn_punishments['reason'])
                elif warn_punishments['punishment'] == 'tempban':
                    punishments['tempban'] += warn_punishments['amount']
                    punishments['tempban_reason'].append(warn_punishments['reason'])

            if punishments['ban'] and await has_permissions(user.guild.me, user, 'ban_members'):
                await user.ban()
                await handle_send(user, discord.Embed(title=f"You've been banned from {guild}",
                                                      description=f"**Reason:** {', '.join(punishments['ban_reason'])}\n**Moderator: **{bot_user}",
                                                      color=0xf54254))
                await log_ban(bot, guild, user, ', '.join(punishments['ban_reason']), bot, bot.conn)

            if punishments['tempban'] > 0 and await has_permissions(user.guild.me, user, 'ban_members'):
                reason = ', '.join(punishments['tempban_reason'])
                await tempban(bot, user, reason, punishments['tempban'], guild, bot_user, bot.conn)

            if punishments['kick'] and await has_permissions(user.guild.me, user, 'kick_members'):
                await user.kick(reason=', '.join(punishments['kick_reason']))
                await handle_send(user, discord.Embed(title=f"You've been kicked from {guild}",
                                                      description=f"**Reason:** {', '.join(punishments['kick_reason'])}\n**Moderator: **{bot_user}",
                                                      color=0xf54254))

            if punishments['mute'] > 0 and await has_permissions(user.guild.me, user, 'moderate_members'):
                reason = ', '.join(punishments['mute_reason'])
                await user.timeout(
                    until=datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(
                        seconds=punishments['mute']))
                await handle_send(user, discord.Embed(title=f"You've been muted in {guild}",
                                                      description=f"**Duration:** {await t(punishments['mute'])}\n**Reason:** {reason}\n**Moderator: **{bot_user}",
                                                      color=0xf54254))
                await log_mute(bot, guild, user, f"{await t(punishments['mute'])}", reason, bot, bot.conn)


async def status_handler(bot, before, after, custom_status):
    settings = await bot.conn.fetchrow('SELECT badstatuses, automodgeneral FROM msg_automod where guild_id=$1',
                                        after.guild.id)

    str_dic = lambda dic: dic if isinstance(dic, dict) else eval(dic.replace("null", "0"))

    if settings is not None:
        badstatus_settings = str_dic(dict(settings)['badstatuses'])
        general_settings = str_dic(dict(settings)['automodgeneral'])
        categories = badstatus_settings['categories']
        role_whitelists = general_settings['role_whitelists'].values()
        if "ignored_words" in list(general_settings.keys()):
            ignored_words = general_settings["ignored_words"]
        else:
            ignored_words = []
    else:
        categories = default_settings['badstatuses']
        role_whitelists = []
        ignored_words = []

    if len(set([str(role.id) for role in after.roles]).intersection(
            role_whitelists)) == 0 and after.id != 834072169507848273:
        bot_user = f"{bot.user.name}#{bot.user.discriminator}"
        guild = after.guild


        st = custom_status
        punishments = await profile_punishments(after, categories, st.strip(), 'namestatus', ignored_words)
        punishments['mute_reason'] = [await to_punish_reason(punishments['mute_words'], 'status')
                                      ]
        punishments['kick_reason'] = [await to_punish_reason(punishments['kick_words'], 'status')
                                      ]
        punishments['tempban_reason'] = [
            await to_punish_reason(punishments['tempban_words'], 'status')
        ]
        punishments['ban_reason'] = [i for i in await to_punish_reason(punishments['ban_words'], 'status')]

        if punishments['warn'] > 0:
            punish_reason = await to_punish_reason(punishments['warn_words'], 'status')
            await handle_send(after, discord.Embed(title=f"You've been warned in {guild}",
                                                   description=f"**Points added:** {punishments['warn']}\n**Reason:** {punish_reason}\n**Moderator: **{bot_user}",
                                                   color=0xf54254))
            warn_punishments = await warn(bot, after, guild, punishments['warn'], bot.conn,
                                          punish_reason, bot)
            if warn_punishments['punishment'] == 'ban':
                punishments['ban'] = True
                punishments['ban_reason'].append(warn_punishments['reason'])
            elif warn_punishments['punishment'] == 'kick':
                punishments['kick'] = True
                punishments['kick_reason'].append(warn_punishments['reason'])
            elif warn_punishments['punishment'] == 'mute':
                punishments['mute'] += warn_punishments['amount']
                punishments['mute_reason'].append(warn_punishments['reason'])
            elif warn_punishments['punishment'] == 'tempban':
                punishments['tempban'] += warn_punishments['amount']
                punishments['tempban_reason'].append(warn_punishments['reason'])

        if punishments['ban'] and await has_permissions(after.guild.me, after, 'ban_members'):
            await after.ban(
                reason=f"Automatic action for {', '.join(punishments['ban_reason'])}")
            await handle_send(after,
                              embed=discord.Embed(title=f"You've been banned from {after.guild}",
                                                  description=f"**Reason:** {', '.join(punishments['ban_reason'])}\n**Moderator: **{bot_user}",
                                                  color=0xf54254))
            await log_ban(bot, guild, after, ', '.join(punishments['ban_reason']),
                          bot, bot.conn)

        if punishments['tempban'] > 0 and await has_permissions(after.guild.me, after, 'ban_members'):
            await tempban(bot, after, ', '.join(punishments['tempban_reason']), punishments['tempban'],
                          after.guild, bot_user, bot.conn)

        if punishments['kick'] and await has_permissions(after.guild.me, after, 'kick_members'):
            await after.kick(
                reason=f"Automatic action for {', '.join(punishments['kick_reason'])}")
            await handle_send(after,
                              embed=discord.Embed(title=f"You've been kicked from {after.guild}",
                                                  description=f"**Reason:** Automatic action for {', '.join(punishments['kick_reason'])}\n**Moderator: **{bot_user}",
                                                  color=0xf54254))
        if punishments['mute'] > 0 and await has_permissions(after.guild.me, after, 'moderate_members'):
            await after.timeout(
                until=datetime.datetime.now() + datetime.timedelta(seconds=punishments['mute']))
            await handle_send(after, embed=discord.Embed(title=f"You've been muted in {after.guild}",
                                                         description=f"**Duration:** {await t(punishments['mute'])}\n**Reason:** Automatic action for {', '.join(punishments['mute_reason'])}\n**Moderator: **{bot_user}",
                                                         color=0xf54254))

            await log_mute(bot, after.guild, after, await t(punishments['mute']),
                           f"Automatic action for {', '.join(punishments['mute_reason'])}",
                           bot, bot.conn)


async def profile_handler(bot, before, after):
    if (before.name != after.name or before.global_name != after.global_name) and after.id != 834072169507848273:
        bot_user = f"{bot.user.name}#{bot.user.discriminator}"
        if before.name != after.name:
            new_name = after.name
        if before.global_name != after.global_name:
            new_name = after.global_name

        for guild in after.mutual_guilds:
            member = await member_fetch(after, guild)
            if member:
                guild_id = guild.id
                settings = await bot.conn.fetchrow(
                    'SELECT badnames, automodgeneral FROM msg_automod where guild_id=$1', guild_id)

                str_dic = lambda dic: dic if isinstance(dic, dict) else eval(dic.replace("null", "0"))

                if settings is not None:
                    badname_settings = str_dic(dict(settings)['badnames'])
                    general_settings = str_dic(dict(settings)['automodgeneral'])
                    categories = badname_settings['categories']
                    role_whitelists = general_settings['role_whitelists'].values()
                    if "ignored_words" in list(general_settings.keys()):
                        ignored_words = general_settings["ignored_words"]
                    else:
                        ignored_words = []
                else:
                    categories = default_settings['badnames']
                    role_whitelists = []
                    ignored_words = []

                if len(set([str(role.id) for role in after.roles]).intersection(
                        role_whitelists)) == 0 and after.id != 834072169507848273:


                    punishments = await profile_punishments(member, categories, new_name.lower().strip(), 'namestatus',
                                                            ignored_words)
                    punishments['mute_reason'] = [await to_punish_reason(punishments['mute_words'], 'username')
                                                  ]
                    punishments['kick_reason'] = [await to_punish_reason(punishments['kick_words'], 'username')
                                                  ]
                    punishments['tempban_reason'] = [
                        await to_punish_reason(punishments['tempban_words'], 'username')
                    ]
                    punishments['ban_reason'] = [i for i in
                                                 await to_punish_reason(punishments['ban_words'], 'username')]

                    if punishments['warn'] > 0:
                        punish_reason = await to_punish_reason(punishments['warn_words'], 'username')
                        await handle_send(after, discord.Embed(title=f"You've been warned in {guild}",
                                                               description=f"**Points added:** {punishments['warn']}\n**Reason:** {punish_reason}\n**Moderator: **{bot_user}",
                                                               color=0xf54254))
                        warn_punishments = await warn(bot, after, guild, punishments['warn'], bot.conn,
                                                      punish_reason, bot)
                        if warn_punishments['punishment'] == 'ban':
                            punishments['ban'] = True
                            punishments['ban_reason'].append(warn_punishments['reason'])
                        elif warn_punishments['punishment'] == 'kick':
                            punishments['kick'] = True
                            punishments['kick_reason'].append(warn_punishments['reason'])
                        elif warn_punishments['punishment'] == 'mute':
                            punishments['mute'] += warn_punishments['amount']
                            punishments['mute_reason'].append(warn_punishments['reason'])
                        elif warn_punishments['punishment'] == 'tempban':
                            punishments['tempban'] += warn_punishments['amount']
                            punishments['tempban_reason'].append(warn_punishments['reason'])

                    if punishments['ban'] and await has_permissions(after.guild.me, after, 'ban_members'):
                        await after.ban(
                            reason=f"Automatic action for {', '.join(punishments['ban_reason'])}")
                        await handle_send(after,
                                          embed=discord.Embed(title=f"You've been banned from {after.guild}",
                                                              description=f"**Reason:** {', '.join(punishments['ban_reason'])}\n**Moderator: **{bot_user}",
                                                              color=0xf54254))
                        await log_ban(bot, guild, after, ', '.join(punishments['ban_reason']),
                                      bot, bot.conn)

                    if punishments['tempban'] > 0 and await has_permissions(after.guild.me, after, 'ban_members'):
                        await tempban(bot, after, ', '.join(punishments['tempban_reason']), punishments['tempban'],
                                      after.guild, bot_user, bot.conn)

                    if punishments['kick'] and await has_permissions(after.guild.me, after, 'kick_members'):
                        await after.kick(
                            reason=f"Automatic action for {', '.join(punishments['kick_reason'])}")
                        await handle_send(after,
                                          embed=discord.Embed(title=f"You've been kicked from {after.guild}",
                                                              description=f"**Reason:** Automatic action for {', '.join(punishments['kick_reason'])}\n**Moderator: **{bot_user}",
                                                              color=0xf54254))
                    if punishments['mute'] > 0 and await has_permissions(after.guild.me, after, 'moderate_members'):
                        await after.timeout(
                            until=datetime.datetime.now() + datetime.timedelta(seconds=punishments['mute']))
                        await handle_send(after, embed=discord.Embed(title=f"You've been muted in {after.guild}",
                                                                     description=f"**Duration:** {await t(punishments['mute'])}\n**Reason:** Automatic action for {', '.join(punishments['mute_reason'])}\n**Moderator: **{bot_user}",
                                                                     color=0xf54254))

                        await log_mute(bot, after.guild, after, await t(punishments['mute']),
                                       f"Automatic action for {', '.join(punishments['mute_reason'])}",
                                       bot, bot.conn)



async def nick_handler(bot, before, after):
    settings = await bot.conn.fetchrow('SELECT badnicks, automodgeneral FROM msg_automod where guild_id=$1', after.guild.id)

    str_dic = lambda dic: dic if isinstance(dic, dict) else eval(dic.replace("null", "0"))

    if settings is not None:
        badnick_settings = str_dic(dict(settings)['badnicks'])
        general_settings = str_dic(dict(settings)['automodgeneral'])
        categories = badnick_settings['categories']
        role_whitelists = general_settings['role_whitelists'].values()
        if "ignored_words" in list(general_settings.keys()):
            ignored_words = general_settings["ignored_words"]
        else:
            ignored_words = []
    else:
        categories = default_settings['badnicks']
        role_whitelists = []
        ignored_words = []


    if len(set([str(role.id) for role in after.roles]).intersection(
            role_whitelists)) == 0 and after.id != 834072169507848273:
        bot_user = f"{bot.user.name}#{bot.user.discriminator}"
        new_nick = after.display_name
        guild_id = after.guild.id

        punishments = await profile_punishments(after, categories, new_nick.lower().strip(), 'nick',
                                                ignored_words)
        punishments['mute_reason'] = [await to_punish_reason(punishments['mute_words'], 'nickname')
                                      ]
        punishments['kick_reason'] = [await to_punish_reason(punishments['kick_words'], 'nickname')
                                      ]
        punishments['tempban_reason'] = [
            await to_punish_reason(punishments['tempban_words'], 'nickname')
        ]
        punishments['ban_reason'] = [i for i in await to_punish_reason(punishments['ban_words'], 'nickname')]

        if punishments['warn'] > 0:
            if await has_permissions(after.guild.me, after, 'manage_nicknames'):
                await after.edit(nick=before.nick)
            punish_reason = await to_punish_reason(punishments['warn_words'], 'nickname')
            await handle_send(after, discord.Embed(title=f"You've been warned in {after.guild}",
                                                   description=f"**Points added:** {punishments['warn']}\n**Reason:** {punish_reason}\n**Moderator: **{bot_user}",
                                                   color=0xf54254))
            warn_punishments = await warn(bot, after, after.guild, punishments['warn'], bot.conn,
                                          punish_reason, bot)
            if warn_punishments['punishment'] == 'ban':
                punishments['ban'] = True
                punishments['ban_reason'].append(warn_punishments['reason'])
            elif warn_punishments['punishment'] == 'kick':
                punishments['kick'] = True
                punishments['kick_reason'].append(warn_punishments['reason'])
            elif warn_punishments['punishment'] == 'mute':
                punishments['mute'] += warn_punishments['amount']
                punishments['mute_reason'].append(warn_punishments['reason'])
            elif warn_punishments['punishment'] == 'tempban':
                punishments['tempban'] += warn_punishments['amount']
                punishments['tempban_reason'].append(warn_punishments['reason'])

        if punishments['ban'] and await has_permissions(after.guild.me, after, 'ban_members'):
            await after.ban(
                reason=f"Automatic action for {', '.join(punishments['ban_reason'])}")
            await handle_send(after,
                              embed=discord.Embed(title=f"You've been banned from {after.guild}",
                                                  description=f"**Reason:** {', '.join(punishments['ban_reason'])}\n**Moderator: **{bot_user}",
                                                  color=0xf54254))
            await log_ban(bot, before.guild, after, ', '.join(punishments['ban_reason']),
                          bot, bot.conn)

        if punishments['tempban'] > 0 and await has_permissions(after.guild.me, after, 'ban_members'):
            await tempban(bot, after, ', '.join(punishments['tempban_reason']), punishments['tempban'],
                          after.guild,
                          bot_user, bot.conn)

        if punishments['kick'] and await has_permissions(after.guild.me, after, 'kick_members'):
            await after.kick(
                reason=f"Automatic action for {', '.join(punishments['kick_reason'])}")
            await handle_send(after,
                              embed=discord.Embed(title=f"You've been kicked from {after.guild}",
                                                  description=f"**Reason:** Automatic action for {', '.join(punishments['kick_reason'])}\n**Moderator: **{bot_user}",
                                                  color=0xf54254))
        if punishments['mute'] > 0 and await has_permissions(after.guild.me, after, 'moderate_members'):
            await after.timeout(
                until=datetime.datetime.now() + datetime.timedelta(seconds=punishments['mute']))
            await handle_send(after, embed=discord.Embed(title=f"You've been muted in {after.guild}",
                                                         description=f"**Duration:** {await t(punishments['mute'])}\n**Reason:** Automatic action for {', '.join(punishments['mute_reason'])}\n**Moderator: **{bot_user}",
                                                         color=0xf54254))

            await log_mute(bot, after.guild, after, await t(punishments['mute']),
                           f"Automatic action for {', '.join(punishments['mute_reason'])}",
                           bot, bot.conn)


async def member_fetch(user, guild):
    member = guild.get_member(user.id)
    if member is None:
        try:
            member = await guild.fetch_member(user.id)
        except (discord.NotFound, discord.HTTPException) as e:
            member = None
    return member


start_timestamp = {}
gc.set_threshold(200, 3, 3)
conn_thing = {'conn_count': 0}


class Automod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.run_garbage_collection.start()

    @commands.Cog.listener()
    async def on_message(self, message):
        await msg_handler(self.bot, message)
        # try:
        #     await msg_handler(self.bot, message)
        # except Exception as e:
        #     print(f"MESSAGE HANDLE ERROR: {e}")
        #     pass
        # finally:
        #     del message

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        old_status = await status(before)
        new_status = await status(after)
        if old_status != new_status and new_status != '' and isinstance(new_status, str):
            try:
                await status_handler(self.bot, before, after, new_status)
            except:
                pass

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        if (
                before.name != after.name or before.global_name != after.global_name) and after.id != 834072169507848273:
            try:
                await profile_handler(self.bot, before, after)
            except:
                pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick != after.nick:
            # try:
                await nick_handler(self.bot, before, after)
            # except:
            #     pass

    @tasks.loop(minutes=15)
    async def run_garbage_collection(self):
        """Run the garbage collector periodically."""
        messages_cache.clear()
        self.bot._connection._messages.clear()
        self.bot._connection._stickers.clear()
        self.bot._connection._polls.clear()

        print(f"Memory: {round(psutil.Process().memory_info().rss / (1024 * 1024), 2)} MB")

    @run_garbage_collection.before_loop
    async def before_run_garbage_collection(self):
        """Wait until the bot is ready before starting the task."""
        await self.bot.wait_until_ready()
        await asyncio.sleep(900)

    @commands.Cog.listener()
    async def on_disconnect(self):
        print("disconnecting!")
        messages_cache.clear()
        self.bot._connection._messages.clear()
        self.bot._connection._stickers.clear()
        self.bot._connection._polls.clear()

        gc.collect()

    @commands.Cog.listener()
    async def on_ready(self):
        start_timestamp['time'] = datetime.datetime.now()
        # conn_thing['conn_count'] += 1
        # if conn_thing['conn_count'] == 1:
        #     task = asyncio.create_task(connections())
        #     await task

    @commands.Cog.listener()
    async def on_resumed(self):
        print("resumed!")
        # conn_thing['conn_count'] += 1
        # if conn_thing['conn_count'] == 1:
        #     task = asyncio.create_task(connections())
        #     await task


def setup(bot):
    bot.add_cog(Automod(bot))
