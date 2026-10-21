"""Replace one exact string in a file (UTF-8): python sub.py FILE OLD NEW"""
import sys
p, old, new = sys.argv[1:4]
s = open(p, encoding="utf-8").read()
n = s.count(old)
if n != 1:
    sys.exit(f"{old!r} found {n} times in {p}")
open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new))
print("ok")
