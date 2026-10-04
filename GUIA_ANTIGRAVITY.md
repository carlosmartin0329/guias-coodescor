# Usar Gemini para editar este proyecto desde VS Code

Si quieres trabajar **dentro de Visual Studio Code**, como con Copilot, instala
la extensión oficial **Gemini Code Assist** y usa su modo **Agent**. Antigravity
es un editor separado; no hace falta instalarlo para usar Gemini en VS Code y
no se agrega ningún código de autenticación a la carpeta del proyecto.

## 1. Instalar Gemini Code Assist en VS Code

Abre una terminal PowerShell y ejecuta:

```powershell
code --install-extension Google.geminicodeassist
```

Si PowerShell dice que `code` no se reconoce, cierra y vuelve a abrir VS Code o
PowerShell para que Windows recargue el `PATH`. También puedes ejecutar VS Code
por su ruta completa:

```powershell
& "$env:LOCALAPPDATA\Programs\Microsoft VS Code\bin\code.cmd" --install-extension Google.geminicodeassist
```

Si VS Code está instalado en otra ubicación, abre VS Code, ve a **Extensions**
(`Ctrl+Shift+X`), busca **Gemini Code Assist** de Google e instálala desde allí.
Si el comando informa que la extensión ya está instalada, puedes continuar.
Después, abre la carpeta del proyecto:

```powershell
Set-Location "D:\Users\57323\Downloads\guias coodescor"
code .
```

Para abrir la carpeta usando la ruta completa del ejecutable:

```powershell
& "$env:LOCALAPPDATA\Programs\Microsoft VS Code\bin\code.cmd" "D:\Users\57323\Downloads\guias coodescor"
```

## 2. Iniciar sesión y activar el modo Agente

En la barra lateral de VS Code, abre **Gemini Code Assist** e inicia sesión
con tu cuenta de Google cuando te lo solicite. En el chat, activa el selector
**Agent** para usar el modo agente en vez del chat normal.

Si el flujo de inicio de sesión muestra un código temporal, introdúcelo solo
donde lo solicite la aplicación o el proceso de autenticación. No es código
fuente: **no lo pegues en el chat ni lo guardes en archivos del proyecto**.

## 3. Pedir edición, creación y pruebas

Describe el resultado esperado en el chat del modo **Agent**. Por ejemplo:

> En el formulario para crear guías, valida que el número de bultos sea mayor
> que cero. Modifica los archivos necesarios, ejecuta las pruebas relacionadas
> y muéstrame el resumen de los cambios.

El modo Agent puede usar herramientas del IDE, como leer y escribir archivos y
ejecutar comandos de terminal. Según la configuración y las confirmaciones que
solicite VS Code, Gemini puede proponer cambios de código y comandos. Revisa y
aprueba cada cambio o ejecución antes de continuar; no actives la aprobación
automática si prefieres autorizar las acciones una por una. Pide explícitamente
que cree archivos o pruebas, o que elimine un archivo concreto, y revisa el diff
antes de aceptar.

## 4. Ejecutar el proyecto

Para iniciar Guías Coodescor, abre la terminal integrada de VS Code
(`Ctrl+``) en la raíz del proyecto y ejecuta:

```powershell
.\run.ps1
```

Como alternativa, si Python 3 está instalado:

```powershell
py -3 run_app.py
```

Abre la aplicación en el navegador:

```powershell
Start-Process "http://localhost:8000"
```

Consulta [README.md](./README.md) para más detalles sobre la ejecución y
configuración de este proyecto.

Documentación oficial:

- [Instalar Gemini Code Assist desde VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=Google.geminicodeassist)
- [Usar el modo Agent en Gemini Code Assist](https://docs.cloud.google.com/gemini/docs/codeassist/use-agentic-chat-pair-programmer)
