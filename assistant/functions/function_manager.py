#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gestor de funciones para el asistente
------------------------------------
Módulo principal que gestiona todas las funciones que el asistente puede llamar.
Proporciona una interfaz única para registrar, ejecutar y manejar funciones.
"""

import os
import json
import logging
from typing import Dict, Any, List, Callable, Optional, Union, Tuple

from assistant.functions.function_definitions import get_all_function_definitions, get_function_definition
from assistant.functions.weather import WeatherFunction
from assistant.functions.google_search import GoogleSearchFunction

class FunctionManager:
    """
    Gestor centralizado de funciones para el asistente.
    Maneja el registro, ejecución y seguimiento de funciones.
    """

    def __init__(self):
        """
        Inicializa el gestor de funciones y registra todas las funciones disponibles.
        """
        self.logger = logging.getLogger("assistant.functions.manager")

        # Diccionario para mapear nombres de funciones a sus implementaciones
        self.function_handlers: Dict[str, Callable] = {}

        # Cargar todas las funciones disponibles
        self._register_all_functions()

    def _register_all_functions(self) -> None:
        """
        Registra todas las funciones disponibles para el asistente.
        """
        self.logger.info("Registrando funciones disponibles")

        try:
            # Registrar función de clima
            weather_function = WeatherFunction()
            self.register_function("get_weather", weather_function.get_weather)

            # Registrar función de búsqueda en Google
            google_search_function = GoogleSearchFunction()
            self.register_function("search_google", google_search_function.search_google)

            # Aquí se pueden registrar más funciones en el futuro

            self.logger.info(f"Registradas {len(self.function_handlers)} funciones correctamente")
        except Exception as e:
            self.logger.error(f"Error al registrar funciones: {str(e)}", exc_info=True)

    def register_function(self, function_name: str, handler: Callable) -> None:
        """
        Registra una nueva función con su handler.

        Args:
            function_name: Nombre de la función
            handler: Función Python que implementa la funcionalidad
        """
        if not callable(handler):
            raise ValueError(f"El handler para {function_name} debe ser una función llamable")

        self.function_handlers[function_name] = handler
        self.logger.debug(f"Función registrada: {function_name}")

    def execute_function(self, function_name: str, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta una función registrada.

        Args:
            function_name: Nombre de la función a ejecutar
            **kwargs: Argumentos para pasar a la función

        Returns:
            Resultado de la ejecución de la función

        Raises:
            ValueError: Si la función no está registrada
        """
        if function_name not in self.function_handlers:
            error_msg = f"Función no registrada: {function_name}"
            self.logger.error(error_msg)
            return {"error": error_msg}

        try:
            self.logger.info(f"Ejecutando función: {function_name} con argumentos: {kwargs}")
            handler = self.function_handlers[function_name]
            result = handler(**kwargs)
            return result
        except Exception as e:
            error_msg = f"Error al ejecutar función {function_name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"error": error_msg, "function": function_name}

    def get_all_functions(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de todas las definiciones de funciones disponibles.

        Returns:
            Lista de definiciones de funciones en formato para la API de OpenAI
        """
        return get_all_function_definitions()

    def handle_function_call(self, function_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja una llamada a función desde la API de OpenAI.

        Args:
            function_call: Información de la llamada a función de la API

        Returns:
            Resultado de la ejecución de la función
        """
        try:
            # Extraer información de la llamada
            function_name = function_call.get("name", "")
            arguments = function_call.get("arguments", "{}")

            # Convertir argumentos de string JSON a diccionario
            if isinstance(arguments, str):
                try:
                    args_dict = json.loads(arguments)
                except json.JSONDecodeError:
                    args_dict = {}
            else:
                args_dict = arguments

            # Ejecutar la función
            return self.execute_function(function_name, **args_dict)

        except Exception as e:
            error_msg = f"Error al manejar llamada a función: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"error": error_msg}

    def format_function_results_for_api(self,
                                      tool_call_id: str,
                                      result: Dict[str, Any]) -> Dict[str, str]:
        """
        Formatea el resultado de una función para enviar a la API.

        Args:
            tool_call_id: ID de la llamada a herramienta
            result: Resultado de la ejecución de la función

        Returns:
            Mensaje formateado para la API
        """
        if "error" in result:
            content = f"Error: {result['error']}"
        else:
            # Convertir el resultado a string JSON
            content = json.dumps(result, ensure_ascii=False)

        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content
        }
