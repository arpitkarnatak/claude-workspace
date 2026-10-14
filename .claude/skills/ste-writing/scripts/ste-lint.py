import re, sys, json, glob, os

# Score v3: unwraps hard-wrapped lines before scoring, applies the 25-word
# descriptive cap in flavored mode, stops counting possessive 's as a
# contraction, and counts the em dash as a violation in both modes.
# Score v2 added complex_tense (perfect tenses, modal stacks), exempts
# adjectival/stative participles from the passive count, moves "provide" to the
# banned list, adds a noun-train marker and a --strict mode. The episode's
# published numbers were measured with score v1 (this file's git history at the
# episode date); v1 and v2 totals are close but not directly comparable.
SCORE_VERSION = 3

MARKETING = ["seamless","seamlessly","robust","powerful","cutting-edge","effortless","effortlessly",
    "world-class","next-generation","revolutionary","blazing","lightning-fast","elegant","delightful",
    "turnkey","best-in-class","state-of-the-art","game-changing","first-class","battle-tested",
    "enterprise-grade","supercharge","unlock","unleash","empower","empowers"]
BANNED = ["begin","begins","commence","commences","initiate","initiates","originate",
    "utilize","utilizes","utilizing","leverage","leverages","leveraging","facilitate","facilitates",
    "ensure","ensures","ensuring","prior to","subsequent to","obtain","obtains","acquire","acquires",
    "demonstrate","demonstrates","additionally","furthermore","moreover","comprehensive","comprehensively",
    "utilization","aforementioned","henceforth","therein","whilst","amongst","numerous","myriad","plethora",
    "provide","provides","provided",
    "in order to","a variety of","in the event that","due to the fact that","it is important to note"]
# STE's own recurring-errors list (see ste-recurring-errors.md). Counted only
# with --strict: these are correct STE but would flag normal prose in docs.
STRICT_BANNED = ["however","since","should","shall","using","follow","follows","followed"]
PHRASAL = ["spin up","spin down","reach out","dive into","dives into","diving into","kick off","kicks off",
    "roll out","rolls out","tear down","ramp up","circle back","drill down","spun up","reaching out"]
MODAL_HEDGE = ["it is important to note","it should be noted","it is worth noting","please note that",
    "as mentioned","as noted above"]
BE = r"(?:am|is|are|was|were|be|been|being)"
PP_IRREG = r"(?:done|made|sent|read|built|kept|held|set|put|run|written|shown|given|taken|found|got|gotten|seen|known|thrown|drawn)"
# Rule 3.3: a past participle used as an adjective is not passive. These
# stative participles only count as passive when a by-agent follows.
STATIVE = r"(?:closed|opened?|damaged|completed?|installed|connected|required|expected|configured|enabled|disabled|deprecated|supported)"
FUNC_WORDS = set("""a an the this that these those of for to in on at by with from as and or but if
when then than not no is are was were be been being am do does did has have had will would can could
may might must should shall it its their your our his her they we you i""".split())

def strip_code(t):
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"`[^`]*`", " ", t)
    return t

BLOCK_START = re.compile(r"^\s*(?:#{1,6}\s|[-*+]\s|\d+[.)]\s|>\s|\|)")

def unwrap(text):
    """Join hard-wrapped continuation lines into one logical line.

    Markdown prose is often wrapped at 80-100 columns. Treating each physical
    line as a sentence hides long sentences and breaks any check whose pattern
    spans the wrap ("has been\\ndesigned"), so a wrapped file scores better than
    the identical unwrapped file. Blank lines, headings, list items, block
    quotes and table rows still start a new block."""
    blocks = []
    for line in text.split("\n"):
        if not line.strip():
            blocks.append("")
        elif blocks and blocks[-1] and not BLOCK_START.match(line):
            blocks[-1] += " " + line.strip()
        else:
            blocks.append(line.rstrip())
    return "\n".join(blocks)

def sentences(text):
    out = []
    for line in unwrap(text).split("\n"):
        s = line.strip()
        if not s: continue
        s = re.sub(r"^\s*#{1,6}\s*", "", s)
        s = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", s)
        if not s: continue
        parts = re.split(r"(?<=[.!?:])\s+(?=[A-Z0-9\"'\-])", s)
        for p in parts:
            p = p.strip()
            if p: out.append(p)
    return out

def wc(s):
    return len([w for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-/]*", s)])

def count_ci(text, phrases):
    n = 0; hits = []
    low = text.lower()
    for ph in phrases:
        for m in re.finditer(r"(?<![a-z])" + re.escape(ph) + r"(?![a-z])", low):
            n += 1; hits.append(ph)
    return n, hits

def noun_trains(text):
    """Runs of 4+ consecutive non-function lowercase words (Rule 2.1 proxy).
    Heuristic marker only - proper nouns break a run, the leading word of each
    sentence is skipped, and the count stays out of the total."""
    hits = []
    for s in sentences(text):
        words = re.findall(r"[A-Za-z][A-Za-z'\-]*", s)[1:]
        run = []
        for w in words + [""]:
            if w and w.lower() not in FUNC_WORDS and not w[0].isupper():
                run.append(w)
            else:
                if len(run) >= 4: hits.append(" ".join(run))
                run = []
    return hits

def lint(text, strict=False):
    raw = text
    text = unwrap(strip_code(text))
    sents = sentences(text)
    words = sum(wc(s) for s in sents) or 1
    v = {}
    # Rule 5.1 caps an instruction at 20 words, rule 6.3 caps descriptive text
    # at 25. Strict mode is procedures, so it holds every sentence to 20.
    cap = 20 if strict else 25
    longs = [(wc(s), s) for s in sents if wc(s) > cap]
    v[f"long_sentence(>{cap}w)"] = len(longs)
    v["semicolon"] = text.count(";")
    # Bare 's is usually possessive ("the parser's output"), which STE permits.
    # It is a contraction only after the handful of words that take "is"/"has".
    v["contraction"] = len(re.findall(r"\b\w+['’](?:t|re|ve|ll|d|m)\b", text)) \
        + len(re.findall(r"\b(?:it|he|she|there|that|what|who|here|let)['’]s\b", text, re.I))
    passive_parts = re.findall(rf"\b{BE}\s+(\w+ed|{PP_IRREG})\b", text, re.I)
    v["passive_voice"] = sum(1 for p in passive_parts if not re.fullmatch(STATIVE, p, re.I)) \
        + len(re.findall(rf"\b{BE}\s+{STATIVE}\s+by\b", text, re.I))
    v["complex_tense"] = len(re.findall(
        rf"\b(?:(?:may|might|could|would|should|must|will|shall|can)\s+)?(?:have|has|had)\s+(?:been\s+)?(?:\w+ed|{PP_IRREG})\b",
        text, re.I))
    v["ing_main_verb"] = len(re.findall(rf"\b{BE}\s+\w+ing\b", text, re.I))
    v["nominalization"] = len(re.findall(r"\b(?:perform(?:s|ed)?|conduct(?:s|ed)?|carry out|carries out|make use of|makes use of)\b", text, re.I)) + len(re.findall(r"\b\w{4,}(?:tion|ment|ance|ence)\s+of\b", text, re.I))
    v["phrasal_verb"], _ = count_ci(text, PHRASAL)
    v["banned_word"], bh = count_ci(text, BANNED)
    v["marketing_adjective"], mh = count_ci(text, MARKETING)
    v["modal_hedge"], _ = count_ci(text, MODAL_HEDGE)
    paras = [p for p in re.split(r"\n\s*\n", raw) if p.strip()]
    v["long_paragraph(>6s)"] = sum(1 for p in paras if len(sentences(strip_code(p))) > 6)
    # The em dash is a house rule, not an ASD rule, so it is counted in both
    # modes. A dash inside code, a URL or a numeric range is not prose.
    em = len(re.findall(r"\s—|—\s|\s–|–\s", text)) + len(re.findall(r"(?<![\d\s])—(?![\d\s])", text))
    v["em_dash"] = em
    trains = noun_trains(text)
    if strict:
        n_strict, sh = count_ci(text, STRICT_BANNED)
        # "may" is matched case-sensitively so the month "May" stays clean
        n_strict += len(re.findall(r"(?<![A-Za-z])may(?![a-z])", text))
        v["strict_banned_word"] = n_strict
    total = sum(v.values())
    return {
        "score_version": SCORE_VERSION,
        "mode": "strict" if strict else "flavored",
        "words": words, "sentences": len(sents),
        "violations": v, "total": total,
        "total_per100w": round(total*100.0/words, 2),
        "em_dash": em,
        "noun_train(>=4w,marker)": len(trains),
        "longest_sentence_words": (max(longs)[0] if longs else max((wc(s) for s in sents), default=0)),
        "sample_marketing": list(dict.fromkeys(mh))[:6],
        "sample_banned": list(dict.fromkeys(bh))[:6],
        "sample_noun_train": trains[:3],
    }

if __name__ == "__main__":
    args = sys.argv[1:]
    strict = "--strict" in args
    as_json = "--json" in args
    fail_over = None
    if "--fail-over" in args:
        i = args.index("--fail-over")
        fail_over = float(args[i + 1])
        del args[i:i + 2]
    files = [a for a in args if a not in ("--strict", "--json")]
    worst = 0.0
    if not files:
        sys.stdin.reconfigure(encoding="utf-8")
        r = lint(sys.stdin.read(), strict=strict)
        print(json.dumps(r, indent=2))
        worst = r["total_per100w"]
    else:
        exp = []
        for f in files: exp += sorted(glob.glob(f)) if any(c in f for c in "*?[") else [f]
        for f in exp:
            with open(f, encoding="utf-8") as fh: r = lint(fh.read(), strict=strict)
            worst = max(worst, r["total_per100w"])
            if as_json:
                print(json.dumps({"file": f, **r}, indent=2))
            else:
                print(f"{os.path.basename(f):32} words={r['words']:4d} total={r['total']:3d} per100w={r['total_per100w']:6.2f} em_dash={r['em_dash']:2d}")
    if fail_over is not None and worst > fail_over:
        sys.exit(1)
