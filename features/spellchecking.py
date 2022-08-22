import re

import pkg_resources
from symspellpy import SymSpell

sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
dictionary_path = pkg_resources.resource_filename(
    "symspellpy", "frequency_dictionary_en_82_765.txt"
)
bigram_path = pkg_resources.resource_filename(
    "symspellpy", "frequency_bigramdictionary_en_243_342.txt"
)

sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1)
sym_spell.load_bigram_dictionary(bigram_path, term_index=0, count_index=2)


def check(text):
    remove_zalgo = lambda s: re.sub("(?i)([aeiouy]̈)|[̀-ͯ҉]", "\\1", s)
    clean_text = remove_zalgo(text)
    suggestions = sym_spell.lookup_compound(clean_text, max_edit_distance=2)
    return str(suggestions[0]).lower()
