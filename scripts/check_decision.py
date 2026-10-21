#!/usr/bin/env python3
"""Run the decision models from the GGUF file in plain numpy and compare with the PyTorch reference.

  check_decision.py qm-decide-Q8_0.gguf REF [--tol-score 0.15]

This is the engine's specification in runnable form: it reads only the GGUF settings and tensors,
follows the layout convert_decision.py documents, and takes token ids from the reference (the
tokenizer is checked separately by the app's tests). For an f32 file the outputs should match the
reference to rounding; for q8_0 the scores should stay within --tol-score and every gate, type and
span tag should mostly agree. It prints one line per model and exits 1 if a check fails.
"""
import argparse, json, math, struct, sys
from pathlib import Path

import numpy as np

T_U8, T_I8, T_U16, T_I16, T_U32, T_I32, T_F32, T_BOOL, T_STR, T_ARR, T_U64, T_I64, T_F64 = range(13)


def read_gguf(path):
    data = Path(path).read_bytes()
    pos = 0
    def take(fmt):
        nonlocal pos
        v = struct.unpack_from(fmt, data, pos); pos += struct.calcsize(fmt)
        return v[0] if len(v) == 1 else v
    def s():
        nonlocal pos
        n = take("<Q"); v = data[pos:pos + n].decode("utf-8"); pos += n
        return v
    scal = {T_U8: "<B", T_I8: "<b", T_U16: "<H", T_I16: "<h", T_U32: "<I", T_I32: "<i", T_F32: "<f", T_BOOL: "<?", T_U64: "<Q", T_I64: "<q", T_F64: "<d"}
    def val(t):
        if t == T_STR:
            return s()
        if t == T_ARR:
            et, n = take("<I"), take("<Q")
            return [val(et) for _ in range(n)]
        return take(scal[t])
    assert data[:4] == b"GGUF"; pos = 4
    ver, nt, nkv = take("<I"), take("<Q"), take("<Q")
    kv = {}
    for _ in range(nkv):
        k = s(); kv[k] = val(take("<I"))
    infos = []
    for _ in range(nt):
        name = s(); nd = take("<I"); dims = [take("<Q") for _ in range(nd)]
        gt, off = take("<I"), take("<Q")
        infos.append((name, dims, gt, off))
    base = pos + (-pos) % 32
    ts = {}
    for name, dims, gt, off in infos:
        shape = list(reversed(dims)); n = int(np.prod(shape))
        if gt == 0:
            a = np.frombuffer(data, "<f4", n, base + off)
        elif gt == 8:
            b = np.frombuffer(data, np.uint8, n // 32 * 34, base + off).reshape(-1, 34)
            d = b[:, :2].copy().view("<f2").astype(np.float32)
            q = b[:, 2:].copy().view(np.int8).astype(np.float32)
            a = (q * d).reshape(-1)
        else:
            raise SystemExit(f"{name}: type {gt}")
        ts[name] = a.reshape(shape).astype(np.float32)
    return kv, ts


def layernorm(x, w, eps):
    m = x.mean(-1, keepdims=True); v = ((x - m) ** 2).mean(-1, keepdims=True)
    return (x - m) / np.sqrt(v + eps) * w


def gelu(x):
    from math import erf
    return 0.5 * x * (1.0 + np.vectorize(erf)(x / math.sqrt(2.0)))


def rope(x, theta):
    """x [heads, T, d]; rotate-half form."""
    T, d = x.shape[1], x.shape[2]
    inv = 1.0 / (theta ** (np.arange(0, d, 2, dtype=np.float32) / d))
    f = np.arange(T, dtype=np.float32)[:, None] * inv[None]
    emb = np.concatenate([f, f], -1)
    c, s = np.cos(emb), np.sin(emb)
    rot = np.concatenate([-x[..., d // 2:], x[..., :d // 2]], -1)
    return x * c + rot * s


def run(kv, ts, p, ids):
    k = f"qmdecide.{p}."
    H, L, NH, F = kv[k + "hidden"], kv[k + "layers"], kv[k + "heads"], kv[k + "ffn"]
    eps, th, th_s, full, wh = kv[k + "norm_eps"], kv[k + "rope_theta"], kv[k + "rope_theta_sliding"], kv[k + "layer_full"], kv[k + "window_half"]
    W = lambda n: ts[f"{p}.{n}"]
    x = layernorm(W("token_embd")[ids], W("token_embd_norm"), eps)
    T = len(ids); hd = H // NH
    dist = np.abs(np.arange(T)[:, None] - np.arange(T)[None])
    for i in range(L):
        b = f"blk.{i}."
        h = layernorm(x, W(b + "attn_norm"), eps) if i > 0 else x
        qkv = h @ W(b + "attn_qkv").T
        q, kk, v = [qkv[:, j * H:(j + 1) * H].reshape(T, NH, hd).transpose(1, 0, 2) for j in range(3)]
        t = th if full[i] else th_s
        q, kk = rope(q, t), rope(kk, t)
        a = q @ kk.transpose(0, 2, 1) / math.sqrt(hd)
        if not full[i]:
            a = np.where(dist[None] <= wh, a, -np.inf)
        a = np.exp(a - a.max(-1, keepdims=True)); a /= a.sum(-1, keepdims=True)
        o = (a @ v).transpose(1, 0, 2).reshape(T, H)
        x = x + o @ W(b + "attn_out").T
        h = layernorm(x, W(b + "ffn_norm"), eps)
        u = h @ W(b + "ffn_up").T
        x = x + (gelu(u[:, :F]) * u[:, F:]) @ W(b + "ffn_down").T
    x = layernorm(x, W("output_norm"), eps)
    pooled = x.mean(0)
    head = lambda n, z: z @ W(f"head.{n}.weight").T + W(f"head.{n}.bias")
    e = head("embed", pooled)
    return {"pooled": pooled, "score": head("score", pooled), "gate": head("gate", pooled), "type": head("type", pooled),
            "embed": e / np.linalg.norm(e), "span": head("span", x), "conf": head("conf", pooled)}


def load(ref, name):
    j = json.loads((ref / f"{name}.json").read_text())
    return np.fromfile(ref / f"{name}.f32", dtype="<f4").reshape(j["shape"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gguf"); ap.add_argument("ref")
    ap.add_argument("--tol-score", type=float, default=0.15)
    ap.add_argument("--models", default="small,medium")
    a = ap.parse_args()
    kv, ts = read_gguf(a.gguf)
    ref = Path(a.ref)
    n = len(json.loads((ref / "inputs.json").read_text(encoding="utf-8")))
    quant = kv["general.file_type"] == 7
    ok_all = True
    for p in a.models.split(","):
        worst = {k: 0.0 for k in ["pooled", "score", "gate", "type", "embed", "span", "conf"]}
        agree = {"gate": 0, "type": 0, "span_tok": 0, "span_n": 0}
        for k in range(n):
            ids = load(ref, f"{p}-{k:02d}.ids").astype(np.int64)
            got = run(kv, ts, p, ids)
            for key in worst:
                want = load(ref, f"{p}-{k:02d}.{key}")
                worst[key] = max(worst[key], float(np.abs(got[key] - want).max()))
            agree["gate"] += int(got["gate"].argmax() == load(ref, f"{p}-{k:02d}.gate").argmax())
            agree["type"] += int(got["type"].argmax() == load(ref, f"{p}-{k:02d}.type").argmax())
            ws = load(ref, f"{p}-{k:02d}.span")
            for lo, hi in ((0, 7), (7, 10), (10, 13)):
                agree["span_tok"] += int((got["span"][:, lo:hi].argmax(-1) == ws[:, lo:hi].argmax(-1)).sum())
                agree["span_n"] += ws.shape[0]
        span_rate = agree["span_tok"] / agree["span_n"]
        if quant:
            ok = worst["score"] <= a.tol_score and agree["gate"] >= n - 1 and agree["type"] >= n - 1 and span_rate >= 0.97
        else:
            ok = all(v < 2e-3 for v in worst.values())
        ok_all &= ok
        print(f"{p}: {'ok' if ok else 'FAILED'}  max |diff| " + " ".join(f"{k} {v:.4f}" for k, v in worst.items())
              + f"  gate {agree['gate']}/{n} type {agree['type']}/{n} span tags {span_rate:.3f}")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
