# qm-decide: model card

Quartermaster's local decision models. They grade Air Force and Space Force evaluation, award and decoration statements on the user's computer. They return scores, never text.

_Numbers below are filled in from `work/multi/results.jsonl` and `extra.jsonl` when a release is built._

## What's in the file

One GGUF (`qm-decide-Q8_0.gguf`) holds two encoders with the same word pieces and the same outputs:

| | small | medium |
|---|---|---|
| Base | Ettin encoder 68M (`jhu-clsp/ettin-encoder-68m`) | Ettin encoder 400M (`jhu-clsp/ettin-encoder-400m`) |
| Role | Answers when its confidence is at or above the threshold | Answers the rest |
| Trained | Distilled from the medium model, plus the real labels | Synthetic pairs, then the panel key and the other tasks |

Outputs, for each statement:

- **score**: 12 values on the rubric4 scale: structure, action, impact, result, quantified, scope, credibility, readability, clipping, tone, level (0 to 4), and overall. All except level run 0 to 5. Clip them to that range.
- **gate**: pass, not_a_bullet, incomplete, nonsense or banned.
- **type**: bullet, narrative, citation, push or strat.
- **spans**: B/I tags on each token for action, impact and result (one layer, never overlapping), plus scope and numbers (a layer each; they may sit inside the others).
- **embed**: 256 numbers of unit length. Statements that say the same thing sit close, including a clipped line and its spelled-out copy.
- **conf** (small only): the chance the small model agrees with the medium one. Agreement means every score is within 0.5 and the gate matches.

## How to run it

1. Collapse white space and drop a leading dash or bullet mark (`qmdecide.text_norm`). The models never saw the leading "- " in training.
2. Spell out approved abbreviations the way the app does before scoring. The models were trained with a quarter of their inputs spelled out, so either form works. The clipping score is meaningless on spelled-out text: compute it in code from the original.
3. Tokenize: NFC, then GPT-2 byte-level BPE (tokens and merges are in the file), then `[CLS] text [SEP]`. Use at most 128 tokens.
4. Run the small model. If sigmoid(conf) is at or above `qmdecide.cascade.threshold`, use its outputs. Otherwise run the medium model.

`convert_decision.py` documents the tensor layout. `check_decision.py` runs the file in plain numpy and checks it against the 20-input PyTorch reference (`decide_reference.py`). Use both to verify any new runtime.

## Training data

- **Bank**: 63,034 public statements from the sources listed in `data/SOURCES.md` on the training PC. Split by source: afbulletsafe.com is held out as validation. The user's Space Force bullets are used for training only, never as shipped examples.
- **Panel key**: 8,206 round 5 statements plus 456 round 4 statements. Two Claude Opus scorers per item, using rubric4. Disputes were ruled by Claude Fable.
- **Spans**: 8,854 statements marked by Claude Opus (`panel/spans.md`). Every piece is checked against the text.
- **Synthetic sets**: ladders and near-miss edits from Claude Opus, kept only when a blind arbiter ranked them in the intended order. They are used for pairwise ranking and as same-meaning pairs. They are never shipped as examples.
- **Types**: from the bank's own labels, plus Opera's bullet-to-narrative pairs for the narrative class. The 147 real narrative performance statements are for testing only.

Source weights used when the small model learns from the medium one:

| Source | Weight | Why |
|---|---|---|
| ussf-bank | 1.5 | Current Space Force bullet format, the forms the app fills |
| github/justinthelaw/opera | 0.5 | Every slash was stripped upstream, so words run together |
| reddit.com | 0.3 | Forum text; many lines are not statements |
| others | 1.0 | |

## Known limits

- The key comes from two model scorers. On the validation source they agree on structure at rho 0.807, so no model can be judged much above that there.
- Narrative statements were learned mostly from Opera's generated narratives. Check the real-narrative test numbers before relying on the type head for Air Force narrative forms.
- Opera's text has its slashes stripped. Repair it before using that source as examples shown to users.
- Scores track the panel's rubric. A unit's own rules (banned words, form limits) are code and data, not the model.
