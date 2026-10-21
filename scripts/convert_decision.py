#!/usr/bin/env python3
"""Pack Quartermaster's two decision models into one GGUF file.

The decision models grade evaluation, award and decoration statements on the
computer: rubric scores, the pass/fail gate, statement type, the parts of the
statement (action, impact, result, scope, numbers) and an embedding for
finding statements that say the same thing. Two Ettin encoders (ModernBERT
architecture) with the same word pieces and the same outputs go in one file:
a small one (68M) that answers when it's confident and a medium one (400M)
that takes the rest. The confidence threshold between them is in the file.

It needs only Python 3.10+ and numpy: it reads the safetensors files itself
(a JSON header and raw numbers, nothing that can run code).

Usage:

    python convert_decision.py export/small export/medium
    python convert_decision.py export/small export/medium --type f32 --out decide-f32.gguf

Each folder holds model.safetensors, config.json (Ettin's) and heads.json
(the heads' settings, written by export_st.py), and tokenizer.json. --type is
q8_0 (the default) or f32. q8_0 stores the encoder's matrices, embeddings
included, as 8-bit blocks; norms and the output heads stay f32. The script
prints the output file's SHA-256 and the sources'.

Layout, for P in small and medium (N counts layers from 0):

    P.token_embd        [V, H]     token embeddings
    P.token_embd_norm   [H]        LayerNorm weight, no bias
    P.blk.N.attn_norm   [H]        absent for N = 0 (no norm before the first attention)
    P.blk.N.attn_qkv    [3H, H]    rows: all query heads, then keys, then values
    P.blk.N.attn_out    [H, H]
    P.blk.N.ffn_norm    [H]
    P.blk.N.ffn_up      [2F, H]    first F rows go through GELU (erf), times the last F rows
    P.blk.N.ffn_down    [H, F]
    P.output_norm       [H]
    P.head.score|gate|type|embed|span|conf.weight [n, H] and .bias [n]

Every LayerNorm has eps qmdecide.P.norm_eps and no bias. Attention uses
rotary positions (rotate-half form, theta qmdecide.P.rope_theta) on queries
and keys; layers marked 0 in qmdecide.P.layer_full attend only to tokens
within qmdecide.P.window_half positions either side. The heads read the
mean of the final hidden states over the real tokens ([CLS] and [SEP]
included); span reads each token. embed is L2-normalized after its bias;
conf goes through a sigmoid.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np

GGML_F32, GGML_F16, GGML_Q8_0 = 0, 1, 8
FILE_TYPE = {"f32": 0, "f16": 1, "q8_0": 7}  # llama.cpp's LlamaFileType numbers
T_U8, T_I8, T_U16, T_I16, T_U32, T_I32, T_F32, T_BOOL, T_STR, T_ARR, T_U64, T_I64, T_F64 = range(13)
TOK_NORMAL, TOK_UNKNOWN, TOK_CONTROL, TOK_USER, TOK_UNUSED, TOK_BYTE = 1, 2, 3, 4, 5, 6
ALIGN = 32
HEADS = ["score", "gate", "type", "embed", "span", "conf"]
HEAD_SRC = {"score": "score", "gate": "gate", "type": "kind", "embed": "embed", "span": "span", "conf": "conf"}


# ------------------------------------------------ GGUF writer (as in Quartermaster's tools/convert_nemo.py)


class GGUF:
    """A small GGUF v3 writer: settings first, then tensors, 32-byte aligned."""

    def __init__(self, arch: str):
        self.kv: list[tuple[str, int, object, int]] = []
        self.tensors: list[tuple[str, np.ndarray, int]] = []
        self.add("general.architecture", T_STR, arch)

    def add(self, key, vtype, value, etype=-1):
        if any(k == key for k, *_ in self.kv):
            raise ValueError(f"setting {key} written twice")
        self.kv.append((key, vtype, value, etype))

    def u32(self, k, v): self.add(k, T_U32, int(v))
    def i32(self, k, v): self.add(k, T_I32, int(v))
    def f32(self, k, v): self.add(k, T_F32, float(v))
    def bool(self, k, v): self.add(k, T_BOOL, bool(v))
    def str(self, k, v): self.add(k, T_STR, str(v))
    def strs(self, k, v): self.add(k, T_ARR, [str(x) for x in v], T_STR)
    def i32s(self, k, v): self.add(k, T_ARR, [int(x) for x in v], T_I32)
    def f32s(self, k, v): self.add(k, T_ARR, [float(x) for x in v], T_F32)

    def tensor(self, name, arr, gtype):
        if any(n == name for n, *_ in self.tensors):
            raise ValueError(f"tensor {name} written twice")
        self.tensors.append((name, arr, gtype))

    @staticmethod
    def _s(s):
        b = s.encode("utf-8")
        return struct.pack("<Q", len(b)) + b

    def _value(self, vtype, v, etype):
        if vtype == T_STR:
            return self._s(v)
        if vtype == T_ARR:
            out = struct.pack("<IQ", etype, len(v))
            if etype == T_STR:
                return out + b"".join(self._s(x) for x in v)
            fmt = {T_I32: "<i", T_U32: "<I", T_F32: "<f", T_F64: "<d"}[etype]
            return out + b"".join(struct.pack(fmt, x) for x in v)
        fmt = {T_U32: "<I", T_I32: "<i", T_F32: "<f", T_BOOL: "<?", T_U64: "<Q", T_F64: "<d"}[vtype]
        return struct.pack(fmt, v)

    def write(self, path: Path) -> str:
        infos, offset = [], 0
        for name, arr, gtype in self.tensors:
            dims = list(reversed(arr.shape)) or [1]
            info = self._s(name) + struct.pack("<I", len(dims))
            info += b"".join(struct.pack("<Q", d) for d in dims)
            info += struct.pack("<IQ", gtype, offset)
            infos.append(info)
            offset += encoded_size(arr, gtype)
            offset += (-offset) % ALIGN
        head = b"GGUF" + struct.pack("<IQQ", 3, len(self.tensors), len(self.kv))
        for k, vtype, v, etype in self.kv:
            head += self._s(k) + struct.pack("<I", vtype) + self._value(vtype, v, etype)
        head += b"".join(infos)
        head += b"\0" * ((-len(head)) % ALIGN)
        h = hashlib.sha256()
        tmp = path.with_name(path.name + ".part")
        with open(tmp, "wb") as f:
            f.write(head); h.update(head)
            for _, arr, gtype in self.tensors:
                d = encode(arr, gtype)
                if len(d) != encoded_size(arr, gtype):
                    raise ValueError("encoded size mismatch")
                pad = b"\0" * ((-len(d)) % ALIGN)
                f.write(d); f.write(pad); h.update(d); h.update(pad)
        tmp.replace(path)
        return h.hexdigest()


def q8_0(arr):
    """ggml's Q8_0: each run of 32 values becomes a float16 scale and 32 int8s,
    rounded half away from zero as ggml's roundf does."""
    x = np.ascontiguousarray(arr, dtype=np.float32).reshape(-1, 32)
    amax = np.abs(x).max(axis=1, keepdims=True)
    d = amax / 127.0
    inv = np.divide(1.0, d, out=np.zeros_like(d), where=d != 0)
    v = x * inv
    q = (np.sign(v) * np.floor(np.abs(v) + 0.5)).astype(np.int8)
    out = np.empty((x.shape[0], 34), dtype=np.uint8)
    out[:, :2] = d.astype("<f2").view(np.uint8).reshape(-1, 2)
    out[:, 2:] = q.view(np.uint8)
    return out.tobytes()


def encoded_size(arr, gtype):
    n = int(arr.size)
    if gtype == GGML_Q8_0:
        if n % 32:
            raise ValueError("Q8_0 needs whole blocks of 32")
        return n // 32 * 34
    return n * {GGML_F32: 4, GGML_F16: 2}[gtype]


def encode(arr, gtype):
    if gtype == GGML_F32:
        return np.ascontiguousarray(arr, dtype="<f4").tobytes()
    if gtype == GGML_Q8_0:
        return q8_0(arr)
    return np.ascontiguousarray(arr, dtype=np.float32).astype("<f2").tobytes()


# ------------------------------------------------ inputs


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_safetensors(path: Path) -> dict[str, np.ndarray]:
    data = path.read_bytes()
    (n,) = struct.unpack("<Q", data[:8])
    if n > len(data) - 8 or n > 100 << 20:
        raise SystemExit(f"{path}: not a safetensors file")
    head = json.loads(data[8:8 + n])
    base = 8 + n
    out = {}
    for k, v in head.items():
        if k == "__metadata__":
            continue
        a, b = v["data_offsets"]
        if not (0 <= a <= b <= len(data) - base):
            raise SystemExit(f"{path}: {k} lies outside the file")
        raw = data[base + a:base + b]
        dt = v["dtype"]
        if dt == "BF16":
            arr = (np.frombuffer(raw, "<u2").astype(np.uint32) << 16).view(np.float32)
        elif dt == "F16":
            arr = np.frombuffer(raw, "<f2").astype(np.float32)
        elif dt == "F32":
            arr = np.frombuffer(raw, "<f4").astype(np.float32)
        else:
            raise SystemExit(f"{path}: {k} has type {dt}")
        if arr.size != int(np.prod(v["shape"], dtype=np.int64)):
            raise SystemExit(f"{path}: {k} has the wrong size")
        out[k] = arr.reshape(v["shape"])
    return out


class Emitter:
    def __init__(self, g, sd, qtype):
        self.g, self.sd, self.qtype, self.used = g, sd, qtype, set()

    def arr(self, key, shape=None):
        if key not in self.sd:
            raise SystemExit(f"the model has no {key}")
        a = self.sd[key]
        if shape is not None and tuple(a.shape) != tuple(shape):
            raise SystemExit(f"{key} is {tuple(a.shape)}, want {tuple(shape)}")
        self.used.add(key)
        return np.ascontiguousarray(a, dtype=np.float32)

    def move(self, key, name, shape=None, quant=True):
        a = self.arr(key, shape)
        q = quant and self.qtype == "q8_0" and a.ndim == 2 and a.shape[0] >= 64 and a.shape[1] % 32 == 0
        self.g.tensor(name, a, GGML_Q8_0 if q else GGML_F32)
        return a

    def check_all_used(self):
        left = sorted(k for k in self.sd if k not in self.used)
        if left:
            raise SystemExit(f"{len(left)} weights were not converted, for example {left[:5]}")


def model(g, qtype, d: Path, p: str, labels: dict):
    cfg = json.loads((d / "config.json").read_text(encoding="utf-8"))
    hj = json.loads((d / "heads.json").read_text(encoding="utf-8"))
    st = d / "model.safetensors"
    sd = read_safetensors(st)
    if cfg.get("model_type") != "modernbert":
        raise SystemExit(f"{d}: not a ModernBERT (Ettin) model")
    for k, want in [("norm_bias", False), ("attention_bias", False), ("mlp_bias", False), ("hidden_activation", "gelu")]:
        if cfg.get(k) != want:
            raise SystemExit(f"{d}: {k} is {cfg.get(k)!r}, which the engine doesn't implement")
    H, L, NH, F = cfg["hidden_size"], cfg["num_hidden_layers"], cfg["num_attention_heads"], cfg["intermediate_size"]
    V = cfg["vocab_size"]
    rope = cfg.get("rope_parameters") or {}
    th_full = rope.get("full_attention", {}).get("rope_theta", cfg.get("global_rope_theta"))
    th_slide = rope.get("sliding_attention", {}).get("rope_theta", cfg.get("local_rope_theta", th_full))
    types = cfg.get("layer_types") or ["full_attention" if i % cfg["global_attn_every_n_layers"] == 0 else "sliding_attention" for i in range(L)]
    for k, want in [("scores", "scores"), ("gates", "gates"), ("types", "types"), ("span_tags", "span_tags")]:
        if hj[k] != labels[k]:
            raise SystemExit(f"{d}: its {k} differ from the other model's")
    e = Emitter(g, sd, qtype)
    e.move("enc.embeddings.tok_embeddings.weight", f"{p}.token_embd", (V, H))
    e.move("enc.embeddings.norm.weight", f"{p}.token_embd_norm", (H,))
    for i in range(L):
        s, o = f"enc.layers.{i}.", f"{p}.blk.{i}."
        if i > 0:
            e.move(s + "attn_norm.weight", o + "attn_norm", (H,))
        e.move(s + "attn.Wqkv.weight", o + "attn_qkv", (3 * H, H))
        e.move(s + "attn.Wo.weight", o + "attn_out", (H, H))
        e.move(s + "mlp_norm.weight", o + "ffn_norm", (H,))
        e.move(s + "mlp.Wi.weight", o + "ffn_up", (2 * F, H))
        e.move(s + "mlp.Wo.weight", o + "ffn_down", (H, F))
    e.move("enc.final_norm.weight", f"{p}.output_norm", (H,))
    n_out = {"score": len(labels["scores"]), "gate": len(labels["gates"]), "type": len(labels["types"]),
             "embed": hj["embed"], "span": 13, "conf": 1}
    for h in HEADS:
        e.move(f"{HEAD_SRC[h]}.weight", f"{p}.head.{h}.weight", (n_out[h], H), quant=False)
        e.move(f"{HEAD_SRC[h]}.bias", f"{p}.head.{h}.bias", (n_out[h],), quant=False)
    e.check_all_used()
    k = f"qmdecide.{p}."
    g.str(k + "base", hj["base"])
    g.str(k + "base_revision", hj.get("base_revision", ""))
    g.str(k + "source.sha256", sha256(st))
    g.u32(k + "hidden", H); g.u32(k + "layers", L); g.u32(k + "heads", NH); g.u32(k + "ffn", F); g.u32(k + "vocab", V)
    g.f32(k + "norm_eps", cfg["norm_eps"])
    g.f32(k + "rope_theta", th_full)
    g.f32(k + "rope_theta_sliding", th_slide)
    g.i32s(k + "layer_full", [1 if t == "full_attention" else 0 for t in types])
    g.u32(k + "window_half", cfg["local_attention"] // 2)
    g.u32(k + "max_tokens", hj["max_len"])
    return hj, cfg


def tokenizer(g, tj: dict, V: int, cfg: dict):
    m = tj["model"]
    want = {"type": "BPE", "byte_fallback": False, "continuing_subword_prefix": None, "end_of_word_suffix": None}
    for k, v in want.items():
        if m.get(k) != v:
            raise SystemExit(f"tokenizer.json: model.{k} is {m.get(k)!r}, which the engine doesn't implement")
    if tj.get("normalizer") != {"type": "NFC"}:
        raise SystemExit("tokenizer.json: the normalizer isn't plain NFC")
    pre = tj.get("pre_tokenizer") or {}
    if pre.get("type") != "ByteLevel" or pre.get("add_prefix_space") or not pre.get("use_regex"):
        raise SystemExit("tokenizer.json: the pre-tokenizer isn't GPT-2's byte-level split")
    tokens = [""] * V
    ttype = [TOK_UNUSED] * V
    for t, i in m["vocab"].items():
        tokens[i] = t; ttype[i] = TOK_NORMAL
    for a in tj["added_tokens"]:
        tokens[a["id"]] = a["content"]
        ttype[a["id"]] = TOK_CONTROL if a["special"] else TOK_USER
    for i in range(V):
        if not tokens[i]:
            tokens[i] = f"[unused{i}]"
    merges = [x if isinstance(x, str) else " ".join(x) for x in m["merges"]]
    g.str("tokenizer.ggml.model", "gpt2")
    g.str("tokenizer.ggml.pre", "gpt-2")
    g.strs("tokenizer.ggml.tokens", tokens)
    g.i32s("tokenizer.ggml.token_type", ttype)
    g.strs("tokenizer.ggml.merges", merges)
    g.u32("tokenizer.ggml.cls_token_id", cfg["cls_token_id"])
    g.u32("tokenizer.ggml.seperator_token_id", cfg["sep_token_id"])
    g.u32("tokenizer.ggml.padding_token_id", cfg["pad_token_id"])
    g.str("qmdecide.tokenizer.normalizer", "NFC")
    g.str("qmdecide.tokenizer.template", "[CLS] text [SEP]")


def main(argv):
    ap = argparse.ArgumentParser(description="Pack the two decision models into one GGUF.")
    ap.add_argument("small", type=Path)
    ap.add_argument("medium", type=Path)
    ap.add_argument("--type", choices=["q8_0", "f32"], default="q8_0")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--name", default="qm-decide")
    a = ap.parse_args(argv)
    sh = json.loads((a.small / "heads.json").read_text(encoding="utf-8"))
    tok = a.small / "tokenizer.json"
    if sha256(tok) != sha256(a.medium / "tokenizer.json"):
        raise SystemExit("the two models' tokenizer.json files differ")
    out = a.out or a.small.parent / f"{a.name}-{a.type.upper()}.gguf"
    g = GGUF("qmdecide")
    g.str("general.name", a.name)
    g.str("general.basename", "qm-decide")
    g.str("general.organization", "Makani Innovation Cell")
    g.u32("general.file_type", FILE_TYPE[a.type])
    g.str("general.source.tokenizer.sha256", sha256(tok))
    labels = {k: sh[k] for k in ["scores", "gates", "types", "span_tags"]}
    g.strs("qmdecide.models", ["small", "medium"])
    g.strs("qmdecide.scores", labels["scores"])
    g.strs("qmdecide.gates", labels["gates"])
    g.strs("qmdecide.types", labels["types"])
    g.strs("qmdecide.span_tags", labels["span_tags"])
    g.f32s("qmdecide.score_max", [4.0 if s == "level" else 5.0 for s in labels["scores"]])
    g.u32("qmdecide.embed", sh["embed"])
    g.str("qmdecide.pooling", "mean")
    g.str("qmdecide.text_norm", sh["norm"])
    cas = sh.get("cascade") or {}
    if "threshold" not in cas:
        raise SystemExit(f"{a.small}/heads.json has no cascade threshold; calibrate the small model first")
    g.f32("qmdecide.cascade.threshold", cas["threshold"])
    g.f32("qmdecide.cascade.target_agree", cas["target_agree"])
    g.f32("qmdecide.cascade.answered_by_small", cas["answered_by_small"])
    g.str("qmdecide.cascade.rule", "use the small model's outputs when sigmoid(conf) >= threshold, else run the medium model")
    srcs = {}
    hs, cs = model(g, a.type, a.small, "small", labels)
    model(g, a.type, a.medium, "medium", labels)
    tokenizer(g, json.loads(tok.read_text(encoding="utf-8")), cs["vocab_size"], cs)
    digest = g.write(out)
    print(f"{out}  {out.stat().st_size / 1e6:.1f} MB")
    print(f"sha256 {digest}")
    for d in (a.small, a.medium):
        print(f"source {d / 'model.safetensors'}  {sha256(d / 'model.safetensors')}")
    print(f"source {tok}  {sha256(tok)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
