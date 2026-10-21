"""Export the lossless icon masters with Pillow; macOS iconutil builds ICNS.

Run on macOS: python3 desktop-preview/scripts/export-theme-icons.py
This only resamples and packages artwork; it never recolors or flattens alpha.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
THEMES = ('sage', 'midnight', 'galaxy', 'aurora', 'ember', 'glass')
DEST = ROOT / 'src/assets/icons'


def export():
    DEST.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        stem = f'verseview-{theme}'
        with Image.open(ROOT / 'assets/icon-masters' / f'{stem}.png') as source:
            assert source.mode == 'RGBA' and source.width == source.height and source.width >= 1024
            image = source.resize((1024, 1024), Image.Resampling.LANCZOS)
        image.save(DEST / f'{stem}.png')
        image.save(DEST / f'{stem}.ico', sizes=[(n, n) for n in (16, 20, 24, 32, 40, 48, 64, 128, 256)])
        with TemporaryDirectory() as folder:
            iconset = Path(folder) / f'{stem}.iconset'
            iconset.mkdir()
            for size in (16, 32, 128, 256, 512):
                for scale in (1, 2):
                    suffix = '@2x' if scale == 2 else ''
                    image.resize((size * scale, size * scale), Image.Resampling.LANCZOS).save(
                        iconset / f'icon_{size}x{size}{suffix}.png')
            subprocess.run(['iconutil', '-c', 'icns', str(iconset), '-o', str(DEST / f'{stem}.icns')], check=True)
        print(f'Exported {stem}: RGBA PNG, multi-resolution ICO, ICNS')


if __name__ == '__main__':
    export()
