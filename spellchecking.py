import re


letter_dict = {'a': '[a4@q]+', 'b': '[b]+', 'c': '[c]+', 'd': '[d]+', 'e': '[e3]+', 'f': '[f]+', 'g': '[gh69]+', 'h': '[h]+', 'i': '[i1!j]+', 'j': '[j]+', 'k': '[k]+', 'l': '[l]+', 'm': '[m]+', 'n': '[n]+', 'o': '[o0p]+', 'p': '[p]+', 'q': '[q]+', 'r': '[r]+', 's': '[s$]+', 't': '[t7]+', 'u': '[u]+', 'v': '[v]+', 'w': '[w]+', 'x': '[x]+', 'y': '[y]+', 'z': '[z]+'}
ends_dict = {'a': '[a4@]+', 'b': '[b]+', 'c': '[c]+', 'd': '[d]+', 'e': '[e3]+', 'f': '[f]+', 'g': '[g9]+', 'h': '[h]+', 'i': '[i1j]+', 'j': '[j]+', 'k': '[k]+', 'l': '[l]+', 'm': '[m]+', 'n': '[n]+', 'o': '[o0]+', 'p': '[p]+', 'q': '[q]+', 'r': '[r]+', 's': '[s$]+', 't': '[t7]+', 'u': '[u]+', 'v': '[v]+', 'w': '[w]+', 'x': '[x]+', 'y': '[y]+', 'z': '[z]+'}

async def trim_nonalpha(word):
    if len(word) > 0:
        found_alpha_at_front = False
        while not found_alpha_at_front and len(word) > 0:
            if not word[0].isalpha():
                word = word[1:]
            else:
                found_alpha_at_front = not found_alpha_at_front

        found_alpha_at_back = False
        while not found_alpha_at_back and len(word) > 0:
            if not word[-1].isalnum():
                word = word[:-1]
            else:
                found_alpha_at_back = not found_alpha_at_back
        return word
    else:
        return word


async def clean_message_words(message):
    word_list = []
    for word in message.split():
        w = re.sub(r"(.)\1{4,}", r"\1\1\1", await trim_nonalpha(word))
        word_list.append(w)
    return word_list


async def generate_word_re(word):
    re_exp = ""
    for i in range(len(word)):
        char = word[i]
        if i == 0 or i == len(word) - 1:
            try:
                re_exp += ends_dict[char]
            except:
                re_exp += f"[{char}]+"
        else:
            try:
                re_exp += letter_dict[char]
            except:
                re_exp += f"[{char}]+"
    return re_exp


async def min_ratio(n):
    if 3 <= n <= 5:
        return 0.3
    if 6 <= n <= 8:
        return 0.15
    return 0.1


async def check_for_word(message, target_word, substring):
    words = await clean_message_words(message)
    full_msg = " ".join(words)
    target_word_re = await generate_word_re(target_word)
    ok_matches = 0
    if substring:
        for word in words:
            matches = re.findall(target_word_re, word)
            for match in matches:
                if (len(set(match) - set(target_word)) <= 2 or word in message) and len(target_word)/len(word) >= await min_ratio(len(target_word)):
                    ok_matches += 1
    else:
        for word in words:
            matches = re.findall(target_word_re, word)
            for match in matches:
                if len(set(word) - set(target_word)) <= 2 and (full_msg.startswith(f"{match} ") or full_msg.endswith(f" {match}") or f" {match} " in full_msg):
                    ok_matches += 1

    return ok_matches >= 1


async def remove_ignored(sentence, ignored_words):
    actual_sentence = []
    for word in sentence.split():
        if word.lower() not in ignored_words:
            actual_sentence.append(word)
    return ' '.join(actual_sentence).lower()

print('scarbo is gay')







