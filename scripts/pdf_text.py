"""Extract text from the reference PDFs into work/txt/*.txt."""
import sys
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
out = ROOT / "work" / "txt"
out.mkdir(parents=True, exist_ok=True)
for p in sys.argv[1:]:
    r = PdfReader(p)
    t = "\n\f\n".join((pg.extract_text() or "") for pg in r.pages)
    f = out / (Path(p).stem + ".txt")
    f.write_text(t, encoding="utf-8")
    print(f.name, len(r.pages), "pages", len(t), "chars")
