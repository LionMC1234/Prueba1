#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo VoiceOutputManager
-------------------------
Gestiona la salida de voz del asistente, incluyendo la síntesis de voz
y la reproducción de sonidos del sistema.
"""

import os
import threading
import queue
import time
import logging
import tempfile
from typing import Dict, Any, List, Optional, Union
import io

from assistant.utils.event_bus import EventBus

# Variables globales para verificar las dependencias disponibles
GTTS_AVAILABLE = False
PYTTSX3_AVAILABLE = False
PYGAME_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    pass

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    pass

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    pass

class VoiceOutputError(Exception):
    """Excepción específica para errores de salida de voz."""
    pass

class VoiceOutputManager:
    """
    Gestor de salida de voz.
    Maneja la síntesis de voz y la reproducción de sonidos.
    """

    def __init__(self, config: Dict[str, Any], event_bus: EventBus):
        """
        Inicializa el gestor de salida de voz.

        Args:
            config: Configuración de la salida de voz
            event_bus: Bus de eventos para comunicación
        """
        self.logger = logging.getLogger("assistant.voice_output")
        self.config = config
        self.event_bus = event_bus

        # Cola de mensajes para síntesis
        self.message_queue = queue.Queue()

        # Estado de reproducción
        self.speaking = False
        self.running = True

        # Motor de síntesis seleccionado
        self.engine_name = config.get("engine", "system").lower()
        self.engine = None

        # Directorio de sonidos
        self.sounds_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "sounds")

        # Inicializar el motor de síntesis
        self._init_engine()

        # Inicializar pygame para reproducción de sonidos (si está disponible)
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
            except Exception as e:
                self.logger.warning(f"No se pudo inicializar el mezclador de audio: {str(e)}")

        # Iniciar el hilo de procesamiento
        self.processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True,
            name="VoiceSynthesisThread"
        )
        self.processing_thread.start()

        self.logger.info(f"Salida de voz inicializada con motor: {self.engine_name}")

    def _init_engine(self) -> None:
        """
        Inicializa el motor de síntesis de voz según la configuración.

        Raises:
            VoiceOutputError: Si no se puede inicializar el motor
        """
        engine_name = self.engine_name

        # Configurar según el motor seleccionado
        if engine_name == "gtts":
            if not GTTS_AVAILABLE:
                self.logger.warning("gTTS no está disponible, usando motor alternativo")
                return self._fallback_engine()

            # No es necesario inicializar gTTS, se usa directamente
            self.logger.debug("Motor gTTS seleccionado")

        elif engine_name == "pyttsx3":
            if not PYTTSX3_AVAILABLE:
                self.logger.warning("pyttsx3 no está disponible, usando motor alternativo")
                return self._fallback_engine()

            try:
                self.engine = pyttsx3.init()

                # Configurar propiedades
                voice_id = self.config.get("voice_id")
                if voice_id:
                    self.engine.setProperty("voice", voice_id)

                # Configurar velocidad (valores típicos: 150-200)
                rate = self.config.get("rate", 175)
                self.engine.setProperty("rate", rate)

                # Configurar volumen (0.0 a 1.0)
                volume = self.config.get("volume", 1.0)
                self.engine.setProperty("volume", volume)

                self.logger.debug(f"Motor pyttsx3 inicializado (rate={rate}, volume={volume})")

            except Exception as e:
                self.logger.error(f"Error al inicializar pyttsx3: {str(e)}", exc_info=True)
                return self._fallback_engine()

        elif engine_name == "espeak":
            # Comprobar si espeak está instalado
            try:
                import subprocess
                result = subprocess.run(["espeak", "--version"],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      check=False)

                if result.returncode != 0:
                    self.logger.warning("espeak no está instalado, usando motor alternativo")
                    return self._fallback_engine()

                self.logger.debug("Motor espeak seleccionado")

            except Exception as e:
                self.logger.error(f"Error al verificar espeak: {str(e)}", exc_info=True)
                return self._fallback_engine()

        elif engine_name == "system":
            # Intentar detectar el sistema y usar el motor apropiado
            import platform
            system = platform.system().lower()

            if system == "windows" and PYTTSX3_AVAILABLE:
                self.engine_name = "pyttsx3"
                return self._init_engine()
            elif system in ["linux", "darwin"] and GTTS_AVAILABLE:
                self.engine_name = "gtts"
                return self._init_engine()
            else:
                self.logger.warning("No se pudo determinar un motor adecuado para el sistema")
                return self._fallback_engine()

        else:
            self.logger.warning(f"Motor desconocido: {engine_name}, usando alternativa")
            return self._fallback_engine()

    def _fallback_engine(self) -> None:
        """
        Configura un motor de síntesis alternativo si el seleccionado no está disponible.

        Raises:
            VoiceOutputError: Si no hay ningún motor disponible
        """
        # Intentar con pyttsx3 primero
        if PYTTSX3_AVAILABLE:
            self.engine_name = "pyttsx3"
            try:
                self.engine = pyttsx3.init()
                rate = self.config.get("rate", 175)
                volume = self.config.get("volume", 1.0)
                self.engine.setProperty("rate", rate)
                self.engine.setProperty("volume", volume)
                self.logger.info("Usando pyttsx3 como motor alternativo")
                return
            except:
                pass

        # Luego probar con gTTS
        if GTTS_AVAILABLE:
            self.engine_name = "gtts"
            self.logger.info("Usando gTTS como motor alternativo")
            return

        # Finalmente probar con espeak
        try:
            import subprocess
            result = subprocess.run(["espeak", "--version"],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  check=False)

            if result.returncode == 0:
                self.engine_name = "espeak"
                self.logger.info("Usando espeak como motor alternativo")
                return
        except:
            pass

        # Si no hay ningún motor disponible
        self.logger.error("No hay motores de síntesis de voz disponibles")
        raise VoiceOutputError("No hay motores de síntesis de voz disponibles")

    def _processing_loop(self) -> None:
        """
        Bucle principal para procesar la cola de mensajes de voz.
        """
        self.logger.debug("Iniciando bucle de procesamiento de voz")

        while self.running:
            try:
                # Obtener el siguiente mensaje de la cola (con timeout)
                try:
                    message = self.message_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Procesar el mensaje
                self.speaking = True

                # Verificar si es un mensaje especial
                if isinstance(message, dict):
                    if message.get("type") == "sound":
                        self._play_sound_file(message.get("sound_name", ""))
                else:
                    # Es un mensaje de texto normal
                    self._synthesize_speech(message)

                self.speaking = False
                self.message_queue.task_done()

                # Publicar evento de síntesis completada
                self.event_bus.publish("speech_synthesis_completed", {})

            except Exception as e:
                self.logger.error(f"Error en el bucle de procesamiento de voz: {str(e)}", exc_info=True)
                self.speaking = False

        self.logger.debug("Bucle de procesamiento de voz terminado")

    def _synthesize_speech(self, text: str) -> None:
        """
        Sintetiza y reproduce el texto utilizando el motor configurado.

        Args:
            text: Texto a sintetizar
        """
        if not text:
            return

        self.logger.debug(f"Sintetizando texto: {text[:50]}...")

        try:
            # Usar el motor seleccionado
            if self.engine_name == "gtts":
                self._synthesize_with_gtts(text)
            elif self.engine_name == "pyttsx3":
                self._synthesize_with_pyttsx3(text)
            elif self.engine_name == "espeak":
                self._synthesize_with_espeak(text)
            else:
                self.logger.warning(f"Motor no soportado: {self.engine_name}")

        except Exception as e:
            self.logger.error(f"Error al sintetizar voz: {str(e)}", exc_info=True)

            # Notificar el error
            self.event_bus.publish("error", {
                "source": "voice_output",
                "message": f"Error al sintetizar voz: {str(e)}",
                "critical": False
            })

    def _synthesize_with_gtts(self, text: str) -> None:
        """
        Sintetiza el texto usando Google Text-to-Speech.

        Args:
            text: Texto a sintetizar
        """
        try:
            # Configuración de gTTS
            language = self.config.get("language", "es")[:2]  # Usar solo el código de idioma (es, en, etc.)

            # Crear objeto gTTS
            tts = gTTS(text=text, lang=language, slow=False)

            # Guardar en archivo temporal
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = temp_file.name

            # Guardar el audio
            tts.save(temp_path)

            # Reproducir el audio
            self._play_audio_file(temp_path)

            # Eliminar el archivo temporal
            try:
                os.unlink(temp_path)
            except:
                pass

        except Exception as e:
            self.logger.error(f"Error con gTTS: {str(e)}", exc_info=True)
            raise

    def _synthesize_with_pyttsx3(self, text: str) -> None:
        """
        Sintetiza el texto usando pyttsx3.

        Args:
            text: Texto a sintetizar
        """
        try:
            # Verificar que el motor esté inicializado
            if not self.engine:
                self.engine = pyttsx3.init()

                # Configurar propiedades si no se hizo antes
                rate = self.config.get("rate", 175)
                volume = self.config.get("volume", 1.0)
                self.engine.setProperty("rate", rate)
                self.engine.setProperty("volume", volume)

            # Reproducir el texto
            self.engine.say(text)
            self.engine.runAndWait()

        except Exception as e:
            self.logger.error(f"Error con pyttsx3: {str(e)}", exc_info=True)
            raise

    def _synthesize_with_espeak(self, text: str) -> None:
        """
        Sintetiza el texto usando espeak.

        Args:
            text: Texto a sintetizar
        """
        try:
            import subprocess

            # Configuración
            language = self.config.get("language", "es")[:2]
            voice = self.config.get("voice_id", "")
            rate = self.config.get("rate", 175)
            volume = self.config.get("volume", 1.0) * 100  # espeak usa 0-200

            # Construir el comando
            cmd = ["espeak", "-v", f"{language}{'+' + voice if voice else ''}", "-s", str(rate), "-a", str(int(volume))]

            # Ejecutar el comando
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.communicate(input=text.encode("utf-8"))

        except Exception as e:
            self.logger.error(f"Error con espeak: {str(e)}", exc_info=True)
            raise

    def _play_audio_file(self, file_path: str) -> None:
        """
        Reproduce un archivo de audio.

        Args:
            file_path: Ruta al archivo de audio
        """
        try:
            if PYGAME_AVAILABLE:
                # Usar pygame para reproducir el audio
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()

                # Esperar a que termine la reproducción
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            else:
                # Alternativa usando playsound si está disponible
                try:
                    from playsound import playsound
                    playsound(file_path)
                except ImportError:
                    # Si no hay librerías de audio, usar alternativas del sistema
                    import platform
                    import subprocess

                    system = platform.system().lower()

                    if system == "darwin":  # macOS
                        subprocess.run(["afplay", file_path], check=False)
                    elif system == "linux":
                        subprocess.run(["aplay", file_path], check=False)
                    elif system == "windows":
                        import winsound
                        winsound.PlaySound(file_path, winsound.SND_FILENAME)
                    else:
                        self.logger.warning(f"No se puede reproducir audio en: {system}")

        except Exception as e:
            self.logger.error(f"Error al reproducir archivo de audio: {str(e)}", exc_info=True)

    def _play_sound_file(self, sound_name: str) -> None:
        """
        Reproduce un sonido del sistema.

        Args:
            sound_name: Nombre del sonido a reproducir
        """
        try:
            # Determinar la ruta del archivo de sonido
            if sound_name == "startup":
                sound_file = os.path.join(self.sounds_dir, "startup.mp3")
            elif sound_name == "shutdown":
                sound_file = os.path.join(self.sounds_dir, "shutdown.mp3")
            elif sound_name == "notification":
                sound_file = os.path.join(self.sounds_dir, "notification.mp3")
            elif sound_name == "wake":
                sound_file = os.path.join(self.sounds_dir, "wake.mp3")
            else:
                sound_file = os.path.join(self.sounds_dir, f"{sound_name}.mp3")

            # Verificar si el archivo existe
            if not os.path.exists(sound_file):
                self.logger.warning(f"Archivo de sonido no encontrado: {sound_file}")
                return

            # Reproducir el sonido
            self._play_audio_file(sound_file)

        except Exception as e:
            self.logger.error(f"Error al reproducir sonido: {str(e)}", exc_info=True)

    def speak(self, text: str) -> None:
        """
        Pone un mensaje en la cola para ser sintetizado.

        Args:
            text: Texto a sintetizar
        """
        if not text:
            return

        self.message_queue.put(text)

    def play_sound(self, sound_name: str) -> None:
        """
        Pone un sonido en la cola para ser reproducido.

        Args:
            sound_name: Nombre del sonido a reproducir
        """
        self.message_queue.put({"type": "sound", "sound_name": sound_name})

    def is_speaking(self) -> bool:
        """
        Indica si el asistente está hablando actualmente.

        Returns:
            True si está hablando, False en caso contrario
        """
        return self.speaking

    def stop_speaking(self) -> None:
        """Detiene la síntesis de voz actual."""
        # Vaciar la cola de mensajes
        with self.message_queue.mutex:
            self.message_queue.queue.clear()

        # Detener la reproducción actual
        if PYGAME_AVAILABLE and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

        # Si se está usando pyttsx3, intentar detenerlo
        if self.engine_name == "pyttsx3" and self.engine:
            try:
                self.engine.stop()
            except:
                pass

        self.speaking = False

    def close(self) -> None:
        """Libera los recursos utilizados por el gestor de salida de voz."""
        self.logger.debug("Cerrando gestor de salida de voz")

        # Detener el hilo de procesamiento
        self.running = False

        # Detener la síntesis actual
        self.stop_speaking()

        # Esperar a que termine el hilo
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2.0)

        # Liberar recursos del motor
        if self.engine_name == "pyttsx3" and self.engine:
            try:
                self.engine.stop()
            except:
                pass

        # Cerrar pygame si está en uso
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.quit()
            except:
                pass
