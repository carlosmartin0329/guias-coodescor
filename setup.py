#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instalador del Sistema de Guías Coodescor
Este script verifica requisitos, instala dependencias y configura el entorno.
Ejecutar en la primera instalación en una nueva PC.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Colores para consola
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def verificar_python():
    """Verifica que Python 3.8+ esté instalado."""
    print_header("VERIFICANDO PYTHON")
    
    try:
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print_error(f"Python 3.8+ requerido. Versión actual: {version.major}.{version.minor}")
            return False
        
        print_success(f"Python {version.major}.{version.minor}.{version.micro} detectado")
        return True
    
    except Exception as e:
        print_error(f"No se pudo verificar Python: {e}")
        return False

def verificar_directorios():
    """Crea los directorios necesarios si no existen."""
    print_header("CONFIGURANDO DIRECTORIOS")
    
    dirs_necesarios = [
        "guias_coodescor/data",
        "guias_coodescor/data/adjuntos",
        "backups",
        "logs"
    ]
    
    for directorio in dirs_necesarios:
        Path(directorio).mkdir(parents=True, exist_ok=True)
        print_success(f"Directorio creado/verificado: {directorio}")
    
    return True

def instalar_dependencias():
    """Instala las dependencias opcionales desde requirements.txt."""
    print_header("INSTALANDO DEPENDENCIAS")
    
    req_file = Path("requirements.txt")
    
    if not req_file.exists():
        print_warning("requirements.txt no encontrado. Continuando sin dependencias externas.")
        return True
    
    try:
        print_info("Instalando paquetes desde requirements.txt...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_file), "--quiet"])
        print_success("Dependencias instaladas correctamente")
        return True
    
    except subprocess.CalledProcessError as e:
        print_error(f"Error instalando dependencias: {e}")
        print_warning("El sistema puede funcionar sin dependencias externas")
        return True

def verificar_conexion():
    """Verifica que el puerto 8000 esté disponible."""
    print_header("VERIFICANDO PUERTO")
    
    import socket
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind(('0.0.0.0', 8000))
        sock.close()
        print_success("Puerto 8000 disponible")
        return True
    
    except OSError as e:
        print_error(f"Puerto 8000 ocupado: {e}")
        print_warning("El sistema usará otro puerto automáticamente o cierre la aplicación que usa el puerto 8000")
        return True

def crear_acceso_directo():
    """Crea un acceso directo en el escritorio (Windows)."""
    print_header("CREANDO ACCESO DIRECTO")
    
    if sys.platform != 'win32':
        print_info("Sistema no Windows. Saltando creación de acceso directo.")
        return True
    
    try:
        # Crear script batch en el escritorio
        desktop = Path(os.environ['USERPROFILE']) / 'Desktop'
        script_content = '''@echo off
cd /d "%~dp0"
py -3 run_app.py
pause
'''
        
        acceso = desktop / 'Guías Coodescor.bat'
        with open(acceso, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        print_success(f"Acceso directo creado: {acceso}")
        return True
    
    except Exception as e:
        print_warning(f"No se pudo crear acceso directo: {e}")
        return True

def mostrar_instrucciones():
    """Muestra las instrucciones finales."""
    print_header("INSTALACIÓN COMPLETADA")
    
    print(f"""
{Colors.OKGREEN}╔══════════════════════════════════════════════════════════╗
║                  INSTALACIÓN EXITOSA                      ║
╚══════════════════════════════════════════════════════════╝{Colors.ENDC}

{Colors.BOLD}Próximos pasos:{Colors.ENDC}

1. {Colors.OKCYAN}Ejecutar el sistema:{Colors.ENDC}
   • Doble clic en {Colors.BOLD}run.bat{Colors.ENDC}
   • O ejecute: {Colors.BOLD}python run_app.py{Colors.ENDC}

2. {Colors.OKCYAN}Acceder al sistema:{Colors.ENDC}
   • Abra su navegador
   • Vaya a: {Colors.BOLD}http://localhost:8000{Colors.ENDC}

3. {Colors.OKCYAN}Usuarios iniciales:{Colors.ENDC}
   ┌──────────────┬─────────────┬─────────────────────────┐
   │ Usuario      │ Contraseña  │ Rol                     │
   ├──────────────┼─────────────┼─────────────────────────┤
   │ admin        │ admin123    │ Admin del Sistema       │
   │ administrativo│ adminbod123│ Administrativo (Bodega) │
   │ ventas       │ ventas123   │ Ventas 1                │
   │ cedis        │ cedis123    │ CEDIS                   │
   │ transportador│ trans123    │ Transportador           │
   └──────────────┴─────────────┴─────────────────────────┘

{Colors.WARNING}⚠️  IMPORTANTE: Cambie las contraseñas inmediatamente{Colors.ENDC}

4. {Colors.OKCYAN}Para acceso desde otros dispositivos:{Colors.ENDC}
   • Todos deben estar en la misma red Wi-Fi
   • Use la IP de este equipo: http://[IP-DEL-PC]:8000
   • Para saber su IP, ejecute: ipconfig (Windows) o ifconfig (Linux/Mac)

{Colors.BOLD}Documentación:{Colors.ENDC}
   • Lea README_PROFESSIONAL.md para información detallada
   • Lea android_app/README.md para instalar app en Android

{Colors.OKGREEN}¡Sistema listo para usar!{Colors.ENDC}
""")

def main():
    """Función principal del instalador."""
    print(f"""
{Colors.OKCYAN}
 ██████╗██╗  ██╗ █████╗ ███╗   ██╗███████╗    ██████╗ ███████╗██╗     ██╗     ██╗███╗   ██╗ █████╗ 
██╔════╝██║  ██║██╔═══██╗████╗  ██║██╔════╝    ██╔══██╗██╔════╝██║     ██║     ██║████╗  ██║██╔══██╗
██║     ███████║██║   ██║██╔██╗ ██║█████╗      ██████╔╝█████╗  ██║     ██║     ██║██╔██╗ ██║███████║
██║     ██╔══██║██║   ██║██║╚██╗██║██╔══╝      ██╔══██╗██╔══╝  ██║     ██║     ██║██║╚██╗██║██╔══██║
╚██████╗██║  ██║╚██████╔╝██║ ╚████║███████╗    ██║  ██║███████╗███████╗███████╗██║██║ ╚████║██║  ██║
 ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝    ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝
                                                                                                    
                    SISTEMA DE GESTIÓN DE GUÍAS
                    Instalador v2.0
{Colors.ENDC}
""")
    
    print_info("Iniciando instalación del Sistema de Guías Coodescor...\n")
    
    # Verificaciones previas
    if not verificar_python():
        print_error("Python 3.8+ es requerido. Por favor instálelo desde python.org")
        input("\nPresione Enter para salir...")
        return 1
    
    # Configuración
    if not verificar_directorios():
        print_error("Error creando directorios")
        return 1
    
    # Dependencias
    if not instalar_dependencias():
        print_warning("Continuando sin algunas dependencias opcionales")
    
    # Puerto
    if not verificar_conexion():
        print_warning("Posibles conflictos de puerto")
    
    # Acceso directo
    crear_acceso_directo()
    
    # Instrucciones finales
    mostrar_instrucciones()
    
    input("\nPresione Enter para finalizar...")
    return 0

if __name__ == "__main__":
    sys.exit(main())
