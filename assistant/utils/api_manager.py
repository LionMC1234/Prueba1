#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo ApiManager
----------------
Gestiona las configuraciones y credenciales de las APIs utilizadas por el asistente.
"""

import os
import logging
from typing import Dict, Any, Optional

class ApiManagerError(Exception):
    """Excepción específica para errores del gestor de API."""
    pass

class ApiManager:
    """
    Gestor de APIs para el asistente.
    Proporciona acceso centralizado a las credenciales y configuraciones de API.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el gestor de API.

        Args:
            config: Configuración global del asistente
        """
        self.logger = logging.getLogger("assistant.api")
        self.config = config
        self.logger.info("ApiManager inicializado")

    def get_api_key(self, provider: str) -> str:
        """
        Obtiene la clave API para un proveedor específico.

        Args:
            provider: Nombre del proveedor (por ejemplo, "openai", "weather")

        Returns:
            Clave API del proveedor

        Raises:
            ApiManagerError: Si no se encuentra la clave API
        """
        provider = provider.lower()
        api_key = ""

        # Buscar en variables de entorno según el proveedor
        if provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY", "")
        elif provider == "azure_openai":
            api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
        elif provider == "weather":
            api_key = os.environ.get("WEATHER_API_KEY", "")
        elif provider == "news":
            api_key = os.environ.get("NEWS_API_KEY", "")
        elif provider == "home_assistant":
            api_key = os.environ.get("HOME_ASSISTANT_TOKEN", "")
        else:
            # Buscar como nombre genérico
            api_key = os.environ.get(f"{provider.upper()}_API_KEY", "")

        # Si no está en variables de entorno, buscar en la configuración
        if not api_key:
            if provider == "openai" and "ai" in self.config:
                api_key = self.config["ai"].get("api_key", "")
            elif provider == "weather" and "skills" in self.config and "weather" in self.config["skills"]:
                api_key = self.config["skills"]["weather"].get("api_key", "")
            elif provider == "news" and "skills" in self.config and "news" in self.config["skills"]:
                api_key = self.config["skills"]["news"].get("api_key", "")
            elif provider == "home_assistant" and "skills" in self.config and "home_automation" in self.config["skills"]:
                api_key = self.config["skills"]["home_automation"].get("token", "")

        # Verificar que tengamos una clave API
        if not api_key:
            error_msg = f"No se ha configurado la clave API para {provider}"
            self.logger.error(error_msg)
            raise ApiManagerError(error_msg)

        return api_key

    def get_api_endpoint(self, provider: str) -> str:
        """
        Obtiene el endpoint API para un proveedor específico.

        Args:
            provider: Nombre del proveedor (por ejemplo, "openai", "weather")

        Returns:
            Endpoint API del proveedor

        Raises:
            ApiManagerError: Si no se encuentra el endpoint API
        """
        provider = provider.lower()
        api_endpoint = ""

        # Buscar en variables de entorno según el proveedor
        if provider == "openai":
            api_endpoint = os.environ.get("OPENAI_BASE_URL", "")
        elif provider == "azure_openai":
            api_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        elif provider == "weather":
            api_endpoint = os.environ.get("WEATHER_API_ENDPOINT", "")
        elif provider == "news":
            api_endpoint = os.environ.get("NEWS_API_ENDPOINT", "")
        elif provider == "home_assistant":
            api_endpoint = os.environ.get("HOME_ASSISTANT_HOST", "")
        else:
            # Buscar como nombre genérico
            api_endpoint = os.environ.get(f"{provider.upper()}_API_ENDPOINT", "")

        # Si no está en variables de entorno, buscar en la configuración
        if not api_endpoint:
            if provider == "openai" and "ai" in self.config:
                api_endpoint = self.config["ai"].get("api_endpoint", "")
                # Valor predeterminado para OpenAI
                if not api_endpoint:
                    api_endpoint = "https://api.openai.com/v1"
            elif provider == "weather" and "skills" in self.config and "weather" in self.config["skills"]:
                api_endpoint = self.config["skills"]["weather"].get("api_endpoint", "")
            elif provider == "news" and "skills" in self.config and "news" in self.config["skills"]:
                api_endpoint = self.config["skills"]["news"].get("api_endpoint", "")
            elif provider == "home_assistant" and "skills" in self.config and "home_automation" in self.config["skills"]:
                api_endpoint = self.config["skills"]["home_automation"].get("host", "")

        # Verificar que tengamos un endpoint API (excepto para algunos servicios)
        if not api_endpoint and provider in ["openai", "azure_openai", "home_assistant"]:
            error_msg = f"No se ha configurado el endpoint API para {provider}"
            self.logger.error(error_msg)
            raise ApiManagerError(error_msg)

        return api_endpoint