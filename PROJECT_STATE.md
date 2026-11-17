# Estado del proyecto

## Misión 001 · 17 de noviembre de 2026

Implementé la primera versión de JARVIS con PySide6, estados conversacionales, entrada de texto y micrófono, visualizador RMS, selección de dispositivos y verificación de proveedores. El flujo usa Ollama con Qwen 3, whisper.cpp y Piper mediante interfaces reemplazables. El contexto reside en memoria. La configuración se guarda en los datos locales del usuario y los WAV se eliminan al terminar cada turno normal.

Seleccioné `qwen3:4b`, Whisper Base multilingüe, la voz es_ES Sharvard y una versión de Qt 6.8 con soporte documentado para Windows 10 x64. La preparación usa whisper.cpp v1.8.2, con un ZIP x64 publicado. PowerShell solicita las descargas de modelos mediante parámetros explícitos.

### Verificado

- Se consultaron las fuentes oficiales para las licencias, las rutas de descarga, los formatos de instalación x64 y los parámetros de CLI. El README conserva los enlaces.
- Las 22 pruebas automatizadas pasaron con Python 3.12 en Linux mediante `python -m unittest discover -s tests -v`. Usa dobles para Ollama, Whisper, Piper y dispositivos de audio. Ejecuta procesos reales de Python para verificar la cancelación y el manejo de stdin.
- `python -m compileall -q jarvis tests` validó la sintaxis. El validador de instalación informa de componentes ausentes en el entorno de desarrollo.

### Pendiente

- Validar la instalación PowerShell y el arranque de PySide6 en Windows 10/11 x64. La conexión a PyPI desde este entorno devolvió un error de proxy, por lo que la suite todavía debe ejecutarse con pytest y las dependencias completas en Windows.
- Ejecutar las pruebas manuales del README con el hardware del usuario. Quedan pendientes una transcripción real, inferencia Qwen 3, síntesis Piper, captura y reproducción con equipos reales y cierre durante cada estado en Windows.
- Registrar aquí los resultados de las pruebas en el notebook. El proyecto permanece en la Misión 001.
