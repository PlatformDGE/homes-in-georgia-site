# Made with Claude (Anthropic) · © Homes in Georgia · Created by Irakli Kvirkvelia
"""Lightly shrink listing photos in the published copy of the site.

The originals stay untouched in the source repository. Each photo is fitted
into 1600 px and saved at JPEG quality 80, and kept only when it gets smaller.
Results are cached by the photo's git blob id, so a photo is processed once.

Usage: shrink_photos.py <public dir> <cache dir> <ls-tree file>
"""
import os
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor

from PIL import Image, ImageOps

MAX_SIDE = 1600
QUALITY = 80


def shrink(job):
    src, dst = job
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert('RGB')
            im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
            tmp = dst + '.tmp'
            im.save(tmp, 'JPEG', quality=QUALITY, optimize=True, progressive=True)
        if os.path.getsize(tmp) >= os.path.getsize(src):
            shutil.copyfile(src, tmp)  # already small: keep the original bytes
        os.replace(tmp, dst)
        return True
    except Exception as e:  # a broken photo is published as it is
        print(f'skip {src}: {e}', file=sys.stderr)
        return False


def main(public, cache, tree_file):
    os.makedirs(cache, exist_ok=True)
    todo, place = [], []
    for line in open(tree_file, encoding='utf-8'):
        meta, path = line.rstrip('\n').split('\t', 1)
        blob = meta.split()[2]
        if not path.lower().endswith(('.jpg', '.jpeg')):
            continue
        rel = path[len('site/'):]
        target = os.path.join(public, rel)
        cached = os.path.join(cache, blob + '.jpg')
        if not os.path.exists(target):
            continue
        if not os.path.exists(cached):
            todo.append((target, cached))
        place.append((cached, target))
    with ProcessPoolExecutor() as pool:
        done = sum(pool.map(shrink, todo, chunksize=16))
    before = after = 0
    for cached, target in place:
        if os.path.exists(cached):
            before += os.path.getsize(target)
            shutil.copyfile(cached, target)
            after += os.path.getsize(target)
    print(f'photos: {len(place)}, newly shrunk: {done}/{len(todo)}, '
          f'{before / 1e9:.2f} GB -> {after / 1e9:.2f} GB')


if __name__ == '__main__':
    main(*sys.argv[1:4])
