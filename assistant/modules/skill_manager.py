#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo SkillManager
------------------
Gestiona las habilidades del asistente, detectando y ejecutando comandos específicos.
"""

import os
import sys
import importlib
import importlib.util
import inspect
import re
import logging
import glob
import json
import time
from typing import Dict, Any, List, Callable, Optional, Union, Tuple, Type

from assistant.utils.event_bus import EventBus
from assistant.utils.api_manager import ApiManager, ApiManagerError
from assistant.modules.weather_function import WeatherFunction
from assistant.modules.reminder_function import ReminderFunction

class Skill:
    """Clase base para todas las habilidades."""

    def __init__(self, config: Dict[str, Any], event_bus: EventBus, api_manager: Optional[ApiManager] = None):
        """
        Inicializa la habilidad.

        Args:
            config: Configuración de la habilidad
            event_bus: Bus de eventos para comunicación
            api_manager: Gestor de API para acceder a las credenciales (opcional)
        """
        self.config = config
        self.event_bus = event_bus
        self.api_manager = api_manager
        self.name = self.__class__.__name__.lower().replace('skill', '')
        self.logger = logging.getLogger(f"assistant.skill.{self.name}")

        # Comandos soportados por la habilidad
        self.commands: Dict[str, Callable] = {}

        # Patrones de expresiones regulares para detectar comandos
        self.patterns: List[Tuple[re.Pattern, Callable]] = []

        # Inicializar la habilidad
        self.initialize()

    def initialize(self) -> None:
        """
        Inicializa la habilidad. Este método debe ser sobrescrito por las subclases.
        """
        pass

    def register_command(self, command: str, handler: Callable) -> None:
        """
        Registra un comando para la habilidad.

        Args:
            command: Nombre del comando (en minúsculas)
            handler: Función que maneja el comando
        """
        self.commands[command.lower()] = handler
        self.logger.debug(f"Comando registrado: {command}")

    def register_pattern(self, pattern: str, handler: Callable) -> None:
        """
        Registra un patrón de expresión regular para detectar comandos.

        Args:
            pattern: Patrón de expresión regular
            handler: Función que maneja el comando
        """
        compiled_pattern = re.compile(pattern, re.IGNORECASE)
        self.patterns.append((compiled_pattern, handler))
        self.logger.debug(f"Patrón registrado: {pattern}")

    def handle_command(self, command: str, text: str) -> bool:
        """
        Maneja un comando específico.

        Args:
            command: Comando a ejecutar
            text: Texto completo del usuario

        Returns:
            True si se manejó el comando, False en caso contrario
        """
        command = command.lower()
        if command in self.commands:
            self.logger.info(f"Ejecutando comando: {command}")
            self.commands[command](text)
            return True
        return False

    def match_patterns(self, text: str) -> bool:
        """
        Verifica si el texto coincide con algún patrón registrado.

        Args:
            text: Texto del usuario

        Returns:
            True si se encontró y manejó un patrón, False en caso contrario
        """
        for pattern, handler in self.patterns:
            match = pattern.search(text)
            if match:
                self.logger.info(f"Patrón coincidente: {pattern.pattern}")
                handler(text, match)
                return True
        return False

    def process(self, text: str) -> bool:
        """
        Procesa el texto del usuario y ejecuta la acción correspondiente.

        Args:
            text: Texto del usuario

        Returns:
            True si la habilidad procesó el texto, False en caso contrario
        """
        # Verificar patrones primero
        if self.match_patterns(text):
            return True

        # Luego verificar comandos directos
        words = text.lower().split()
        for word in words:
            if word in self.commands:
                return self.handle_command(word, text)

        return False

    def get_api_key(self, provider: str) -> str:
        """
        Obtiene una clave API para un servicio específico.

        Args:
            provider: Nombre del proveedor del servicio

        Returns:
            Clave API si está disponible

        Raises:
            Exception: Si no se puede obtener la clave API
        """
        if self.api_manager:
            try:
                return self.api_manager.get_api_key(provider)
            except ApiManagerError as e:
                self.logger.warning(f"No se pudo obtener la clave API para {provider}: {str(e)}")
                raise

        # Fallback a la configuración de la habilidad
        if "api_key" in self.config:
            return self.config["api_key"]

        raise Exception(f"No se ha configurado la clave API para {provider}")

class WeatherSkill(Skill):
    """Habilidad para consultar el clima."""

    def initialize(self) -> None:
        """Inicializa la habilidad del clima."""
        # Registrar comandos
        self.register_command("clima", self.get_weather)
        self.register_command("temperatura", self.get_weather)

        # Registrar patrones
        self.register_pattern(r"cómo está el clima (en|para) ([a-zA-Z ,]+)", self.get_weather_for_location)
        self.register_pattern(r"temperatura (en|para|de) ([a-zA-Z ,]+)", self.get_temperature_for_location)
        self.register_pattern(r"va a llover", self.get_rain_forecast)

        self.logger.info("Habilidad de clima inicializada")

    def get_weather(self, text: str) -> None:
        """
        Obtiene la información del clima actual.

        Args:
            text: Texto completo del usuario
        """
        # TODO: Implementar llamada a API de clima
        location = self.config.get("default_location", "Madrid, España")

        # Intentar obtener la clave API si es necesario
        try:
            if self.api_manager:
                api_key = self.api_manager.get_api_key("weather")
                self.logger.debug(f"Usando API key para servicio meteorológico: {api_key[:5]}...")
        except:
            self.logger.debug("No se pudo obtener la clave API para el servicio meteorológico")

        # Simular respuesta
        response = f"Actualmente en {location} el clima es despejado con una temperatura de 22°C."

        # Publicar respuesta
        self.event_bus.publish("skill_command_detected", {
            "skill": "weather",
            "command": "get_weather",
            "response": response
        })

    def get_weather_for_location(self, text: str, match: re.Match) -> None:
        """
        Obtiene el clima para una ubicación específica.

        Args:
            text: Texto completo del usuario
            match: Objeto de coincidencia de la expresión regular
        """
        location = match.group(2).strip()

        # TODO: Implementar llamada a API de clima

        # Simular respuesta
        response = f"El clima en {location} es mayormente soleado con una temperatura de 24°C."

        # Publicar respuesta
        self.event_bus.publish("skill_command_detected", {
            "skill": "weather",
            "command": "get_weather_for_location",
            "location": location,
            "response": response
        })

    def get_temperature_for_location(self, text: str, match: re.Match) -> None:
        """
        Obtiene la temperatura para una ubicación específica.

        Args:
            text: Texto completo del usuario
            match: Objeto de coincidencia de la expresión regular
        """
        location = match.group(2).strip()

        # TODO: Implementar llamada a API de clima

        # Simular respuesta
        response = f"La temperatura actual en {location} es de 23°C."

        # Publicar respuesta
        self.event_bus.publish("skill_command_detected", {
            "skill": "weather",
            "command": "get_temperature_for_location",
            "location": location,
            "response": response
        })

    def get_rain_forecast(self, text: str, match: re.Match) -> None:
        """
        Obtiene el pronóstico de lluvia.

        Args:
            text: Texto completo del usuario
            match: Objeto de coincidencia de la expresión regular
        """
        location = self.config.get("default_location", "Madrid, España")

        # TODO: Implementar llamada a API de clima

        # Simular respuesta
        response = f"No hay pronóstico de lluvia para las próximas horas en {location}."

        # Publicar respuesta
        self.event_bus.publish("skill_command_detected", {
            "skill": "weather",
            "command": "get_rain_forecast",
            "response": response
        })

class TimeSkill(Skill):
    """Habilidad para consultar la hora y fecha."""

    def initialize(self) -> None:
        """Inicializa la habilidad de tiempo."""
        # Registrar comandos
        self.register_command("hora", self.get_time)
        self.register_command("fecha", self.get_date)

        # Registrar patrones
        self.register_pattern(r"qué hora es", self.get_time)
        self.register_pattern(r"qué día es hoy", self.get_date)

        self.logger.info("Habilidad de tiempo inicializada")

    def get_time(self, text: str, match: re.Match = None) -> None:
        """
        Obtiene la hora actual.

        Args:
            text: Texto completo del usuario
            match: Objeto de coincidencia de la expresión regular (opcional)
        """
        import datetime
        now = datetime.datetime.now()

        # Formatear la hora
        time_str = now.strftime("%H:%M")

        # Respuesta
        response = f"Son las {time_str}."

        # Publicar respuesta
        self.event_bus.publish("skill_command_detected", {
            "skill": "time",
            "command": "get_time",
            "response": response
        })

    def get_date(self, text: str, match: re.Match = None) -> None:
        """
        Obtiene la fecha actual.

        Args:
            text: Texto completo del usuario
            match: Objeto de coincidencia de la expresión regular (opcional)
        """
        import datetime
        import locale

        # Intentar configurar el locale a español
        try:
            locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
        except:
            try:
                locale.setlocale(locale.LC_TIME, "es_ES")
            except:
                pass

        now = datetime.datetime.now()

        # Formatear la fecha
        try:
            date_str = now.strftime("%A %d de %B de %Y")
            date_str = date_str.capitalize()
        except:
            # Fallback en caso de error con locale
            months = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                      "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
            days = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

            day_name = days[now.weekday()]
            month_name = months[now.month - 1]
            date_str = f"{day_name} {now.day} de {month_name} de {now.year}"

        # Respuesta
        response = f"Hoy es {date_str}."

        # Publicar respuesta
        self.event_bus.publish("skill_command_detected", {
            "skill": "time",
            "command": "get_date",
            "response": response
        })

class SystemSkill(Skill):
    """Habilidad para controlar el sistema."""

    def initialize(self) -> None:
        """Inicializa la habilidad del sistema."""
        # Registrar comandos
        self.register_command("apagar", self.shutdown)
        self.register_command("reiniciar", self.restart)
        self.register_command("silencio", self.mute)

        # Registrar patrones
        self.register_pattern(r"apaga (el|al) asistente", self.shutdown)
        self.register_pattern(r"reinicia (el|al) asistente", self.restart)
        self.register_pattern(r"guarda silencio", self.mute)

        self.logger.info("Habilidad de sistema inicializada")

    def shutdown(self, text: str, match: re.Match = None) -> None:
        """
        Apaga el asistente.

        Args:
            text: Texto completo del usuario
            match: Objeto de coincidencia de la expresión regular (opcional)
        """
        response = "Apagando el asistente. Hasta pronto."

        # Publicar respuesta
        self.event_bus.publish("skill_command_detected", {
            "skill": "system",
            "command": "shutdown",
            "response": response
        })

        # Enviar comando de sistema para apagar
        self.event_bus.publish("system_command", {
            "command": "stop"
        })

    def restart(self, text: str, match: re.Match = None) -> None:
        """
        Reinicia el asistente.

        Args:
            text: Texto completo del usuario
            match: Objeto de coincidencia de la expresión regular (opcional)
        """
        response = "Reiniciando el asistente. Espere un momento."

        # Publicar respuesta
        self.event_bus.publish("skill_command_detected", {
            "skill": "system",
            "command": "restart",
            "response": response
        })

        # Enviar comandos de sistema para reiniciar
        self.event_bus.publish("system_command", {
            "command": "stop"
        })

        # En un caso real, aquí se iniciaría un proceso para reiniciar el sistema

    def mute(self, text: str, match: re.Match = None) -> None:
        """
        Silencia temporalmente el asistente.

        Args:
            text: Texto completo del usuario
            match: Objeto de coincidencia de la expresión regular (opcional)
        """
        response = "Me mantendré en silencio hasta que me necesites."

        # Publicar respuesta
        self.event_bus.publish("skill_command_detected", {
            "skill": "system",
            "command": "mute",
            "response": response
        })

        # Enviar comando de sistema para pausar
        self.event_bus.publish("system_command", {
            "command": "pause"
        })

class SkillManager:
    """
    Gestor de habilidades del asistente.
    Carga, gestiona y ejecuta las habilidades disponibles.
    """

    def __init__(self, config: Dict[str, Any], event_bus: EventBus, ai_processor=None):
        """
        Inicializa el gestor de habilidades.

        Args:
            config: Configuración de las habilidades
            event_bus: Bus de eventos para comunicación
            ai_processor: Procesador de IA para habilidades que requieren NLP
        """
        self.logger = logging.getLogger("assistant.skills")
        self.config = config
        self.event_bus = event_bus
        self.ai_processor = ai_processor

        # Inicializar el gestor de API
        self.api_manager = ApiManager({"skills": config})

        # Habilidades disponibles
        self.skills: Dict[str, Skill] = {}

        # Cargar las habilidades incorporadas
        self._load_builtin_skills()

        # Cargar las habilidades externas
        self._load_external_skills()

        # Registrar funciones para llamadas automáticas si hay procesador de IA
        if self.ai_processor:
            self._register_functions()

        self.logger.info(f"Gestor de habilidades inicializado con {len(self.skills)} habilidades")

    def _register_functions(self) -> None:
        """
        Registra las funciones que pueden ser llamadas automáticamente por el asistente.
        """
        # Registrar función de clima si está habilitada
        if "weather" in self.config and self.config["weather"].get("enabled", True):
            try:
                # Inicializar la función de clima
                weather_config = self.config.get("weather", {})
                weather_function = WeatherFunction(weather_config)

                # Obtener la definición de la función
                weather_function_def = weather_function.get_weather_function_definition()

                # Registrar la función en el procesador de IA
                self.ai_processor.register_function(
                    weather_function_def,
                    weather_function.get_weather
                )

                self.logger.info("Función de clima registrada para llamadas automáticas")
            except Exception as e:
                self.logger.error(f"Error al registrar función de clima: {str(e)}", exc_info=True)

        # Registrar función de recordatorios si está habilitada
        if "reminders" in self.config and self.config["reminders"].get("enabled", True):
            try:
                # Inicializar la función de recordatorios
                reminders_config = self.config.get("reminders", {})
                reminder_function = ReminderFunction(reminders_config, self.event_bus)

                # Obtener la definición de la función
                reminder_function_def = reminder_function.get_reminder_function_definition()

                # Registrar la función en el procesador de IA
                self.ai_processor.register_function(
                    reminder_function_def,
                    reminder_function.create_reminder
                )

                self.logger.info("Función de recordatorios registrada para llamadas automáticas")
            except Exception as e:
                self.logger.error(f"Error al registrar función de recordatorios: {str(e)}", exc_info=True)

        # Aquí se pueden registrar más funciones para otras habilidades

    def _load_builtin_skills(self) -> None:
        """Carga las habilidades incorporadas en el asistente."""
        # Habilidades básicas incorporadas
        builtin_skills = {
            "weather": WeatherSkill,
            "time": TimeSkill,
            "system": SystemSkill
        }

        for name, skill_class in builtin_skills.items():
            if name in self.config and self.config[name].get("enabled", True):
                try:
                    skill_config = self.config.get(name, {})
                    skill = skill_class(skill_config, self.event_bus, self.api_manager)
                    self.skills[name] = skill
                    self.logger.info(f"Habilidad incorporada cargada: {name}")
                except Exception as e:
                    self.logger.error(f"Error al cargar habilidad incorporada {name}: {str(e)}", exc_info=True)

    def _load_external_skills(self) -> None:
        """Carga las habilidades externas desde el directorio de habilidades."""
        # Directorio de habilidades
        skills_dir = os.path.join(os.path.dirname(__file__), "..", "skills")

        if not os.path.exists(skills_dir):
            self.logger.debug(f"Directorio de habilidades no encontrado: {skills_dir}")
            return

        # Buscar archivos Python en el directorio de habilidades
        skill_files = glob.glob(os.path.join(skills_dir, "*_skill.py"))

        for skill_file in skill_files:
            try:
                # Obtener el nombre del módulo
                module_name = os.path.basename(skill_file)[:-3]  # Quitar la extensión .py
                skill_name = module_name.replace("_skill", "")

                # Verificar si la habilidad está habilitada
                if skill_name in self.config and not self.config[skill_name].get("enabled", True):
                    self.logger.debug(f"Habilidad externa deshabilitada: {skill_name}")
                    continue

                # Importar el módulo
                spec = importlib.util.spec_from_file_location(module_name, skill_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Buscar la clase de habilidad en el módulo
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and issubclass(obj, Skill) and obj != Skill and
                        name.lower().endswith("skill")):
                        # Instanciar la habilidad
                        skill_config = self.config.get(skill_name, {})
                        skill = obj(skill_config, self.event_bus, self.api_manager)
                        self.skills[skill_name] = skill
                        self.logger.info(f"Habilidad externa cargada: {skill_name}")
                        break

            except Exception as e:
                self.logger.error(f"Error al cargar habilidad externa {skill_file}: {str(e)}", exc_info=True)

    def process_command(self, text: str) -> bool:
        """
        Procesa un comando del usuario, detectando y ejecutando la habilidad correspondiente.

        Args:
            text: Texto del usuario

        Returns:
            True si se procesó el comando, False en caso contrario
        """
        if not text:
            return False

        self.logger.debug(f"Procesando comando: {text}")

        # Procesar con cada habilidad hasta que una lo maneje
        for name, skill in self.skills.items():
            try:
                if skill.process(text):
                    self.logger.info(f"Comando procesado por habilidad: {name}")
                    return True
            except Exception as e:
                self.logger.error(f"Error en habilidad {name}: {str(e)}", exc_info=True)

        # Si llegamos aquí, ninguna habilidad manejó el comando
        return False

    def get_skill(self, name: str) -> Optional[Skill]:
        """
        Obtiene una habilidad por su nombre.

        Args:
            name: Nombre de la habilidad

        Returns:
            La habilidad si existe, None en caso contrario
        """
        return self.skills.get(name.lower())

    def close(self) -> None:
        """Libera los recursos utilizados por las habilidades."""
        self.logger.debug("Cerrando gestor de habilidades")

        # Cerrar cada habilidad si tiene método close
        for name, skill in self.skills.items():
            try:
                if hasattr(skill, "close") and callable(skill.close):
                    skill.close()
            except Exception as e:
                self.logger.error(f"Error al cerrar habilidad {name}: {str(e)}")
