"""
图片优化脚本 — 压缩 JPG + 大 PNG 转 WebP
======================================
回退方式: python rollback_images.py
或手动: cp static/images/_backup/* static/images/
"""
import os
from PIL import Image

IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'static', 'images')

# 不处理的文件（QR码已经很小了，保留原样）
SKIP = {'placeholder.png', 'placeholder_thumb.png', 'favicon.ico',
        'qr-guanghe-university.png', 'qr-guanghe-player.png',
        '_backup', '_originals'}

# 压缩参数
JPG_QUALITY = 78       # JPG 压缩质量（70-80 肉眼几乎无损）
WEBP_QUALITY = 82      # WebP 质量
MAX_SIZE = (1600, 1600)  # 超过此尺寸先缩图

results = []

for fname in sorted(os.listdir(IMAGES_DIR)):
    if fname in SKIP or fname.startswith('.') or fname.startswith('_'):
        continue

    fpath = os.path.join(IMAGES_DIR, fname)
    if not os.path.isfile(fpath):
        continue

    try:
        img = Image.open(fpath)
    except Exception:
        continue

    orig_size = os.path.getsize(fpath)
    name, ext = os.path.splitext(fname)
    ext_lower = ext.lower()

    # ── 先缩尺寸（如果超了） ──
    if img.width > MAX_SIZE[0] or img.height > MAX_SIZE[1]:
        img.thumbnail(MAX_SIZE, Image.LANCZOS)

    if ext_lower in ('.jpg', '.jpeg'):
        # ── JPG 原地压缩 ──
        img.save(fpath, 'JPEG', quality=JPG_QUALITY, optimize=True)
        new_size = os.path.getsize(fpath)
        pct = (1 - new_size / orig_size) * 100
        results.append(f'{fname}: {orig_size//1024}KB -> {new_size//1024}KB ({pct:.0f}% off)')
        print(f'OK {fname}: {orig_size//1024}KB -> {new_size//1024}KB ({pct:.0f}% off)')

    elif ext_lower == '.png':
        # ── PNG → WebP（保留原PNG不动） ──
        webp_path = os.path.join(IMAGES_DIR, f'{name}.webp')

        # 有透明通道用 lossless=False，效果也很好
        if img.mode in ('RGBA', 'PA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            img.save(webp_path, 'WEBP', quality=WEBP_QUALITY, method=6)
        else:
            img.save(webp_path, 'WEBP', quality=WEBP_QUALITY, method=6)

        new_size = os.path.getsize(webp_path)
        pct = (1 - new_size / orig_size) * 100
        results.append(f'{fname} -> {name}.webp: {orig_size//1024}KB -> {new_size//1024}KB ({pct:.0f}% off)')
        print(f'OK {fname} -> {name}.webp: {orig_size//1024}KB -> {new_size//1024}KB ({pct:.0f}% off)')

# ── 汇总 ──
print('\n' + '=' * 40)
total_orig = sum(os.path.getsize(os.path.join(IMAGES_DIR, '_backup', f))
                 for f in os.listdir(os.path.join(IMAGES_DIR, '_backup'))
                 if os.path.isfile(os.path.join(IMAGES_DIR, '_backup', f)))
total_new = sum(os.path.getsize(os.path.join(IMAGES_DIR, f))
                for f in os.listdir(IMAGES_DIR)
                if os.path.isfile(os.path.join(IMAGES_DIR, f)) and not f.startswith('.'))

print(f'Total: {total_orig//1024}KB -> {total_new//1024}KB (saved {(1-total_new/total_orig)*100:.0f}%)')
print(f'Rollback: cp static/images/_backup/* static/images/')
