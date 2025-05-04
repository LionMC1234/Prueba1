#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo ConfigManager
-------------------
Gestiona la configuración del asistente, cargando y validando los archivos de configuración.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
import copy
from dotenv import load_dotenv

class ConfigError(Exception):
    """Excepción lanzada cuando hay un error en la configuración."""
    pass

class ConfigManager:
    """
    Gestor de configuración para el asistente.
    Carga, valida y proporciona acceso a la configuración.
    """

    # Configuración por defecto
    DEFAULT_CONFIG = {
        "assistant": {
            "name": "Asistente",
            "version": "1.0.0",
            "language": "es-ES",
            "wake_word": "asistente",
            "voice_detection_sensitivity": 0.5,
            "timezone": "Europe/Madrid",
            "startup_sound": True,
            "shutdown_sound": True
        },
        "voice": {
            "input": {
                "enabled": True,
                "engine": "system",
                "device_index": None,
                "energy_threshold": 300,
                "pause_threshold": 0.8,
                "phrase_threshold": 0.3,
                "dynamic_energy_threshold": True,
                "timeout": 5,
                "offline_mode": False
            },
            "output": {
                "enabled": True,
                "engine": "system",
                "voice_id": None,
                "rate": 175,
                "volume": 1.0,
                "pitch": 1.0,
                "offline_mode": False
            }
        },
        "ai": {
            "provider": "openai",
            "model": "gpt-4",
            "max_tokens": 2048,
            "temperature": 0.7,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "system_prompt": "Eres un asistente personal virtual inteligente, útil, educado y conciso. Responde de manera clara y eficiente a las preguntas y solicitudes del usuario.",
            "context_window_size": 10,
            "api_key": "",
            "api_endpoint": "https://api.openai.com/v1",
            "stream_response": True,
            "fallback_to_offline": True
        },
        "system": {
            "log_level": "INFO",
            "log_file": "logs/assistant.log",
            "log_rotation": True,
            "max_log_size": 10,
            "backup_count": 5,
            "auto_update": False,
            "allow_telemetry": False,
            "cpu_limit": 80,
            "memory_limit": 75,
            "offline_capabilities": True
        }
    }

    def __init__(self, config_path: str):
        """
        Inicializa el gestor de configuración.

        Args:
            config_path: Ruta al archivo de configuración JSON

        Raises:
            ConfigError: Si hay un error al cargar o validar la configuración
        """
        self.logger = logging.getLogger("assistant.config")
        self.config_path = config_path
        self.config: Dict[str, Any] = {}

        # Cargar variables de entorno desde .env si existe
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
        if os.path.exists(env_path):
            self.logger.info(f"Cargando variables de entorno desde: {env_path}")
            load_dotenv(env_path)

        self._load_config()
        self._validate_config()
        self._apply_environment_variables()

    def _load_config(self) -> None:
        """
        Carga la configuración desde el archivo JSON.

        Raises:
            ConfigError: Si hay un error al cargar el archivo
        """
        try:
            if not os.path.exists(self.config_path):
                self.logger.warning(f"Archivo de configuración no encontrado: {self.config_path}")
                self.logger.info("Utilizando configuración por defecto")
                self.config = copy.deepcopy(self.DEFAULT_CONFIG)

                # Guardar la configuración por defecto
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.DEFAULT_CONFIG, f, ensure_ascii=False, indent=4)

                self.logger.info(f"Configuración por defecto guardada en: {self.config_path}")
                return

            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)

            # Combinar con la configuración por defecto para asegurar que están todos los campos
            self.config = self._merge_configs(copy.deepcopy(self.DEFAULT_CONFIG), loaded_config)
            self.logger.info(f"Configuración cargada desde: {self.config_path}")

        except json.JSONDecodeError as e:
            raise ConfigError(f"Error al analizar el archivo de configuración: {str(e)}")
        except Exception as e:
            raise ConfigError(f"Error al cargar la configuración: {str(e)}")

    def _merge_configs(self, default_config: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combina la configuración del usuario con la configuración por defecto.

        Args:
            default_config: Configuración por defecto
            user_config: Configuración del usuario

        Returns:
            Configuración combinada
        """
        for key, value in user_config.items():
            if key in default_config and isinstance(value, dict) and isinstance(default_config[key], dict):
                default_config[key] = self._merge_configs(default_config[key], value)
            else:
                default_config[key] = value
        return default_config

    def _validate_config(self) -> None:
        """
        Valida la configuración cargada.

        Raises:
            ConfigError: Si la configuración no es válida
        """
        # Validar campos obligatorios
        required_fields = [
            ("assistant", "name"),
            ("assistant", "language"),
            ("ai", "provider"),
            ("ai", "model"),
            ("system", "log_level")
        ]

        for section, field in required_fields:
            if section not in self.config or field not in self.config[section]:
                raise ConfigError(f"Campo de configuración obligatorio no encontrado: {section}.{field}")

        # Validar valores específicos
        if self.config["ai"]["temperature"] < 0 or self.config["ai"]["temperature"] > 2:
            self.logger.warning("Valor de temperatura fuera del rango recomendado (0-2)")

        # Validar que el motor de voz sea compatible con el sistema
        if self.config["voice"]["input"]["enabled"] and self.config["voice"]["input"]["engine"] not in ["system", "whisper", "vosk"]:
            self.logger.warning(f"Motor de entrada de voz no reconocido: {self.config['voice']['input']['engine']}")

        if self.config["voice"]["output"]["enabled"] and self.config["voice"]["output"]["engine"] not in ["system", "gtts", "pyttsx3", "espeak"]:
            self.logger.warning(f"Motor de salida de voz no reconocido: {self.config['voice']['output']['engine']}")

        self.logger.info("Configuración validada correctamente")

    def _apply_environment_variables(self) -> None:
        """
        Aplica las variables de entorno a la configuración.
        Las variables de entorno tienen prioridad sobre el archivo de configuración.
        """
        # Aplicar claves API desde variables de entorno para OpenAI
        if "OPENAI_API_KEY" in os.environ:
            self.config["ai"]["api_key"] = os.environ["OPENAI_API_KEY"]
            self.logger.info("API key de OpenAI aplicada desde variable de entorno")

        if "OPENAI_API_ENDPOINT" in os.environ:
            self.config["ai"]["api_endpoint"] = os.environ["OPENAI_API_ENDPOINT"]
            self.logger.info("API endpoint de OpenAI aplicado desde variable de entorno")

        # Aplicar API keys para habilidades si existen en la configuración
        if "skills" in self.config:
            # Configuración para Weather API
            if "weather" in self.config["skills"] and "WEATHER_API_KEY" in os.environ:
                self.config["skills"]["weather"]["api_key"] = os.environ["WEATHER_API_KEY"]
                self.logger.info("API key del clima aplicada desde variable de entorno")

            # Configuración para News API
            if "news" in self.config["skills"] and "NEWS_API_KEY" in os.environ:
                self.config["skills"]["news"]["api_key"] = os.environ["NEWS_API_KEY"]
                self.logger.info("API key de noticias aplicada desde variable de entorno")

            # Configuración para Home Assistant
            if "home_automation" in self.config["skills"] and "HOME_ASSISTANT_TOKEN" in os.environ:
                self.config["skills"]["home_automation"]["token"] = os.environ["HOME_ASSISTANT_TOKEN"]
                self.logger.info("Token de Home Assistant aplicado desde variable de entorno")

        # Aplicar otras configuraciones desde variables de entorno
        if "ASSISTANT_LOG_LEVEL" in os.environ:
            log_level = os.environ["ASSISTANT_LOG_LEVEL"].upper()
            if log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                self.config["system"]["log_level"] = log_level
                self.logger.info(f"Nivel de log configurado a {log_level} desde variable de entorno")

    def get_config(self) -> Dict[str, Any]:
        """
        Devuelve la configuración completa.

        Returns:
            Diccionario con la configuración
        """
        return self.config

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Devuelve una sección específica de la configuración.

        Args:
            section: Nombre de la sección

        Returns:
            Diccionario con la sección de configuración

        Raises:
            ConfigError: Si la sección no existe
        """
        if section not in self.config:
            raise ConfigError(f"Sección de configuración no encontrada: {section}")
        return self.config[section]

    def get_value(self, section: str, key: str, default: Any = None) -> Any:
        """
        Devuelve un valor específico de la configuración.

        Args:
            section: Nombre de la sección
            key: Nombre de la clave
            default: Valor por defecto si no se encuentra

        Returns:
            Valor de configuración
        """
        if section in self.config and key in self.config[section]:
            return self.config[section][key]
        return default

    def update_config(self, section: str, key: str, value: Any) -> None:
        """
        Actualiza un valor en la configuración y guarda el archivo.

        Args:
            section: Nombre de la sección
            key: Nombre de la clave
            value: Nuevo valor

        Raises:
            ConfigError: Si hay un error al guardar la configuración
        """
        try:
            if section not in self.config:
                self.config[section] = {}

            self.config[section][key] = value

            # Guardar la configuración actualizada
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)

            self.logger.info(f"Configuración actualizada: {section}.{key}")

        except Exception as e:
            raise ConfigError(f"Error al actualizar la configuración: {str(e)}")

    def save_config(self) -> None:
        """
        Guarda la configuración actual en el archivo.

        Raises:
            ConfigError: Si hay un error al guardar la configuración
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)

            self.logger.info(f"Configuración guardada en: {self.config_path}")

        except Exception as e:
            raise ConfigError(f"Error al guardar la configuración: {str(e)}")