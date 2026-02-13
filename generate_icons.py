#!/usr/bin/env python3
"""Конвертация исходной PNG-иконки в форматы для сборки приложения."""

from PIL import Image
import os
import sys


def _load_source_icon(source_path: str) -> Image.Image:
    """Загружает исходную PNG-иконку."""
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source icon not found: {source_path}")
    return Image.open(source_path).convert("RGBA")


def save_png_icon(source: Image.Image, output_path: str, size: int = 512) -> None:
    """Сохраняет PNG-иконку фиксированного размера."""
    icon = source.resize((size, size), Image.Resampling.LANCZOS)
    icon.save(output_path, "PNG")
    print(f"Generated: {output_path} ({size}x{size})")


def save_ico_icon(source: Image.Image, output_path: str) -> None:
    """Сохраняет ICO-иконку (Windows) с множественными размерами."""
    sizes = [16, 32, 48, 64, 128, 256]
    base_size = max(sizes)
    icon = source.resize((base_size, base_size), Image.Resampling.LANCZOS)

    icon.save(
        output_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
    )
    print(f"Generated: {output_path} with sizes: {sizes}")


def save_icns_icon(source: Image.Image, output_path: str) -> None:
    """Пробует сохранить ICNS (если Pillow поддерживает текущую платформу)."""
    try:
        icon = source.resize((1024, 1024), Image.Resampling.LANCZOS)
        icon.save(output_path, "ICNS")
        print(f"Generated: {output_path}")
    except Exception as exc:
        print(f"Skipped ICNS generation: {exc}")


def main():
    """Главная функция конвертации всех иконок."""
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    os.makedirs(assets_dir, exist_ok=True)
    source_path = os.path.join(assets_dir, "ico.png")

    try:
        source = _load_source_icon(source_path)
    except FileNotFoundError as exc:
        print(exc)
        sys.exit(1)

    save_png_icon(source, os.path.join(assets_dir, "icon.png"), size=512)
    save_ico_icon(source, os.path.join(assets_dir, "icon.ico"))
    save_icns_icon(source, os.path.join(assets_dir, "icon.icns"))

    print("\nAll icons generated successfully!")
    print(f"Assets directory: {assets_dir}")


if __name__ == '__main__':
    main()
