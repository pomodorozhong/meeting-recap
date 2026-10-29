# /// script
# dependencies = ["opencc-python-reimplemented"]
# ///
"""Proxy transcript checks without a reference transcript.

- hallucination markers: Hangul, kana, Latin-script lines in other languages, stock phrases
- simplified share: CJK characters that change under OpenCC s2tw
- expected terms: optional pipe-separated terms in MEETING_RECAP_EXPECTED_TERMS
"""
import json, os, re, sys
from opencc import OpenCC

s2t = OpenCC("s2tw")
EXPECTED = [term for term in os.environ.get("MEETING_RECAP_EXPECTED_TERMS", "").split("|") if term]
STOCK = ["谢谢", "謝謝大家", "Thank you", "Bye", "Vielen Dank", "字幕", "訂閱", "Okay."]

def clean(t):
    return re.sub(r"<\|[^|]*\|>", "", t)

for path in sys.argv[1:]:
    d = json.load(open(path))
    segs = [clean(s["text"]).strip() for s in d["segments"]]
    text = "".join(segs)
    cjk = [c for c in text if "一" <= c <= "鿿"]
    changed = sum(a != b for a, b in zip("".join(cjk), s2t.convert("".join(cjk))))
    hangul_kana = len(re.findall(r"[가-힯぀-ヿ]", text))
    latin_only = [s for s in segs if s and not re.search(r"[一-鿿]", s)]
    stock = sum(text.count(p) for p in STOCK)
    found = [t for t in EXPECTED if t.lower() in text.lower()]
    name = path.split("/")[-1].removesuffix(".json")
    simplified = changed / len(cjk) if cjk else 0
    print(f"{name:22s} segs {len(segs):3d}  cjk {len(cjk):5d}  simplified {simplified:5.1%}  hangul/kana {hangul_kana:2d}  "
          f"latin-only segs {len(latin_only):2d}  stock {stock:2d}  terms {len(found)}/{len(EXPECTED)} {found}")
