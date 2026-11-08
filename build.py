# -*- coding: utf-8 -*-
"""FX RIG 9000.exe を作る（build.bat から呼ばれます）。先に make_html.py で app.html を作っておく"""
import os
here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)
import PyInstaller.__main__
sep = ';' if os.name == 'nt' else ':'
PyInstaller.__main__.run([
    'fxrig.py',
    '--name', 'FX RIG 9000',
    '--onefile',
    '--noconsole',
    '--icon', 'fxrig.ico',
    '--add-data', 'app.html' + sep + '.',
    '--clean', '--noconfirm', '--distpath', os.environ.get('FXRIG_DIST', 'dist'),
])
out = os.path.join(here, os.environ.get('FXRIG_DIST', 'dist'), 'FX RIG 9000.exe')
print()
print('できました:', out if os.path.exists(out) else '（失敗しました。上のエラーを見てください）')
