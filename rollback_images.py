"""
图片优化回退脚本
===============
用法: python rollback_images.py
作用: 从 _backup 恢复所有原始图片，并清理 .webp 文件
"""
import os
import shutil

BASE = os.path.join(os.path.dirname(__file__), 'static', 'images')
BACKUP = os.path.join(BASE, '_backup')

if not os.path.exists(BACKUP):
    print('错误: _backup 文件夹不存在，无法回退')
    exit(1)

# 1. 恢复原始图片
for fname in os.listdir(BACKUP):
    src = os.path.join(BACKUP, fname)
    dst = os.path.join(BASE, fname)
    if os.path.isfile(src):
        shutil.copy2(src, dst)
        print(f'恢复: {fname}')

# 2. 删除所有 .webp 文件
for fname in os.listdir(BASE):
    if fname.lower().endswith('.webp'):
        os.remove(os.path.join(BASE, fname))
        print(f'删除: {fname}')

print('\n完成! 所有图片已恢复到优化前状态。')
print('接下来请手动回退模板中的 .webp -> .png 引用（用 git diff 查看改动）')
print('或者直接: git checkout -- templates/ static/css/style.css')
