# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# Загружаем версию
version = "1.0.3"  # Обновляется автоматически bump-my-version

# Определяем путь к иконке в зависимости от платформы.
# Приоритет у пользовательской иконки assets/ico.png.
if sys.platform == 'darwin':
    icon_candidates = ['assets/icon.icns', 'assets/icon.png', 'assets/ico.png']
elif sys.platform == 'win32':
    icon_candidates = ['assets/icon.ico', 'assets/ico.png', 'assets/icon.png']
else:
    icon_candidates = ['assets/icon.png', 'assets/ico.png']

icon_path = next((path for path in icon_candidates if os.path.exists(path)), None)
if not icon_path:
    print(f"Warning: Icon not found. Checked: {icon_candidates}")

# Для macOS используем onedir mode (noarchive=True) для корректной работы .app bundle
# Для других платформ используем onefile mode (noarchive=False)
is_macos = sys.platform == 'darwin'

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=['pystray', 'PIL', 'PIL._imagingtk', 'PIL.Image', 'PIL.ImageDraw'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=is_macos,  # True для macOS (onedir), False для других (onefile)
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='claude-code-cli-hub',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

# Для macOS создаем .app bundle с иконкой
if is_macos:
    app = BUNDLE(
        exe,
        name='claude-code-cli-hub.app',
        icon=icon_path,
        bundle_identifier='com.vladimirnosov.claude-code-cli-hub',
        info_plist={
            'CFBundleShortVersionString': version,
            'CFBundleVersion': version,
            'NSHighResolutionCapable': 'True',
        },
    )
