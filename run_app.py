#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de lanzamiento desde la carpeta raíz del proyecto.
Asegura que se pueda importar 'guias_coodescor' como paquete y
arranca el servidor HTTP.
"""
import os
import sys

_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from guias_coodescor.app import main

if __name__ == "__main__":
    main()
