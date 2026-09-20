# Reglas del proyecto

> **REGLA FIJA (no negociable):** todas las herramientas, librerías, APIs y soluciones
> propuestas deben ser **GRATUITAS**. El usuario no tiene licencias de pago.
> Prohibido sugerir: trials temporales, software con licencia comercial obligatoria,
> suscripciones, servicios que exijan tarjeta de crédito, o freemium cuyo límite bloquee la tarea.

## Criterios de selección

| Aceptado | Rechazado |
|---|---|
| Licencia MIT / Apache 2.0 / BSD / GPL / LGPL | Licencia propietaria de pago |
| Open source que corre local | SaaS solo con plan pago |
| Capa gratuita permanente y suficiente | Trial de 14/30 días |
| Binarios oficiales gratuitos | Software con "activación" o crack |
| API con cuota gratis real (sin tarjeta) | API que pide tarjeta para probar |

Si existe una alternativa paga más cómoda, se menciona **solo como referencia** y se indica
siempre cuál es la opción 100 % gratuita equivalente.

---

## Kit de herramientas gratuitas por tipo de tarea

### 1. Texto y datos codificados
- **Python 3 (stdlib):** `base64`, `binascii`, `codecs`, `zlib`, `gzip`, `lzma`, `bz2`,
  `urllib.parse`, `hashlib`, `hmac`, `json`, `re`
- **base64 / hex / URL encode-decode:** `base64 -d`, `xxd`, `od -A x -t x1z`
- **JWT:** `PyJWT` (gratis) o decodificado manual de los 3 segmentos base64url
- **Cifrados clásicos y análisis de frecuencia:** `hashcat`/`john` (solo sobre datos propios),
  librerías Python `pycipher`, `pycryptodome`
- **Ofuscación JS:** `js-beautify`, `prettier` (npm, gratis)

### 2. Video / audio
- **FFmpeg** (GPL/LGPL) — extraer, cortar, transcodear, separar pistas, dump de frames
- **MediaInfo / MediaInfoLib** — identificar códecs y contenedores
- **MKVToolNix, MP4Box (GPAC)** — remux sin recodificar
- **Whisper.cpp / faster-whisper** (open source) — transcripción de audio local, sin nube
- **Audacity** — edición de audio
- **Demucs** (MIT) — separación de pistas/voces
- **VLC** — reproducción universal y conversión

### 3. Imágenes y códigos visuales
- **Pillow / OpenCV** — procesamiento
- **ZBar / pyzbar, OpenCV QRCodeDetector** — QR y códigos de barras
- **Tesseract OCR** (+ idiomas `spa`, `eng`) — texto en imágenes
- **ExifTool** — metadatos EXIF/XMP
- **Stegsolve (Java, gratis), `steghide`, `zsteg`** — esteganografía
- **GIMP, ImageMagick, Krita** — edición

### 4. Señales, radio y protocolos
- **GNU Radio, Gqrx, SDR#, SoapySDR, rtl_433** — SDR y decodificación de RF (433 MHz, ADS-B, POCSAG…)
- **Wireshark / tshark** — análisis de tramas de red
- **pySerial, python-can, cantools** — serial, CAN bus y archivos DBC
- **SigDigger, baudline, Inspectrum, URH (Universal Radio Hacker)** — análisis de señales
- **mosquitto, paho-mqtt** — MQTT local
- **modpoll / pymodbus, snap7** — Modbus y S7

### 5. Documentos y datos estructurados
- **pandas, openpyxl, python-docx, python-pptx, pdfplumber, PyMuPDF, tabula-py**
- **LibreOffice** (conversión por línea de comandos)
- **sqlite3, DuckDB** — bases de datos embebidas, sin servidor

### 6. Entorno de ejecución
- **Python venv**, **Docker Engine** (gratis para uso personal/pequeñas empresas),
  **Git**, **VS Code / VSCodium**, **Jupyter Lab**
- Ejecución **100 % local**: nada se sube a servicios de terceros salvo que el usuario lo autorice

---

## Flujo de trabajo acordado

1. El usuario entrega los datos/archivo/contexto.
2. Se identifica el formato (inspección con `file`, `xxd`, MediaInfo, ExifTool…).
3. Se propone **primero** la solución gratuita, con el comando o script listo.
4. Se ejecuta en `/home/user` y se entrega el resultado + cómo reproducirlo.
5. Se documenta cualquier límite de cuota gratuita si se usa una API.

## Pendiente de definir por el usuario
- [ ] ¿Qué hay que decodificar exactamente?
- [ ] ¿Dónde están los datos (archivo, texto pegado, URL, dispositivo)?
- [ ] ¿La solución final corre aquí en el workspace o en su PC/servidor?
