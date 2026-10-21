"""Write a trained checkpoint as safetensors, beside the Ettin config and the heads' settings.

  export_st.py work/multi/m400.pt export/medium

The converter (convert_decision.py) reads only these files, so it never opens a pickle.
"""
import json, os, shutil, sys

import torch
from huggingface_hub import hf_hub_download
from safetensors.torch import save_file


def main(ckpt, out):
    os.makedirs(out, exist_ok=True)
    cfg = json.load(open(ckpt[:-3] + ".json"))
    sd = torch.load(ckpt, map_location="cpu", weights_only=True)
    sd = {k: v.float().contiguous() for k, v in sd.items()}
    save_file(sd, os.path.join(out, "model.safetensors"))
    for f in ["config.json", "tokenizer.json"]:
        shutil.copy(hf_hub_download(cfg["base"], f), os.path.join(out, f))
    snap = os.path.basename(os.path.dirname(hf_hub_download(cfg["base"], "config.json")))
    cfg["base_revision"] = snap
    cfg["checkpoint"] = os.path.basename(ckpt)
    json.dump(cfg, open(os.path.join(out, "heads.json"), "w"), indent=1)
    print("wrote", out, len(sd), "tensors")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
