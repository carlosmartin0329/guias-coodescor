#!/usr/bin/env python3
"""
Script para generar los íconos de la PWA.
Requiere: pip install pillow

Ejecuta: python static/icons/generar_iconos.py
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    import os
    
    # Configuración
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
    
    # Colores
    BG_COLOR = (30, 78, 216)  # #1e4ed8 - azul
    TEXT_COLOR = (255, 255, 255)  # blanco
    
    # Crear directorio si no existe
    os.makedirs(BASE_DIR, exist_ok=True)
    
    # Crear íconos
    for size in SIZES:
        # Crear imagen
        img = Image.new('RGB', (size, size), BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        # Intentar cargar fuente (si está disponible)
        try:
            font_size = int(size * 0.4)
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Dibujar iniciales "GC" (Guías Coodescor)
        text = "GC"
        text_width, text_height = draw.textsize(text, font=font)
        x = (size - text_width) / 2
        y = (size - text_height) / 2
        draw.text((x, y), text, fill=TEXT_COLOR, font=font)
        
        # Guardar
        filename = os.path.join(BASE_DIR, f"icon-{size}x{size}.png")
        img.save(filename)
        print(f"Generado: {filename}")
    
    print("\n✅ Todos los íconos generados correctamente!")
    print("Puedes eliminorre este script después de generar los íconos.")
    
except ImportError as e:
    print("❌ Error: Necesitas instalar Pillow")
    print("   Ejecuta: pip install pillow")
    print("   O en Windows: py -3 -m pip install pillow")
    print(f"   Error: {e}")
