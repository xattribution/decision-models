# decision-models

Training code for Quartermaster's local decision models (ROADMAP item 15): small Ettin encoders that grade Air Force and Space Force evaluation bullets on structure, content, impact, tone, level and the pass/fail gate.

Data is never committed. The bullet bank, panel scores, synthetic sets and trained weights stay in `qm-training` on the training PC.

## Layout

| Folder | What's in it |
|---|---|
| `panel/` | Scoring rubrics. `rubric4.md` is the current one. |
| `synth/` | Specs for the synthetic sets (ladders, near-miss edits) and the blind arbiter. |
| `scripts/` | Data audit, panel batching and keys, synthetic set tools, training and test runners. |

## Main scripts

| Script | What it does |
|---|---|
| `bank_items.py R` | Picks real bullets for panel round R. |
| `panel4.py items/round/key/check R` | Writes scorer batches, finds disputes, builds the key with Fable's rulings. |
| `synth_seeds.py` | Picks seed bullets from the train split. |
| `synth_arb.py batches/score SET` | Shuffles synthetic groups for the blind arbiter and keeps the groups it ranks in order. |
| `nm_check.py`, `synth_stats.py` | Check a synthetic set for shortcuts (length, shorthand, separators by level). |
| `train_head.py` | Trains one score head on an Ettin encoder and tests it on held-out real bullets. |
| `baselines.py DIM` | Simple-rule baseline and the scorer-to-scorer ceiling for one dimension. |

## Running

Python 3.12 in a uv venv with `torch` (CUDA), `transformers`, `pandas`, `pyarrow` and `scipy`. Example:

```
.\.venv\Scripts\python.exe scripts\train_head.py --dim content --base jhu-clsp/ettin-encoder-400m --real r5 --arm staged --epochs 1 --real-epochs 4 --sets content,nmcontent
```
