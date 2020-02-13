import argparse
import sys
from pathlib import Path

from addict import Dict
from skimage import io
import torch

sys.path.append(str(Path(__file__).parent.parent.resolve()))
from omnigan.data import get_all_loaders
from omnigan.mega_depth import get_mega_model
from omnigan.trainer import Trainer
from omnigan.utils import decode_mega_depth, load_opts
from run import print_header

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", default="config/local_tests.yaml")
args = parser.parse_args()
root = Path(__file__).parent.parent
opts = load_opts(root / args.config, default=root / "shared/defaults.yaml")


if __name__ == "__main__":

    opts = opts.copy()
    crop_to = 32
    write_images = True
    test_batch = False
    test_translation = True

    not_committed_path = Path(__file__).parent / "not_committed"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if not not_committed_path.exists():
        not_committed_path.mkdir()

    if crop_to > 0:
        opts.data.transforms += [
            Dict({"name": "crop", "ignore": False, "height": crop_to, "width": crop_to})
        ]

    mega = get_mega_model().to(device)
    loaders = get_all_loaders(opts)
    loader = loaders["train"]["rn"]
    batch = next(iter(loader))

    if test_batch:
        print_header("infer MD on batch")
        im_t = batch["data"]["x"].to(device)
        print("inferring...")
        im_d = mega(im_t)
        print("Done. Saving...")
        for i, im in enumerate(im_d):
            im_n = decode_mega_depth(im, numpy=True)
            stem = Path(batch["paths"]["s"][i]).stem
            if write_images:
                io.imsave(
                    str(not_committed_path / (stem + "_depth.png")), im_n,
                )
        print("Done.")

    if test_translation:
        print_header("translate then infer MD")
        trainer = Trainer(opts, verbose=1)
        trainer.setup()
        print("Translating...")
        y = trainer.G.translate_batch(trainer.batch_to_device(batch))
        print("Done. Inferring depth...")
        y_d = mega(y)
        print("Done.")
        if write_images:
            for i, im_d in enumerate(y_d):
                print(i, "/", len(y_d))
                im_n = decode_mega_depth(im_d, numpy=True)
                stem = Path(batch["paths"]["s"][i]).stem
                io.imsave(
                    str(not_committed_path / (stem + "_translated_depth.png")), im_n,
                )
        else:
            im_d = decode_mega_depth(y_d)