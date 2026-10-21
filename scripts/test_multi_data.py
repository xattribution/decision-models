"""Checks for multi_data: counts, the expander, and span tags round-tripping to the same char spans."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import multi_data as M
from transformers import AutoTokenizer

sc = M.scored()
print({k: len(v) for k, v in sc.items()})
ty = M.typed()
import collections
print({k: dict(collections.Counter(t for _, t in v)) for k, v in ty.items()})
sp = M.spans()
print({k: len(v) for k, v in sp.items()})
same = M.same_pairs()
print({k: len(v) for k, v in same.items()}, collections.Counter(s for *_, s in same["train"]))
ex = M.Expander()
print("expander terms", len(ex.map))
for t in ["Mgd sq trng prgm; tracked 45 mbrs' upgrade trng--ensured 100% compliance",
          "Led 6-mbr tm f/3 sat handovers; coord'd w/2 sqs/41 prsnl--zero lost contacts, DEL msn rdy 2 days early"]:
    print("  ", M.norm(ex(t)))
n = sum(ex(r["text"]) != r["text"] for r in sc["train"])
print("train items the expander changes:", n, "of", len(sc["train"]))

tok = AutoTokenizer.from_pretrained("jhu-clsp/ettin-encoder-68m")
ok = bad = 0
for text, s in sp["train"] + sp["val"]:
    ids, o, scp, num, off = M.span_tags(tok, text, s, 128)
    back = M.decode_spans(text, off, o, scp, num)
    for f in s:
        want = sorted(tuple(x) for x in s[f])
        got = sorted(tuple(x) for x in back[f])
        # a piece that ends inside a token comes back to the token's end; compare text, trimmed
        w = [text[a:b].strip(" ;,.-") for a, b in want]
        g = [text[a:b].strip(" ;,.-") for a, b in got]
        if w == g:
            ok += 1
        else:
            bad += 1
            if bad <= 5:
                print("MISMATCH", f, w, g)
print("span fields round-trip", ok, "bad", bad)
