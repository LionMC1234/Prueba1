#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo AssistantManager
-----------------------
Gestiona y coordina todos los componentes del asistente personal virtual.
"""

import logging
import threading
import time
import os
from typing import Dict, Any, List, Optional

from assistant.modules.voice_input import VoiceInputManager
from assistant.modules.voice_output import VoiceOutputManager
from assistant.modules.ai_processor import AIProcessor
from assistant.modules.skill_manager import SkillManager
from assistant.utils.event_bus import EventBus
from assistant.utils.system_info import SystemInfo
from assistant.utils.api_manager import ApiManager

class AssistantManager:
    """Clase principal que gestiona todos los componentes del asistente."""

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el gestor del asistente.

        Args:
            config: Diccionario con la configuración del asistente
        """
        self.logger = logging.getLogger("assistant")
        self.logger.info("Inicializando AssistantManager")

        self.config = config
        self.running = False
        self.paused = False
        self.conversation_history: List[Dict[str, str]] = []

        # Inicializar el bus de eventos para comunicación entre componentes
        self.event_bus = EventBus()

        # Inicializar el gestor de API
        self.api_manager = ApiManager(self.config)

        # Inicializar módulos principales
        self._init_modules()

        # Registrar manejadores de eventos
        self._register_event_handlers()

        self.logger.info("AssistantManager inicializado correctamente")

    def _init_modules(self) -> None:
        """Inicializa todos los módulos del asistente."""
        # Cargar información del sistema
        self.system_info = SystemInfo()

        # Inicializar procesador de IA
        self.ai_processor = AIProcessor(
            self.config["ai"],
            self.event_bus
        )

        # Inicializar gestor de habilidades
        self.skill_manager = SkillManager(
            self.config["skills"],
            self.event_bus,
            self.ai_processor
        )

        # Inicializar módulos de voz (si están habilitados)
        if self.config["voice"]["input"]["enabled"]:
            self.voice_input = VoiceInputManager(
                self.config["voice"]["input"],
                self.event_bus,
                wake_word=self.config["assistant"]["wake_word"]
            )
        else:
            self.voice_input = None

        if self.config["voice"]["output"]["enabled"]:
            self.voice_output = VoiceOutputManager(
                self.config["voice"]["output"],
                self.event_bus
            )
        else:
            self.voice_output = None

    def _register_event_handlers(self) -> None:
        """Registra los manejadores de eventos para el bus de eventos."""
        self.event_bus.subscribe("voice_input_received", self._handle_voice_input)
        self.event_bus.subscribe("ai_response_received", self._handle_ai_response)
        self.event_bus.subscribe("skill_command_detected", self._handle_skill_command)
        self.event_bus.subscribe("system_command", self._handle_system_command)
        self.event_bus.subscribe("error", self._handle_error)

    def _handle_voice_input(self, data: Dict[str, Any]) -> None:
        """
        Maneja el evento de entrada de voz.

        Args:
            data: Datos del evento con la transcripción de voz
        """
        if not data.get("text"):
            return

        self.logger.debug(f"Entrada de voz recibida: {data['text']}")

        # Añadir a la historia de conversación
        self.conversation_history.append({"role": "user", "content": data["text"]})

        # Procesar con IA y habilidades
        # Primero verificar si es un comando para alguna habilidad
        if not self.skill_manager.process_command(data["text"]):
            # Si no es un comando específico, enviar a la IA
            self.ai_processor.process_input(data["text"], self.conversation_history)

    def _handle_ai_response(self, data: Dict[str, Any]) -> None:
        """
        Maneja el evento de respuesta de la IA.

        Args:
            data: Datos del evento con la respuesta de la IA
        """
        response = data.get("response", "")
        self.logger.debug(f"Respuesta de IA recibida: {response[:50]}...")

        # Añadir a la historia de conversación
        self.conversation_history.append({"role": "assistant", "content": response})

        # Limitar el tamaño de la historia de conversación
        max_history = self.config["ai"].get("context_window_size", 10)
        if len(self.conversation_history) > max_history * 2:  # multiplicamos por 2 para considerar pares de mensajes
            self.conversation_history = self.conversation_history[-max_history*2:]

        # Enviar al sistema de voz si está habilitado
        if self.voice_output:
            self.voice_output.speak(response)
        else:
            print(f"Asistente: {response}")

    def _handle_skill_command(self, data: Dict[str, Any]) -> None:
        """
        Maneja el evento de comando de habilidad detectado.

        Args:
            data: Datos del evento con el resultado de la habilidad
        """
        self.logger.debug(f"Resultado de habilidad: {data.get('skill')}")

        # Si la habilidad produjo una respuesta, enviarla al sistema de voz
        response = data.get("response", "")
        if response and self.voice_output:
            self.voice_output.speak(response)
        elif response:
            print(f"Asistente: {response}")

        # Añadir a la historia de conversación si hay respuesta
        if response:
            self.conversation_history.append({"role": "assistant", "content": response})

    def _handle_system_command(self, data: Dict[str, Any]) -> None:
        """
        Maneja el evento de comando del sistema.

        Args:
            data: Datos del evento con el comando del sistema
        """
        command = data.get("command", "")

        if command == "pause":
            self.pause()
        elif command == "resume":
            self.resume()
        elif command == "stop":
            self.stop()

    def _handle_error(self, data: Dict[str, Any]) -> None:
        """
        Maneja el evento de error.

        Args:
            data: Datos del evento con la información del error
        """
        error_msg = data.get("message", "Error desconocido")
        error_source = data.get("source", "sistema")

        self.logger.error(f"Error en {error_source}: {error_msg}")

        # Notificar al usuario del error si es grave
        if data.get("critical", False) and self.voice_output:
            self.voice_output.speak(f"Lo siento, ha ocurrido un error: {error_msg}")

    def run(self) -> None:
        """Inicia la ejecución del asistente."""
        self.logger.info("Iniciando el asistente")
        self.running = True

        # Reproducir sonido de inicio si está configurado
        if self.config["assistant"].get("startup_sound", False) and self.voice_output:
            self.voice_output.play_sound("startup")

        # Iniciar módulos en hilos separados si es necesario
        if self.voice_input:
            self.voice_input.start()

        # Ejecutar el bucle principal
        try:
            self._main_loop()
        except Exception as e:
            self.logger.error(f"Error en el bucle principal: {str(e)}", exc_info=True)
        finally:
            self.stop()

    def _main_loop(self) -> None:
        """Bucle principal del asistente."""
        self.logger.info("Bucle principal del asistente iniciado")
        print(f"Asistente '{self.config['assistant']['name']}' está escuchando... (Ctrl+C para salir)")

        # Mantener el proceso principal activo
        while self.running:
            time.sleep(0.1)  # Pequeña pausa para no consumir CPU innecesariamente

            # Aquí podríamos añadir comprobaciones periódicas, como:
            # - Verificar la carga del sistema
            # - Comprobar actualizaciones
            # - Ejecutar tareas programadas

    def pause(self) -> None:
        """Pausa temporalmente el asistente."""
        if not self.paused:
            self.logger.info("Pausando el asistente")
            self.paused = True

            # Pausar módulos
            if self.voice_input:
                self.voice_input.pause()

    def resume(self) -> None:
        """Reanuda el asistente después de una pausa."""
        if self.paused:
            self.logger.info("Reanudando el asistente")
            self.paused = False

            # Reanudar módulos
            if self.voice_input:
                self.voice_input.resume()

    def stop(self) -> None:
        """Detiene completamente el asistente."""
        if self.running:
            self.logger.info("Deteniendo el asistente")
            self.running = False

            # Reproducir sonido de apagado si está configurado
            if self.config["assistant"].get("shutdown_sound", False) and self.voice_output:
                self.voice_output.play_sound("shutdown")

            # Detener módulos
            if self.voice_input:
                self.voice_input.stop()

            # Cerrar recursos
            self.skill_manager.close()
            self.ai_processor.close()

            self.logger.info("Asistente detenido correctamente")