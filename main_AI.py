import pysrt
import re
from wordfreq import zipf_frequency
from nltk.tokenize import word_tokenize
from nltk.tokenize.treebank import TreebankWordDetokenizer
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ── 常量 ──────────────────────────────────────────────────
MAX_WORKERS_SUBS  = 8   # 并发处理字幕条数
MAX_WORKERS_WORDS = 4   # 每条字幕内并发翻译单词数
# 两个翻译方向可并行，所以单词级实际并发 = MAX_WORKERS_WORDS

# ── API Key（只读一次，线程安全）─────────────────────────
with open("api_key") as f:
    API_KEY = f.read().strip()

# ── 工具函数 ──────────────────────────────────────────────
def is_rare(word: str) -> bool:
    if word[0].isupper() and word[1:].islower():
        return False
    word = word.lower()
    if not re.match(r"^[a-z]+$", word):
        return False
    if word == "wili":
        return False
    return zipf_frequency(word, "en") < 3


# lru_cache 让相同单词只翻译一次，多线程下用锁保护
_translate_lock = threading.Lock()
_translate_cache: dict[tuple, str] = {}

def translate_word(word: str, src: str = "en", tgt: str = "zh") -> str:
    key = (word, src, tgt)
    with _translate_lock:
        if key in _translate_cache:
            return _translate_cache[key]

    url = "https://translation.googleapis.com/language/translate/v2"
    params = {"q": word, "target": tgt, "source": src, "format": "text", "key": API_KEY}
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    result = response.json()["data"]["translations"][0]["translatedText"]
    print(f"  🔤 {word!r:20s} → [{tgt}] {result}")

    with _translate_lock:
        _translate_cache[key] = result
    return result


def sub_word_add_notation(word: str) -> str:
    """对单个 token 做注释；罕见词并行请求两种语言翻译。"""
    if not is_rare(word):
        return word

    # 两个翻译方向并行
    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_zh = ex.submit(translate_word, word, "en", "zh")
        fut_my = ex.submit(translate_word, word, "en", "my")
        zh = fut_zh.result()
        my = fut_my.result()

    return f"{word}( {my} | {zh} )"


def sub_add_notation(sub, detokenizer: TreebankWordDetokenizer):
    """处理单条字幕（线程安全：不共享可变状态）。"""
    tokens = word_tokenize(sub.text)

    # 条内单词并行（翻译 I/O 密集，适合多线程）
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_WORDS) as ex:
        futures = {ex.submit(sub_word_add_notation, t): idx for idx, t in enumerate(tokens)}
        results = [None] * len(tokens)
        for fut in as_completed(futures):
            results[futures[fut]] = fut.result()

    sub.text = detokenizer.detokenize(results)
    return sub


# ── 主函数：字幕级多线程 ──────────────────────────────────
def subs_add_notation(subs):
    detokenizer = TreebankWordDetokenizer()   # 无状态，可共享
    total = len(subs)
    results = [None] * total
    completed = 0
    lock = threading.Lock()

    def process(idx, sub):
        annotated = sub_add_notation(sub, detokenizer)
        nonlocal completed
        with lock:
            completed += 1
            print(f"✅ DONE {completed:>4} / {total}  (sub #{idx})")
        return idx, annotated

    with ThreadPoolExecutor(max_workers=MAX_WORKERS_SUBS) as ex:
        futures = {ex.submit(process, i, subs[i]): i for i in range(total)}
        for fut in as_completed(futures):
            idx, annotated = fut.result()
            results[idx] = annotated

    return results


# ── 入口 ─────────────────────────────────────────────────
if __name__ == "__main__":
    srt_input  = "SrtsToProcess/Game of Thrones - 2x07 - A Man Without Honor.720p.BluRay.ShAaNiG.HI.en.srt"
    srt_output = "Game of Thrones - 2x07 - A Man Without Honor.720p.BluRay.ShAaNiG.HI.en"

    subs = pysrt.open(srt_input)
    subs[:] = subs_add_notation(subs)   # 原地替换，保留 SubRipFile 对象
    subs.save(srt_output, encoding="utf-8")
    print(f"\n🎉 已保存：{srt_output}")