import pysrt
import re
from wordfreq import zipf_frequency
from nltk.tokenize import word_tokenize
from nltk.tokenize.treebank import TreebankWordDetokenizer
import requests

def is_rare(word):

    # 排除首字母大写
    if word[0].isupper() and word[1:].islower():
        return False

    word = word.lower()
    # 排除标点符号
    if not re.match(r"^[a-z]+$", word):
        return False

    # 排除人为异常
    if word == "wili":
        return False

    return zipf_frequency(word.lower(), "en") < 3

def translate_word( word, translate_from_lang = "en" , translate_into_lang = "zh" ):
    with open('api_key') as f:
        API_KEY = f.read()
    url = "https://translation.googleapis.com/language/translate/v2"
    params = {
        "q": word,
        "target": translate_into_lang,
        "source": translate_from_lang,      # 省略則自動偵測
        "format": "text",    # 或 "html"
        "key": API_KEY,
    }
    response = requests.get(url, params=params)
    data = response.json()
    translated_text = data["data"]["translations"][0]["translatedText"]
    print("translated from " + word + " into " + translated_text )
    return translated_text

def sub_word_add_notation(sub_word):
    if is_rare( sub_word ):
        # 如果是罕见词，进行翻译然后填充
        chinese_translate = translate_word( sub_word, 'en', 'zh')
        burmese_translate = translate_word( sub_word, 'en', 'my')
        sub_word = sub_word + "( " + burmese_translate + " | " + chinese_translate + " )"
        return sub_word
    else:
        return sub_word


def sub_add_notation(sub, detokenizer):
    orgSub = sub;
    sub_words = word_tokenize(sub.text)
    for i in range(len(sub_words)):
        sub_words[i] = sub_word_add_notation(sub_words[i])
    sub_words = detokenizer.detokenize( sub_words )
    orgSub.text = sub_words
    return orgSub


def subs_add_notation(subs):
    detokenizer = TreebankWordDetokenizer()
    for i in range(len(subs)):
        subs[i] = sub_add_notation(subs[i], detokenizer)
        print(f"✅ DONE {i} / {len(subs)}")
    return subs


srt_input_file_name = "Game.of.Thrones.S02E05.1080p.Bluray.x265-HiQVE.srt"
srt_output_file_name = "Game.of.Thrones.S02E05.1080p.Bluray.x265-HiQVE_out.srt"

subs = pysrt.open(srt_input_file_name)

subs = subs_add_notation(subs)

subs.save(srt_output_file_name, encoding="utf-8")

