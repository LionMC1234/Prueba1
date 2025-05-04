#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo VoiceInputManager
-------------------------
Gestiona la entrada de voz del usuario, incluyendo la detección de la palabra clave
y el reconocimiento de voz.
"""

import os
import threading
import time
import logging
import queue
import json
import wave
import io
import tempfile
from typing import Dict, Any, List, Optional, Callable, Union
import numpy as np

from assistant.utils.event_bus import EventBus

# Variable global para verificar si se pueden importar las dependencias
SPEECH_RECOGNITION_AVAILABLE = False
PYAUDIO_AVAILABLE = False

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    pass

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    pass

class VoiceInputError(Exception):
    """Excepción específica para errores de entrada de voz."""
    pass

class VoiceInputManager:
    """
    Gestor de entrada de voz.
    Maneja la detección de la palabra clave y el reconocimiento de voz.
    """

    def __init__(self, config: Dict[str, Any], event_bus: EventBus, wake_word: str = "asistente"):
        """
        Inicializa el gestor de entrada de voz.

        Args:
            config: Configuración de la entrada de voz
            event_bus: Bus de eventos para comunicación
            wake_word: Palabra clave para activar el asistente

        Raises:
            VoiceInputError: Si no se pueden cargar las dependencias necesarias
        """
        self.logger = logging.getLogger("assistant.voice_input")
        self.config = config
        self.event_bus = event_bus
        self.wake_word = wake_word.lower()

        # Estado del reconocimiento
        self.running = False
        self.paused = False
        self.listening_for_command = False

        # Verificar dependencias
        if not SPEECH_RECOGNITION_AVAILABLE:
            error_msg = "No se pudo cargar speech_recognition, la entrada de voz no estará disponible"
            self.logger.error(error_msg)
            raise VoiceInputError(error_msg)

        if not PYAUDIO_AVAILABLE:
            error_msg = "No se pudo cargar pyaudio, la entrada de voz no estará disponible"
            self.logger.error(error_msg)
            raise VoiceInputError(error_msg)

        # Inicializar reconocedor de voz
        self.recognizer = sr.Recognizer()

        # Configurar parámetros del reconocedor
        self.recognizer.energy_threshold = config.get("energy_threshold", 300)
        self.recognizer.pause_threshold = config.get("pause_threshold", 0.8)
        self.recognizer.phrase_threshold = config.get("phrase_threshold", 0.3)
        self.recognizer.dynamic_energy_threshold = config.get("dynamic_energy_threshold", True)

        # Seleccionar el dispositivo de entrada
        self.device_index = config.get("device_index", None)

        # Thread de reconocimiento
        self.thread = None

        # Modo offline
        self.offline_mode = config.get("offline_mode", False)

        # Seleccionar motor de reconocimiento
        self.engine = config.get("engine", "system").lower()

        self.logger.info(f"Entrada de voz inicializada con motor: {self.engine}")

    def start(self) -> None:
        """Inicia el reconocimiento de voz en un hilo separado."""
        if self.running:
            return

        self.running = True
        self.paused = False

        self.logger.info("Iniciando reconocimiento de voz")

        # Crear e iniciar el hilo
        self.thread = threading.Thread(
            target=self._recognition_loop,
            daemon=True,
            name="VoiceRecognitionThread"
        )
        self.thread.start()

    def stop(self) -> None:
        """Detiene el reconocimiento de voz."""
        if not self.running:
            return

        self.logger.info("Deteniendo reconocimiento de voz")
        self.running = False

        # Esperar a que termine el hilo
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def pause(self) -> None:
        """Pausa temporalmente el reconocimiento de voz."""
        if not self.running or self.paused:
            return

        self.logger.info("Pausando reconocimiento de voz")
        self.paused = True

    def resume(self) -> None:
        """Reanuda el reconocimiento de voz después de una pausa."""
        if not self.running or not self.paused:
            return

        self.logger.info("Reanudando reconocimiento de voz")
        self.paused = False

    def _recognition_loop(self) -> None:
        """
        Bucle principal de reconocimiento de voz.
        Este método se ejecuta en un hilo separado.
        """
        self.logger.debug("Bucle de reconocimiento de voz iniciado")

        # Preparar el micrófono
        try:
            mic = sr.Microphone(device_index=self.device_index)

            # Ajuste de ruido (solo si el umbral de energía es dinámico)
            if self.recognizer.dynamic_energy_threshold:
                with mic as source:
                    self.logger.debug("Ajustando ruido ambiente...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    self.logger.debug(f"Umbral de energía ajustado a: {self.recognizer.energy_threshold}")

            # Bucle principal de reconocimiento
            while self.running:
                # Pausa si es necesario
                if self.paused:
                    time.sleep(0.1)
                    continue

                try:
                    with mic as source:
                        # Escuchar el audio
                        timeout = self.config.get("timeout", 5)
                        phrase_time_limit = None if self.listening_for_command else 3

                        self.logger.debug(f"Escuchando{'...' if self.listening_for_command else ' palabra clave...'}")
                        audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

                        # Procesar el audio
                        text = self._recognize_audio(audio)

                        if text:
                            text = text.lower()
                            self.logger.debug(f"Texto reconocido: {text}")

                            # Comprobar si estamos escuchando comandos o la palabra clave
                            if self.listening_for_command:
                                # Enviar el texto al sistema
                                self.event_bus.publish("voice_input_received", {
                                    "text": text,
                                    "confidence": 1.0  # No disponible en todos los motores
                                })

                                # Después de procesar un comando, volver a escuchar la palabra clave
                                self.listening_for_command = False
                            else:
                                # Comprobar si se ha dicho la palabra clave
                                if self.wake_word in text:
                                    self.logger.info(f"Palabra clave detectada: {self.wake_word}")

                                    # Activar el modo de escucha de comandos
                                    self.listening_for_command = True

                                    # Reproducir sonido o notificar al usuario
                                    self.event_bus.publish("wake_word_detected", {})

                except sr.WaitTimeoutError:
                    # Timeout al escuchar, continuar con el bucle
                    continue
                except sr.UnknownValueError:
                    # No se pudo reconocer el audio
                    continue
                except Exception as e:
                    self.logger.error(f"Error en bucle de reconocimiento: {str(e)}", exc_info=True)
                    time.sleep(1)  # Pausa para evitar bucles de error continuos

        except Exception as e:
            self.logger.error(f"Error crítico en reconocimiento de voz: {str(e)}", exc_info=True)

            # Notificar el error
            self.event_bus.publish("error", {
                "source": "voice_input",
                "message": f"Error en el sistema de reconocimiento de voz: {str(e)}",
                "critical": True
            })

            # Detener el reconocimiento
            self.running = False

        self.logger.debug("Bucle de reconocimiento de voz terminado")

    def _recognize_audio(self, audio: sr.AudioData) -> str:
        """
        Reconoce el texto a partir de los datos de audio.

        Args:
            audio: Datos de audio capturados

        Returns:
            Texto reconocido o cadena vacía si hay un error
        """
        try:
            language = self.config.get("language", "es-ES")

            # Usar el motor configurado
            if self.offline_mode:
                # En modo offline, usar motores locales
                return self._recognize_offline(audio)
            elif self.engine == "whisper":
                # Usar OpenAI Whisper API
                return self._recognize_with_whisper(audio)
            elif self.engine == "vosk":
                # Usar Vosk (reconocimiento local)
                return self._recognize_with_vosk(audio)
            else:
                # Usar el motor predeterminado de speech_recognition
                text = self.recognizer.recognize_google(audio, language=language)
                return text

        except sr.UnknownValueError:
            # Audio no reconocido
            return ""
        except sr.RequestError as e:
            self.logger.warning(f"Error de API en reconocimiento: {str(e)}")

            # Intentar con reconocimiento offline si falla la API
            if not self.offline_mode:
                self.logger.info("Intentando reconocimiento offline")
                return self._recognize_offline(audio)

            return ""
        except Exception as e:
            self.logger.error(f"Error al reconocer audio: {str(e)}", exc_info=True)
            return ""

    def _recognize_with_whisper(self, audio: sr.AudioData) -> str:
        """
        Reconoce audio usando la API de Whisper de OpenAI.

        Args:
            audio: Datos de audio capturados

        Returns:
            Texto reconocido o cadena vacía si hay un error
        """
        try:
            # Comprobar si la API está configurada
            if "OPENAI_API_KEY" not in os.environ and not self.config.get("whisper_api_key"):
                self.logger.warning("API key de Whisper no configurada")
                return ""

            # Convertir audio a formato wav
            wav_data = io.BytesIO(audio.get_wav_data())

            # Guardar en archivo temporal
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav_data.getvalue())
                temp_file = f.name

            try:
                # Usar OpenAI Whisper API
                from openai import OpenAI

                api_key = os.environ.get("OPENAI_API_KEY") or self.config.get("whisper_api_key", "")
                client = OpenAI(api_key=api_key)

                with open(temp_file, "rb") as audio_file:
                    response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language=self.config.get("language", "es")[:2]
                    )

                return response.text

            finally:
                # Eliminar archivo temporal
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

        except Exception as e:
            self.logger.error(f"Error con Whisper API: {str(e)}", exc_info=True)
            return ""

    def _recognize_with_vosk(self, audio: sr.AudioData) -> str:
        """
        Reconoce audio usando Vosk (reconocimiento local).

        Args:
            audio: Datos de audio capturados

        Returns:
            Texto reconocido o cadena vacía si hay un error
        """
        try:
            from vosk import Model, KaldiRecognizer, SetLogLevel

            # Suprimir logs de Vosk
            SetLogLevel(-1)

            # Comprobar si el modelo existe
            model_path = self.config.get("vosk_model_path", "models/vosk")
            if not os.path.exists(model_path):
                self.logger.warning(f"Modelo Vosk no encontrado en: {model_path}")
                return ""

            # Cargar modelo
            model = Model(model_path)

            # Obtener datos de audio en formato raw
            raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)

            # Crear reconocedor
            rec = KaldiRecognizer(model, 16000)

            # Procesar audio
            rec.AcceptWaveform(raw_data)
            result = json.loads(rec.FinalResult())

            return result.get("text", "")

        except ImportError:
            self.logger.warning("Vosk no está instalado")
            return ""
        except Exception as e:
            self.logger.error(f"Error con Vosk: {str(e)}", exc_info=True)
            return ""

    def _recognize_offline(self, audio: sr.AudioData) -> str:
        """
        Intenta reconocer audio en modo offline usando diferentes motores disponibles.

        Args:
            audio: Datos de audio capturados

        Returns:
            Texto reconocido o cadena vacía si hay un error
        """
        # Intentar con Vosk primero
        try:
            from vosk import Model, KaldiRecognizer, SetLogLevel

            # Comprobar si el modelo existe
            model_path = self.config.get("vosk_model_path", "models/vosk")
            if os.path.exists(model_path):
                SetLogLevel(-1)
                model = Model(model_path)
                raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
                rec = KaldiRecognizer(model, 16000)
                rec.AcceptWaveform(raw_data)
                result = json.loads(rec.FinalResult())
                text = result.get("text", "")
                if text:
                    return text
        except ImportError:
            pass
        except Exception as e:
            self.logger.debug(f"Error con Vosk offline: {str(e)}")

        # Intentar con Sphinx como alternativa
        try:
            text = self.recognizer.recognize_sphinx(audio, language=self.config.get("language", "es-ES")[:2])
            return text
        except sr.UnknownValueError:
            return ""
        except ImportError:
            self.logger.warning("PocketSphinx no está instalado")
            return ""
        except Exception as e:
            self.logger.debug(f"Error con Sphinx offline: {str(e)}")
            return ""
