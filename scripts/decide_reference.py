#!/usr/bin/env python3
"""PyTorch reference outputs for 20 fixed inputs, for checking any other runtime of the decision models.

  decide_reference.py export/small export/medium REF

Runs both models in float32 on the CPU, one input at a time (no padding), and writes for each model
P and input k:

  P-k.ids      token ids, as written by the tokenizer ([CLS] text [SEP])
  P-k.pooled   mean of the final hidden states        [H]
  P-k.score    the 12 scores                          [12]
  P-k.gate     gate logits                            [5]
  P-k.type     statement-type logits                  [5]
  P-k.embed    the unit-length embedding              [256]
  P-k.span     per-token span logits                  [T, 13]
  P-k.conf     confidence logit                       [1]

Each as NAME.f32 (raw little-endian float32, row-major; ids as float32 too) with NAME.json giving its
shape, as Quartermaster's other reference tools do. inputs.json lists the 20 texts before and after
the text rule (white space collapsed, a leading dash dropped); the models read the normalized text.
"""
import json, os, sys
from pathlib import Path

import numpy as np
import torch
from safetensors.torch import load_file
from transformers import AutoConfig, AutoModel, AutoTokenizer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from multi_data import norm

# Invented examples covering the cases a runtime can get wrong: shorthand, slashes, long inputs past
# the 64-token sliding window, non-ASCII, a heading, a citation, a narrative, pushes and strats.
INPUTS = [
    "- Rebuilt sq deployment checklist; trained 30 Amn on new steps--cut acft generation time 25%/met short-notice wing tasking",
    "- Mgd sq trng prgm; tracked 45 mbrs' upgrade trng--ensured 100% compliance",
    "- Led 6-mbr tm f/3 sat handovers; coord'd w/2 sqs/41 prsnl--zero lost contacts, DEL msn rdy 2 days early",
    "Led a six-member team through three satellite handovers, coordinating with two squadrons and 41 personnel; no contacts were lost and the Delta was mission ready two days early.",
    "Phenomenal leader! My #1 TSgt of 12--promote now!",
    "#1 of 14 SSgts; rewired 3 radar shelters in 6 days--restored base approach control 2 wks early",
    "- Stellar ramp spt helped wg win AMC Maintenance Award--promote",
    "Athletically gifted; crushed intramural events--squadron kept the Golden Wrench trophy",
    "- Volunteered 20 hrs at family shelter; served meals to 30 patrons--provided vital needs to less fortunate citizens",
    "Completed Airman Leadership School; earned 94% average on all exams",
    "Bullet writing tips for your EPB",
    "   -   Supervises 5-mbr maint team;   performs daily acft insp--ensures flt line spt f/$2B wg fleet   ",
    "Repaired 12 HVAC units at the dining facility, restoring cooling for 1,200 Airmen during a 105°F heat wave and saving $48K in contract costs.",
    "- Drove “zero-defect” culture; re-wrote 14 TOs w/ new torque specs--cut rework 31% & saved 410 man-hrs",
    "Sergeant Doe distinguished himself by meritorious service as Section Chief, Vehicle Maintenance Flight, 99th Logistics Readiness Squadron. During this period, his leadership of a 22-member team kept 340 vehicles mission capable through two deployments and a wing inspection, and his rebuilt parts program cut repair times by 18 percent. The distinctive accomplishments of Sergeant Doe reflect credit upon himself and the United States Air Force.",
    "- Spearheaded base-wide cyber hygiene campaign; briefed 2.4K prsnl across 9 units, patched 610 workstations, closed 37 open findings, rewrote the wing's removable media policy, stood up a weekly scan review with the comm sq, and trained 18 unit cyber reps--wing passed CCRI w/ 'Excellent' rating, 0 cat I findings, and HHQ benchmarked the program for 4 other wings in the command",
    "ID'd 3 corrupted SATCOM keys; xfer'd to backup & rebooted terminals in 40 min--kept CENTCOM C2 link up",
    "Did stuff",
    "Organized squadron picnic for 300; secured $5K in donations--boosted morale",
    "- Spearheaded Delta's first OPIR data-tagging pipeline; automated 92% of 1.1M daily tracks--cut analyst workload 3K hrs/yr",
]


class Multi(torch.nn.Module):
    def __init__(self, cfg_dir):
        super().__init__()
        cfg = AutoConfig.from_pretrained(cfg_dir)
        cfg._attn_implementation = "eager"
        self.enc = AutoModel.from_config(cfg)
        H = cfg.hidden_size
        hj = json.load(open(os.path.join(cfg_dir, "heads.json")))
        self.score = torch.nn.Linear(H, len(hj["scores"])); self.gate = torch.nn.Linear(H, len(hj["gates"]))
        self.kind = torch.nn.Linear(H, len(hj["types"])); self.embed = torch.nn.Linear(H, hj["embed"])
        self.span = torch.nn.Linear(H, 13); self.conf = torch.nn.Linear(H, 1)

    def forward(self, ids):
        h = self.enc(input_ids=ids, attention_mask=torch.ones_like(ids)).last_hidden_state[0]
        p = h.mean(0)
        return {"pooled": p, "score": self.score(p), "gate": self.gate(p), "type": self.kind(p),
                "embed": torch.nn.functional.normalize(self.embed(p), dim=-1), "span": self.span(h), "conf": self.conf(p)}


def save(out: Path, name, arr):
    arr = np.ascontiguousarray(np.asarray(arr, dtype=np.float32))
    arr.tofile(out / f"{name}.f32")
    (out / f"{name}.json").write_text(json.dumps({"name": name, "shape": list(arr.shape), "source": {"kind": "pytorch"}}))


def main(small, medium, ref):
    out = Path(ref); out.mkdir(parents=True, exist_ok=True)
    texts = [norm(t) for t in INPUTS]
    (out / "inputs.json").write_text(json.dumps([{"k": k, "raw": r, "text": t} for k, (r, t) in enumerate(zip(INPUTS, texts))], indent=1, ensure_ascii=False), encoding="utf-8")
    torch.set_num_threads(4)
    for p, d in (("small", small), ("medium", medium)):
        m = Multi(d)
        m.load_state_dict(load_file(os.path.join(d, "model.safetensors")))
        m.eval()
        tok = AutoTokenizer.from_pretrained(d)
        with torch.no_grad():
            for k, t in enumerate(texts):
                ids = tok(t, truncation=True, max_length=128)["input_ids"]
                o = m(torch.tensor([ids]))
                save(out, f"{p}-{k:02d}.ids", ids)
                for key, v in o.items():
                    save(out, f"{p}-{k:02d}.{key}", v.numpy())
        print(p, "done", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])
