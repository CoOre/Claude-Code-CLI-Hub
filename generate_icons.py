#!/usr/bin/env python3
"""Генерация иконок для приложения Claude Code CLI Hub."""

from PIL import Image, ImageDraw
import os
import tempfile
import struct


def generate_base_icon(size: int) -> Image.Image:
    """Генерирует базовую иконку заданного размера.

    Стиль: темный фон, синий круг с белой обводкой, темный квадрат в центре.
    """
    image = Image.new("RGBA", (size, size), (30, 30, 36, 255))
    draw = ImageDraw.Draw(image)

    # Синий круг с белой обводкой
    circle_margin = size // 8
    draw.ellipse(
        (circle_margin, circle_margin, size - circle_margin, size - circle_margin),
        fill=(93, 188, 210, 255),
        outline=(255, 255, 255, 255),
        width=max(1, size // 32)
    )

    # Темный квадрат в центре
    square_half = size // 5
    center = size // 2
    draw.rectangle(
        (center - square_half, center - square_half,
         center + square_half, center + square_half),
        fill=(30, 30, 36, 255)
    )

    return image


def save_png_icon(output_path: str, size: int = 512) -> None:
    """Сохраняет иконку в формате PNG."""
    icon = generate_base_icon(size)
    icon.save(output_path, "PNG")
    print(f"Generated: {output_path} ({size}x{size})")


def save_ico_icon(output_path: str) -> None:
    """Сохраняет иконку в формате ICO (Windows) с множественными размерами."""
    sizes = [16, 32, 48, 64, 128, 256]
    icons = [generate_base_icon(size) for size in sizes]

    # PIL сам сохраняет ICO с множественными размерами
    icons[0].save(
        output_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=icons[1:]
    )
    print(f"Generated: {output_path} with sizes: {sizes}")


def save_icns_icon(output_path: str) -> None:
    """Сохраняет иконку в формате ICNS (macOS)."""
    sizes = {
        'icp4': 16,      # 16x16
        'icp5': 32,      # 32x32
        'icp6': 64,      # 64x64
        'ic07': 128,     # 128x128
        'ic08': 256,     # 256x256
        'ic09': 512,     # 512x512
        'ic10': 1024,    # 1024x1024 (Retina)
    }

    # Создаем временную директорию для иконок
    with tempfile.TemporaryDirectory() as tmpdir:
        iconset_dir = os.path.join(tmpdir, 'icon.iconset')
        os.makedirs(iconset_dir)

        # Сохраняем PNG для каждого размера
        for icon_type, size in sizes.items():
            icon = generate_base_icon(size)
            # Для Retina используем @2x суффикс где нужно
            if icon_type == 'ic10':
                # 1024x1024 = 512@2x
                png_path = os.path.join(iconset_dir, f'icon_512x512@2x.png')
            elif size <= 512:
                png_path = os.path.join(iconset_dir, f'icon_{size}x{size}.png')
                # Retina версия
                if size <= 256:
                    icon_2x = generate_base_icon(size * 2)
                    png_path_2x = os.path.join(iconset_dir, f'icon_{size}x{size}@2x.png')
                    icon_2x.save(png_path_2x, 'PNG')
            icon.save(png_path, 'PNG')

        # Используем iconutil для создания .icns (только на macOS)
        # Если не macOS, создаем вручную
        if os.uname().sysname == 'Darwin':
            os.system(f'iconutil -c icns {iconset_dir} -o {output_path}')
        else:
            # Создаем упрощенный ICNS вручную для Linux/Windows сборки
            create_icns_manually(output_path, sizes)

    print(f"Generated: {output_path}")


def create_icns_manually(output_path: str, sizes: dict) -> None:
    """Создает ICNS файл вручную (для не-macOS систем)."""
    # ICNS формат:
    # Header: 4 bytes magic ('icns'), 4 bytes file length
    # Data: repeating blocks of 4 bytes type, 4 bytes length, N bytes data

    # Только основные типы для совместимости
    icon_types = {
        16: b'icp4',
        32: b'icp5',
        128: b'ic07',
        256: b'ic08',
        512: b'ic09',
    }

    data_blocks = []
    for size, icon_type in icon_types.items():
        icon = generate_base_icon(size)
        # Сохраняем в PNG формат
        import io
        png_buffer = io.BytesIO()
        icon.save(png_buffer, 'PNG')
        png_data = png_buffer.getvalue()

        # ICNS data block: type (4) + length (4) + data (N)
        block_length = 8 + len(png_data)
        block = icon_type + struct.pack('>I', block_length) + png_data
        data_blocks.append(block)

    # Собираем файл
    all_data = b''.join(data_blocks)
    header = b'icns' + struct.pack('>I', 8 + len(all_data))

    with open(output_path, 'wb') as f:
        f.write(header + all_data)


def main():
    """Главная функция генерации всех иконок."""
    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
    os.makedirs(assets_dir, exist_ok=True)

    # PNG для Linux и macOS (512x512)
    # PyInstaller для macOS автоматически конвертирует PNG в ICNS
    save_png_icon(os.path.join(assets_dir, 'icon.png'), size=512)

    # ICO для Windows
    save_ico_icon(os.path.join(assets_dir, 'icon.ico'))

    print("\nAll icons generated successfully!")
    print(f"Assets directory: {assets_dir}")


if __name__ == '__main__':
    main()
