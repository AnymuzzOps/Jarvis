# JARVIS 1.0

Asistente de escritorio en español para Windows 10/11 x64. Usa Ollama para generar respuestas, whisper.cpp para transcribir el micrófono y Piper para sintetizar voz. Tras instalar las herramientas y los modelos, puedes conversar con internet desconectado.

## Instalar en Windows

1. Instala [Python 3.12 x64](https://www.python.org/downloads/windows/) con el lanzador `py.exe` y [Ollama para Windows](https://ollama.com/download/windows). Ollama documenta compatibilidad desde Windows 10 22H2. Si desactivaste la ejecución de aplicaciones de escritorio para el micrófono, habilítala en la configuración de privacidad de Windows. [Requisitos de Ollama](https://docs.ollama.com/windows)
2. Si Ollama está abierto en la bandeja, sal de él. Abre PowerShell y deja este proceso abierto durante la preparación y el uso de JARVIS.

   ```powershell
   $env:OLLAMA_HOST = '127.0.0.1:11434'
   $env:OLLAMA_NO_CLOUD = '1'
   ollama serve
   ```

   Ollama también permite desactivar la nube mediante `disable_ollama_cloud` en su archivo `server.json`. Reinicia Ollama después de cambiarlo. [Modo local de Ollama](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features)

3. En otra ventana de PowerShell, entra a la carpeta del repositorio descargado o descomprimido. Ejecuta el siguiente comando si aceptas descargar las tres clases de modelos. Los parámetros explícitos autorizan la descarga de los componentes indicados.

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Setup-Jarvis.ps1 -InstallWhisper -DownloadVoiceModels -PullOllamaModel
   ```

   Ejecuta el mismo comando sin parámetros de descarga para instalar solo las dependencias de Python y ver la guía. La política de ejecución del ejemplo se aplica únicamente al proceso nuevo. Para un notebook con recursos limitados, agrega `-Model 'qwen3:1.7b'` y selecciona ese modelo en **Configuración** antes de validar. También puedes probar `qwen3:0.6b` o `qwen3:8b` según el hardware.

4. Valida los componentes y abre la aplicación.

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-JarvisSetup.ps1
   .\.venv\Scripts\python.exe -m jarvis
   ```

   **Verificar** vuelve a consultar Ollama y las rutas después de corregir un error. En **Configuración** puedes ajustar el modelo, la voz, las rutas, los dispositivos y los límites. Los cambios se guardan en `%LOCALAPPDATA%\Jarvis\settings.json`. Si un dispositivo seleccionado desaparece o cambia de índice, vuelve a elegirlo en la lista actualizada.

## Modelos

| Componente | Selección inicial | Ubicación y origen |
| --- | --- | --- |
| Ollama | `qwen3:4b` | Ollama lo administra. El repositorio de modelos publica alternativas de distintos tamaños. [Qwen 3](https://ollama.com/library/qwen3) |
| Whisper | `ggml-base.bin` multilingüe | `%LOCALAPPDATA%\Jarvis\models`. Usa `ggml-small.bin` si necesitas más precisión y el equipo lo permite. [Modelos GGML](https://huggingface.co/ggerganov/whisper.cpp/tree/main) |
| Piper | `es_ES-sharvard-medium.onnx` y `es_ES-sharvard-medium.onnx.json` | Ambos archivos deben quedar juntos en `%LOCALAPPDATA%\Jarvis\models`. [Voz Sharvard](https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_ES/sharvard/medium) |

## Preparación manual

Si falla la descarga automatizada, prueba el siguiente procedimiento desde la carpeta del repositorio:

- Crea el entorno con `py -3.12 -m venv .venv` e instala las dependencias con `.\.venv\Scripts\python.exe -m pip install -e ".[test]"`. Confirma que exista `.venv\Scripts\piper.exe`.
- Descarga `whisper-bin-x64.zip` de la versión **v1.8.2** y extráelo. Copia la carpeta que contiene `whisper-cli.exe` y sus DLL de forma que el ejecutable quede en `%LOCALAPPDATA%\Jarvis\whisper\whisper-cli.exe`, o selecciona la ruta extraída en JARVIS. [Publicación oficial](https://github.com/ggml-org/whisper.cpp/releases/tag/v1.8.2)
- Descarga `ggml-base.bin` y los dos archivos de voz desde los enlaces de la tabla. Guárdalos en `%LOCALAPPDATA%\Jarvis\models` o selecciona las rutas en **Configuración**.
- Con el servidor iniciado, ejecuta `ollama pull qwen3:4b` y comprueba el modelo con `ollama list`. Ejecuta de nuevo `Test-JarvisSetup.ps1`.

## Uso y comprobaciones

Pulsa **Grabar**, habla y pulsa **Detener grabación**. La aplicación muestra la transcripción y la respuesta. Para conversar por teclado, escribe un mensaje y pulsa Intro o **Enviar**. El contexto conserva hasta seis turnos anteriores durante la sesión en curso.

Ejecuta la suite con `.\.venv\Scripts\python.exe -m pytest`. Las verificaciones manuales requieren Windows y los modelos instalados.

| Prueba manual | Resultado esperado |
| --- | --- |
| Abre JARVIS con Ollama detenido y pulsa **Verificar** después de iniciarlo | El estado indica primero que Ollama no está disponible y luego muestra el modelo instalado. |
| Escribe «Mi ciudad favorita es Valdivia» y después «¿Cuál es mi ciudad favorita?» | El modelo responde usando el contexto del turno anterior. |
| Graba una pregunta en español y detén la grabación | El indicador reacciona al micrófono. Aparecen la transcripción y la respuesta, y luego se oye la voz. |
| Graba y alcanza la duración máxima, o detén la grabación de inmediato | Al alcanzar el límite se inicia la transcripción. Una captura demasiado corta produce un mensaje recuperable. |
| Cambia micrófono y altavoces. Desconecta un dispositivo elegido y vuelve a seleccionar uno disponible | JARVIS informa del fallo y permite volver a intentar. |
| Cambia temporalmente la ruta de Whisper y después la de Piper | La comprobación indica el archivo ausente. Con Piper ausente, la respuesta de texto sigue visible. |
| Cierra la ventana durante la grabación, la inferencia o la voz | El proceso de JARVIS termina y Windows vuelve a permitir el uso de los dispositivos. Ollama sigue disponible para otras aplicaciones. |
| Desconecta internet tras completar la preparación | Los turnos de texto y voz siguen funcionando con los modelos locales. |

## Licencias de las dependencias

Ollama y whisper.cpp se publican bajo MIT, el Qwen3-4B oficial bajo Apache 2.0 y Piper actual bajo GPL-3.0. Piper se instala como dependencia separada y JARVIS lo invoca mediante su CLI. La ficha de Sharvard acredita el conjunto de entrenamiento bajo CC BY 3.0 y el repositorio de voces declara MIT. [Ollama](https://github.com/ollama/ollama/blob/main/LICENSE) · [whisper.cpp](https://github.com/ggml-org/whisper.cpp/blob/master/LICENSE) · [Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B) · [Piper](https://github.com/OHF-Voice/piper1-gpl) · [Ficha de Sharvard](https://huggingface.co/rhasspy/piper-voices/blob/main/es/es_ES/sharvard/medium/MODEL_CARD)

PySide6 ofrece LGPL/GPL y licencia comercial. sounddevice usa MIT, soundfile y NumPy BSD-3-Clause, y pytest MIT. El uso local descrito aquí emplea las distribuciones abiertas. [PySide6](https://pypi.org/project/PySide6/6.8.3/) · [sounddevice](https://pypi.org/project/sounddevice/) · [soundfile](https://pypi.org/project/soundfile/) · [NumPy](https://pypi.org/project/numpy/) · [pytest](https://pypi.org/project/pytest/)
