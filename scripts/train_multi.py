"""The multi-head decision model: one Ettin encoder, every output the app reads.

  train_multi.py teach   --base jhu-clsp/ettin-encoder-400m --name m400
  train_multi.py distill --base jhu-clsp/ettin-encoder-68m  --teacher work/multi/m400.pt --name s68
  train_multi.py direct  --base jhu-clsp/ettin-encoder-68m  --name d68      (same recipe as teach, for comparison)
  train_multi.py eval    --ckpt work/multi/m400.pt

Heads, on the mean of the last hidden states (spans on each token):
  score  12 values: structure action impact result quantified scope credibility readability clipping tone level overall
  gate   pass not_a_bullet incomplete nonsense banned
  type   bullet narrative citation push strat
  embed  256 numbers, unit length; statements that say the same thing sit close
  spans  per token: B/I tags for action, impact, result (one layer), scope (one), numbers (one)
  conf   the small model's chance of agreeing with the medium one (distill only; cascade)

teach/direct: stage 1 synthetic pairs (logistic on structure, the content mean, impact) and same-meaning
pairs; stage 2 every task: the panel key, types, spans, same-meaning pairs. A quarter of scored texts
are spelled out first (the app spells abbreviations out before scoring); clipping isn't taught on those.
distill: stage 1 as above, then the student matches the teacher on the bank's train split plus the
real labels; then the conf head learns agreement on bank items the student never saw.
"""
import argparse, hashlib, json, math, os, random, sys, time

import numpy as np
import torch
import torch.nn.functional as F
from scipy.stats import spearmanr
from transformers import AutoModel, AutoTokenizer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import multi_data as M

ROOT = M.ROOT
OUT = os.path.join(ROOT, "work", "multi")
MAXLEN = 128
EMB = 256
NS = len(M.SCORES)
CLIP = M.SCORES.index("clipping")
SYN_HEAD = {"structure": [0], "content": M.CONTENT_IDX, "impact": [2]}
SYN_SETS = {"structure": "structure,nmstruct", "content": "content,nmcontent", "impact": "nmimpact"}
# How often a bank source is drawn when the student learns from the teacher, and why.
SOURCE_WEIGHT = {
    "ussf-bank": (1.5, "current Space Force bullet format, the forms the app fills"),
    "github/justinthelaw/opera": (0.5, "every slash was stripped upstream, so words run together"),
    "reddit.com": (0.3, "forum text; many lines are not statements"),
}


class Multi(torch.nn.Module):
    def __init__(self, base):
        super().__init__()
        self.enc = AutoModel.from_pretrained(base)
        H = self.enc.config.hidden_size
        self.score = torch.nn.Linear(H, NS)
        self.gate = torch.nn.Linear(H, len(M.GATES))
        self.kind = torch.nn.Linear(H, len(M.TYPES))  # statement type ("type" would hide Module.type)
        self.embed = torch.nn.Linear(H, EMB)
        self.span = torch.nn.Linear(H, 7 + 3 + 3)
        self.conf = torch.nn.Linear(H, 1)

    def forward(self, ids, mask):
        h = self.enc(input_ids=ids, attention_mask=mask).last_hidden_state
        m = mask.unsqueeze(-1).to(h.dtype)
        p = (h * m).sum(1) / m.sum(1)
        return {"score": self.score(p), "gate": self.gate(p), "type": self.kind(p),
                "embed": F.normalize(self.embed(p).float(), dim=-1), "span": self.span(h), "conf": self.conf(p).squeeze(-1),
                "pooled": p}


def synth_pairs():
    from train_head import synth_pairs as sp
    out = []
    for dim, sets in SYN_SETS.items():
        for hi, lo, gap in sp(sets):
            out.append((M.norm(hi), M.norm(lo), dim))
    return out


class Trainer:
    def __init__(self, a):
        self.a = a
        random.seed(a.seed); torch.manual_seed(a.seed)
        self.dev = "cuda"
        self.tok = AutoTokenizer.from_pretrained(a.base)
        self.model = Multi(a.base).to(self.dev)
        self.exp = M.Expander()
        self.sc = M.scored()
        self.ty = M.typed()
        self.sp = M.spans()
        self.same = M.same_pairs()
        self.t0 = time.time()
        # type sampling: equal chance per class
        self.ty_by = {}
        for t, c in self.ty["train"]:
            self.ty_by.setdefault(c, []).append(t)
        print(f"scored {len(self.sc['train'])} types {len(self.ty['train'])} spans {len(self.sp['train'])} "
              f"same {len(self.same['train'])}", flush=True)

    def enc(self, xs):
        return self.tok(list(xs), padding=True, truncation=True, max_length=MAXLEN, return_tensors="pt").to(self.dev)

    def fwd(self, xs):
        x = self.enc(xs)
        return self.model(x.input_ids, x.attention_mask)

    # ---- losses ----
    def loss_scored(self, b):
        texts, ys, gs = [], [], []
        for r in b:
            t, y = r["text"], list(r["scores"])
            if random.random() < 0.25:
                t2 = M.norm(self.exp(t))
                if t2 != t:
                    t, y[CLIP] = t2, float("nan")
            texts.append(t); ys.append(y); gs.append(r["gate"])
        o = self.fwd(texts)
        y = torch.tensor(ys, device=self.dev)
        ok = ~torch.isnan(y)
        d = (o["score"].float() - torch.nan_to_num(y)) ** 2
        ls = (d * ok).sum() / ok.sum().clamp(min=1)
        lg = F.cross_entropy(o["gate"].float(), torch.tensor(gs, device=self.dev), ignore_index=-100)
        return ls + 0.5 * lg

    def loss_type(self, n=16):
        cls = list(self.ty_by)
        b = [(random.choice(self.ty_by[c]), c) for c in random.choices(cls, k=n)]
        o = self.fwd([t for t, _ in b])
        return F.cross_entropy(o["type"].float(), torch.tensor([c for _, c in b], device=self.dev))

    def span_batch(self, rows):
        ids, tags = [], []
        for text, s in rows:
            i, oo, ss, nn, _ = M.span_tags(self.tok, text, s, MAXLEN)
            ids.append(i); tags.append((oo, ss, nn))
        L = max(map(len, ids))
        pad = self.tok.pad_token_id
        X = torch.full((len(ids), L), pad); A = torch.zeros((len(ids), L), dtype=torch.long)
        T = torch.full((3, len(ids), L), -100)
        for k, i in enumerate(ids):
            X[k, :len(i)] = torch.tensor(i); A[k, :len(i)] = 1
            for j in range(3):
                T[j, k, :len(i)] = torch.tensor(tags[k][j])
        return X.to(self.dev), A.to(self.dev), T.to(self.dev)

    def loss_spans(self, n=16):
        if not self.sp["train"]:
            return torch.zeros((), device=self.dev)
        X, A, T = self.span_batch(random.sample(self.sp["train"], min(n, len(self.sp["train"]))))
        lg = self.model(X, A)["span"].float()
        l = F.cross_entropy(lg[..., :7].reshape(-1, 7), T[0].reshape(-1), ignore_index=-100)
        l = l + 0.5 * F.cross_entropy(lg[..., 7:10].reshape(-1, 3), T[1].reshape(-1), ignore_index=-100)
        l = l + 0.5 * F.cross_entropy(lg[..., 10:].reshape(-1, 3), T[2].reshape(-1), ignore_index=-100)
        return l

    def loss_same(self, n=32, extra=None):
        b = random.sample(self.same["train"], n)
        # spelled-out copies are the same statement too
        if extra:
            for r in random.sample(extra, n // 2):
                t2 = M.norm(self.exp(r["text"]))
                if t2 != r["text"]:
                    b.append((r["text"], t2, "exp"))
        ea = self.fwd([x[0] for x in b])["embed"]; eb = self.fwd([x[1] for x in b])["embed"]
        s = ea @ eb.T / 0.05
        lab = torch.arange(len(b), device=self.dev)
        return (F.cross_entropy(s, lab) + F.cross_entropy(s.T, lab)) / 2

    def loss_synth(self, b):
        hi = self.fwd([p[0] for p in b])["score"].float(); lo = self.fwd([p[1] for p in b])["score"].float()
        d = []
        for k, p in enumerate(b):
            idx = SYN_HEAD[p[2]]
            d.append(hi[k, idx].mean() - lo[k, idx].mean())
        return F.softplus(-torch.stack(d)).mean()

    # ---- phases ----
    def run(self, steps, step_fn, lr, tag, params=None):
        params = params or [p for p in self.model.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.01)
        sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, s / max(1, steps // 10)) * max(0.0, 1 - s / steps))
        self.model.train()
        for s in range(steps):
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss, parts = step_fn(s)
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step(); sched.step()
            if s % 200 == 0:
                print(f"{tag} {s}/{steps} loss {loss.item():.3f} {parts} {time.time() - self.t0:.0f}s", flush=True)

    def stage1(self):
        pairs = synth_pairs()
        random.shuffle(pairs)
        bs = 32
        steps = len(pairs) // bs
        print("synthetic pairs", len(pairs), flush=True)
        def step(s):
            b = pairs[s * bs:(s + 1) * bs]
            l1 = self.loss_synth(b)
            l2 = self.loss_same(16)
            return l1 + 0.3 * l2, f"synth {l1.item():.3f} same {l2.item():.3f}"
        self.run(steps, step, self.a.lr, "stage1")

    def stage2(self, epochs, extra_fn=None):
        tr = self.sc["train"]
        steps = epochs * len(tr) // 16
        def step(s):
            ls = self.loss_scored(random.sample(tr, 16))
            lt = self.loss_type()
            lp = self.loss_spans()
            le = self.loss_same(32, extra=tr)
            loss = ls + 0.3 * lt + 0.5 * lp + 0.3 * le
            parts = f"sc {ls.item():.3f} ty {lt.item():.3f} sp {lp.item():.3f} same {le.item():.3f}"
            if extra_fn:
                lx, px = extra_fn(s)
                loss = loss + lx; parts += " " + px
            return loss, parts
        self.run(steps, step, self.a.lr, "stage2")

    def save(self, name, extra=None):
        os.makedirs(OUT, exist_ok=True)
        p = os.path.join(OUT, name + ".pt")
        torch.save(self.model.state_dict(), p)
        cfg = {"base": self.a.base, "scores": M.SCORES, "gates": M.GATES, "types": M.TYPES, "span_tags": M.SPAN_TAGS,
               "embed": EMB, "max_len": MAXLEN, "norm": "collapse white space; drop a leading dash or bullet mark",
               "source_weight": {k: v[0] for k, v in SOURCE_WEIGHT.items()}}
        cfg.update(extra or {})
        json.dump(cfg, open(os.path.join(OUT, name + ".json"), "w"), indent=1)
        print("saved", p, flush=True)


def load_model(ckpt, dev="cuda"):
    cfg = json.load(open(ckpt[:-3] + ".json"))
    m = Multi(cfg["base"]).to(dev)
    m.load_state_dict(torch.load(ckpt, map_location=dev))
    m.eval()
    return m, cfg


@torch.no_grad()
def predict(model, tok, texts, dev="cuda", bs=64):
    out = {k: [] for k in ["score", "gate", "type", "embed", "conf"]}
    for i in range(0, len(texts), bs):
        x = tok(list(texts[i:i + bs]), padding=True, truncation=True, max_length=MAXLEN, return_tensors="pt").to(dev)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            o = model(x.input_ids, x.attention_mask)
        for k in out:
            out[k].append(o[k].float().cpu())
    return {k: torch.cat(v).numpy() for k, v in out.items()}


@torch.no_grad()
def predict_spans(model, tok, texts, dev="cuda"):
    res = []
    for t in texts:
        e = tok(t, truncation=True, max_length=MAXLEN, return_offsets_mapping=True)
        x = torch.tensor([e["input_ids"]], device=dev)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            lg = model(x, torch.ones_like(x))["span"][0].float()
        o = lg[:, :7].argmax(-1).tolist(); s = lg[:, 7:10].argmax(-1).tolist(); n = lg[:, 10:].argmax(-1).tolist()
        res.append(M.decode_spans(t, e["offset_mapping"], o, s, n))
    return res


def evaluate(model, tok, name="", dev="cuda", expand=False):
    """Every head on held-out data. Returns a dict and prints a short table."""
    ex = M.Expander() if expand else None
    sc = M.scored()
    R = {"name": name, "expanded": expand}
    for split in ["val", "r4test"]:
        rows = sc[split]
        texts = [M.norm(ex(r["text"])) if ex else r["text"] for r in rows]
        p = predict(model, tok, texts, dev)
        Y = np.array([r["scores"] for r in rows])
        d = {}
        for k, s in enumerate(M.SCORES):
            ok = ~np.isnan(Y[:, k])
            d[s] = round(float(spearmanr(p["score"][ok, k], Y[ok, k]).correlation), 3)
        cm = Y[:, M.CONTENT_IDX].mean(1); ok = ~np.isnan(cm)
        d["content"] = round(float(spearmanr(p["score"][ok][:, M.CONTENT_IDX].mean(1), cm[ok]).correlation), 3)
        g = np.array([r["gate"] for r in rows]); okg = g >= 0
        pg = p["gate"].argmax(1)
        d["gate_acc"] = round(float((pg[okg] == g[okg]).mean()), 3)
        d["pass_vs_fail_acc"] = round(float(((pg[okg] == 0) == (g[okg] == 0)).mean()), 3)
        R[split] = d
    ty = M.typed()
    for split in ["val", "test"]:
        rows = ty[split]
        p = predict(model, tok, [t for t, _ in rows], dev)["type"].argmax(1)
        y = np.array([c for _, c in rows])
        R[f"type_{split}"] = {M.TYPES[c]: round(float((p[y == c] == c).mean()), 3) for c in sorted(set(y))}
    sp = M.spans()["val"]
    if sp:
        got = predict_spans(model, tok, [t for t, _ in sp], dev)
        f1 = {}
        for f in ["action", "impact", "result", "scope", "numbers"]:
            tp = fp = fn = 0
            for (t, s), g in zip(sp, got):
                want = {t[a:b].strip(" ;,.-") for a, b in s.get(f, [])}
                have = {t[a:b].strip(" ;,.-") for a, b in g.get(f, [])}
                tp += len(want & have); fp += len(have - want); fn += len(want - have)
            f1[f] = round(2 * tp / max(1, 2 * tp + fp + fn), 3)
        R["span_exact_f1"] = f1
    same = M.same_pairs()["val"]
    ea = predict(model, tok, [x[0] for x in same], dev)["embed"]; eb = predict(model, tok, [x[1] for x in same], dev)["embed"]
    s = ea @ eb.T
    R["same_recall_at_1"] = round(float((s.argmax(1) == np.arange(len(same))).mean()), 3)
    R["same_n"] = len(same)
    print(json.dumps(R), flush=True)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "results.jsonl"), "a") as f:
        f.write(json.dumps(R) + "\n")
    return R


def bank_texts(seed=3):
    """Bank train texts with their source weight, split by a hash into distill (85%) and calibration (15%)."""
    df = M.bank()
    df = df[df.split == "train"]
    dist, cal = [], []
    for t, src in zip(df.text, df.source):
        t = M.norm(t)
        w = SOURCE_WEIGHT.get(src, (1.0,))[0]
        h = int(hashlib.sha1(t.encode()).hexdigest()[:8], 16) % 100
        (cal if h < 15 else dist).append((t, w))
    return dist, cal


def distill(a):
    T = Trainer(a)
    teacher, tcfg = load_model(a.teacher)
    for p in teacher.parameters():
        p.requires_grad_(False)
    T.stage1()
    dist, cal = bank_texts()
    w = np.array([x[1] for x in dist]); w = w / w.sum()
    print(f"distill on {len(dist)} bank texts, calibrate on {len(cal)}", flush=True)
    model, dev, tok = T.model, T.dev, T.tok
    expander = T.exp

    def kl(s, t):
        return F.kl_div(F.log_softmax(s.float(), -1), F.softmax(t.float(), -1), reduction="batchmean")

    def extra(s):
        idx = np.random.choice(len(dist), 32, p=w)
        texts = [dist[i][0] for i in idx]
        texts = [M.norm(expander(t)) if random.random() < 0.25 else t for t in texts]
        x = T.enc(texts)
        with torch.no_grad():
            to = teacher(x.input_ids, x.attention_mask)
        so = model(x.input_ids, x.attention_mask)
        l = F.mse_loss(so["score"].float(), to["score"].float())
        l = l + 0.5 * kl(so["gate"], to["gate"]) + 0.3 * kl(so["type"], to["type"])
        l = l + 0.5 * (1 - (so["embed"] * to["embed"]).sum(-1)).mean()
        m = x.attention_mask.bool()
        ss, ts = so["span"].float()[m], to["span"].float()[m]
        l = l + 0.5 * (kl(ss[:, :7], ts[:, :7]) + 0.5 * kl(ss[:, 7:10], ts[:, 7:10]) + 0.5 * kl(ss[:, 10:], ts[:, 10:]))
        return a.dw * l, f"kd {l.item():.3f}"

    # the stage-2 schedule runs epochs * scored/16 steps; set epochs so the bank is seen about a.kd_epochs times
    steps_wanted = int(a.kd_epochs * len(dist) / 32)
    ep = max(1, round(steps_wanted * 16 / len(T.sc["train"])))
    T.stage2(ep, extra_fn=extra)
    T.save(a.name + "_nocal", {"teacher": a.teacher})
    calibrate(T, teacher, cal, a)


def agree(so, to):
    """The small model agrees when its overall score is within 0.5 of the medium one's and the gate matches.
    (Requiring all 11 scores within 0.5 held for only a third of items, and no signal could pick them.)"""
    ov = M.SCORES.index("overall")
    d = (so["score"][:, ov] - to["score"][:, ov]).abs()
    return (d <= 0.5) & (so["gate"].argmax(1) == to["gate"].argmax(1))


def calibrate(T, teacher, cal, a):
    """Train the conf head (encoder frozen) to predict agreement with the teacher, then pick the threshold."""
    model, dev = T.model, T.dev
    rnd = random.Random(5)
    rnd.shuffle(cal)
    held = cal[: len(cal) // 3]
    fit = cal[len(cal) // 3:]
    def labels(texts):
        x = T.enc(texts)
        with torch.no_grad():
            to = teacher(x.input_ids, x.attention_mask)
            so = model(x.input_ids, x.attention_mask)
        return so["pooled"].float(), agree({k: v.float() for k, v in so.items()}, {k: v.float() for k, v in to.items()}).float()
    for p in model.parameters():
        p.requires_grad_(False)
    model.conf.weight.requires_grad_(True); model.conf.bias.requires_grad_(True)
    opt = torch.optim.AdamW(model.conf.parameters(), lr=1e-3)
    model.eval()
    for ep in range(3):
        rnd.shuffle(fit)
        for i in range(0, len(fit) - 63, 64):
            texts = [M.norm(T.exp(t)) if rnd.random() < 0.25 else t for t, _ in fit[i:i + 64]]
            with torch.autocast("cuda", dtype=torch.bfloat16):
                pooled, y = labels(texts)
            lo = model.conf(pooled.to(model.conf.weight.dtype)).squeeze(-1).float()
            loss = F.binary_cross_entropy_with_logits(lo, y)
            opt.zero_grad(); loss.backward(); opt.step()
        print(f"conf ep {ep} loss {loss.item():.3f}", flush=True)
    # threshold on the held third: the lowest confidence whose answered items agree at least a.target of the time
    texts = [t for t, _ in held]
    ys, cs = [], []
    for i in range(0, len(texts), 64):
        with torch.autocast("cuda", dtype=torch.bfloat16):
            x = T.enc(texts[i:i + 64])
            with torch.no_grad():
                to = teacher(x.input_ids, x.attention_mask); so = model(x.input_ids, x.attention_mask)
        ys.append(agree({k: v.float() for k, v in so.items()}, {k: v.float() for k, v in to.items()}).cpu())
        cs.append(torch.sigmoid(so["conf"].float()).cpu())
    y = torch.cat(ys).numpy(); c = torch.cat(cs).numpy()
    order = np.argsort(-c)
    cum = np.cumsum(y[order]) / np.arange(1, len(y) + 1)
    curve = []
    for frac in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        k = max(1, int(frac * len(y))) - 1
        curve.append({"answered": frac, "agree": round(float(cum[k]), 3), "conf": round(float(c[order][k]), 3)})
    ok = np.where(cum >= a.target)[0]
    k = int(ok.max()) if len(ok) else 0
    thr = float(c[order][k])
    res = {"base_agree": round(float(y.mean()), 3), "threshold": round(thr, 4), "answered_by_small": round((k + 1) / len(y), 3),
           "target_agree": a.target, "curve": curve, "n_held": len(y)}
    print("cascade", json.dumps(res), flush=True)
    T.save(a.name, {"teacher": a.teacher, "cascade": res})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["teach", "direct", "distill", "calibrate", "eval"])
    ap.add_argument("--base", default="jhu-clsp/ettin-encoder-400m")
    ap.add_argument("--name", default="m400")
    ap.add_argument("--teacher", default="")
    ap.add_argument("--ckpt", default="")
    ap.add_argument("--epochs", type=int, default=4, help="stage-2 passes over the scored items")
    ap.add_argument("--kd-epochs", dest="kd_epochs", type=float, default=2.0)
    ap.add_argument("--dw", type=float, default=1.0, help="weight of the teacher-matching loss")
    ap.add_argument("--target", type=float, default=0.9, help="agreement the small model must keep on what it answers")
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--no-stage1", dest="stage1", action="store_false")
    a = ap.parse_args()
    if a.mode == "eval":
        m, cfg = load_model(a.ckpt)
        tok = AutoTokenizer.from_pretrained(cfg["base"])
        name = os.path.basename(a.ckpt)[:-3]
        evaluate(m, tok, name)
        evaluate(m, tok, name, expand=True)
        return
    if a.mode == "calibrate":
        # rerun only the cascade step on a distilled student (--ckpt work/multi/NAME_nocal.pt)
        T = Trainer(a)
        T.model.load_state_dict(torch.load(a.ckpt, map_location="cuda"))
        teacher, _ = load_model(a.teacher)
        for p in teacher.parameters():
            p.requires_grad_(False)
        calibrate(T, teacher, bank_texts()[1], a)
    elif a.mode == "distill":
        distill(a)
    else:
        T = Trainer(a)
        if a.stage1:
            T.stage1()
        T.stage2(a.epochs)
        T.save(a.name)
    m, cfg = load_model(os.path.join(OUT, a.name + ".pt"))
    tok = AutoTokenizer.from_pretrained(cfg["base"])
    evaluate(m, tok, a.name)
    evaluate(m, tok, a.name, expand=True)


if __name__ == "__main__":
    main()
