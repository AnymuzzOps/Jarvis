# Arquitectura de JARVIS 1.0

| Módulo | Responsabilidad |
| --- | --- |
| `jarvis/ui` | Ventana PySide6, configuración, conversación y visualización del nivel RMS de entrada y salida. |
| `jarvis/core` | Estados, contratos de proveedores, turnos, historial, comprobaciones y gestión de procesos locales. |
| `jarvis/audio` | Grabación WAV mono PCM a 16 kHz con PortAudio y reproducción WAV por bloques con sounddevice y soundfile. |
| `jarvis/stt` | Invocación de whisper-cli en español y lectura de su salida. |
| `jarvis/llm` | Consulta de modelos instalados y generación mediante la API local de Ollama. |
| `jarvis/tts` | Síntesis WAV por Piper con entrada UTF-8. |
| `jarvis/config.py` | Validación de ajustes y guardado local atómico. |
| `tests` | Pruebas de estados, contratos, transporte, audio simulado y liberación de recursos. |

La ventana inicia un trabajador en segundo plano para verificar proveedores y enumerar dispositivos. Ese trabajador también ejecuta un turno a la vez y comunica cambios a Qt mediante señales. El orden de voz es **ESCUCHANDO → TRANSCRIBIENDO → PROCESANDO → HABLANDO → INACTIVO**. Un turno de texto comienza en **PROCESANDO**. Tras **ERROR** se puede volver a intentar o corregir la configuración.

`Session` recibe proveedores con los contratos `Transcriber`, `LanguageModel` y `SpeechSynthesizer`. Conserva hasta seis pares completos de pregunta y respuesta en memoria. La interfaz muestra la respuesta antes de intentar la síntesis. Si falla la salida de voz, la respuesta generada continúa visible y forma parte del contexto.

Las peticiones de Ollama salen directamente a una dirección de loopback y el cliente rechaza redirecciones HTTP. El arranque documentado de Ollama fija el enlace local y deshabilita la nube. El texto generado se usa como texto de interfaz y como entrada estándar de Piper. Los ejecutables de STT y TTS provienen de rutas configuradas por el usuario y se lanzan con argumentos separados.

Cada turno usa un directorio temporal que se libera al concluir. Al cerrar, la ventana pide detener la grabación y reproducción, interrumpe el socket de inferencia y cancela los procesos hijos de voz. Mantiene el bucle de Qt activo hasta que el trabajador libera sus recursos.
