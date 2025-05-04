#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo FunctionCalling
---------------------
Proporciona funcionalidad para detectar automáticamente cuándo el asistente debe llamar a una función
y gestionar las llamadas a funciones utilizando la API de OpenAI.
"""

import json
import logging
from typing import Dict, Any, List, Callable, Optional, Union

from assistant.utils.event_bus import EventBus

class FunctionRegistry:
    """
    Registro de funciones que pueden ser llamadas por el asistente.
    Mantiene un catálogo de funciones disponibles con sus definiciones.
    """

    def __init__(self):
        """
        Inicializa el registro de funciones.
        """
        self.logger = logging.getLogger("assistant.functions")
        self.functions: List[Dict[str, Any]] = []
        self.function_handlers: Dict[str, Callable] = {}

    def register_function(self,
                        function_def: Dict[str, Any],
                        handler: Callable) -> None:
        """
        Registra una nueva función en el sistema.

        Args:
            function_def: Definición de la función en formato compatible con OpenAI
            handler: Función Python que implementa la funcionalidad
        """
        if not isinstance(function_def, dict) or 'function' not in function_def:
            raise ValueError("La definición de función debe ser un diccionario con una clave 'function'")

        if not callable(handler):
            raise ValueError("El handler debe ser una función llamable")

        function_name = function_def.get("function", {}).get("name")
        if not function_name:
            raise ValueError("La definición de función debe incluir un nombre")

        # Añadir al registro
        self.functions.append(function_def)
        self.function_handlers[function_name] = handler

        self.logger.info(f"Función registrada: {function_name}")

    def get_functions_list(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de definiciones de funciones para la API.

        Returns:
            Lista de definiciones de funciones
        """
        return self.functions

    def get_function_handler(self, function_name: str) -> Optional[Callable]:
        """
        Obtiene el handler para una función específica.

        Args:
            function_name: Nombre de la función

        Returns:
            Handler de la función si existe, None en caso contrario
        """
        return self.function_handlers.get(function_name)

    def clear(self) -> None:
        """
        Limpia todas las funciones registradas.
        """
        self.functions = []
        self.function_handlers = {}
        self.logger.debug("Registro de funciones limpiado")


class FunctionCallingManager:
    """
    Gestor de llamadas a funciones para el asistente.
    Determina cuándo se debe llamar a una función y gestiona la ejecución.
    """

    def __init__(self, config: Dict[str, Any], event_bus: EventBus, function_registry: FunctionRegistry = None):
        """
        Inicializa el gestor de llamadas a funciones.

        Args:
            config: Configuración del gestor
            event_bus: Bus de eventos para comunicación
            function_registry: Registro de funciones (se crea uno nuevo si no se proporciona)
        """
        self.logger = logging.getLogger("assistant.functions.manager")
        self.config = config
        self.event_bus = event_bus

        # Crear o usar el registro de funciones proporcionado
        self.function_registry = function_registry if function_registry else FunctionRegistry()

        self.logger.info("Gestor de llamadas a funciones inicializado")

    def prepare_functions_for_api(self) -> List[Dict[str, Any]]:
        """
        Prepara la lista de funciones para enviar a la API.

        Returns:
            Lista de definiciones de funciones en formato para la API
        """
        return self.function_registry.get_functions_list()

    def handle_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Maneja las llamadas a herramientas/funciones devueltas por la API.

        Args:
            tool_calls: Lista de llamadas a herramientas/funciones desde la API

        Returns:
            Diccionario con resultados de las llamadas
        """
        results = {}

        for tool_call in tool_calls:
            try:
                # Extraer información de la llamada
                if 'function' in tool_call:
                    function_name = tool_call.get('function', {}).get('name')
                    function_args_str = tool_call.get('function', {}).get('arguments', '{}')
                    function_id = tool_call.get('id')

                    # Analizar argumentos
                    function_args = json.loads(function_args_str)

                    # Obtener el handler
                    handler = self.function_registry.get_function_handler(function_name)

                    if handler and callable(handler):
                        self.logger.info(f"Ejecutando función: {function_name}")

                        # Ejecutar la función
                        result = handler(**function_args)

                        # Almacenar resultado
                        results[function_id] = {
                            "function_name": function_name,
                            "result": result
                        }

                        # Publicar evento
                        self.event_bus.publish("function_call_executed", {
                            "function_name": function_name,
                            "arguments": function_args,
                            "result": result
                        })
                    else:
                        error_msg = f"Función no encontrada: {function_name}"
                        self.logger.error(error_msg)
                        results[function_id] = {
                            "function_name": function_name,
                            "error": error_msg
                        }
                else:
                    self.logger.warning(f"Formato de llamada a herramienta no reconocido: {tool_call}")

            except json.JSONDecodeError as e:
                error_msg = f"Error al analizar argumentos JSON: {str(e)}"
                self.logger.error(error_msg)
                results[tool_call.get('id', 'unknown')] = {"error": error_msg}

            except Exception as e:
                error_msg = f"Error al ejecutar función: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                results[tool_call.get('id', 'unknown')] = {"error": error_msg}

        return results

    def format_function_results_for_api(self, tool_calls: List[Dict[str, Any]], results: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Formatea los resultados de las funciones para enviar a la API.

        Args:
            tool_calls: Lista de llamadas a herramientas/funciones desde la API
            results: Resultados de las llamadas a funciones

        Returns:
            Lista de mensajes formateados para la API
        """
        messages = []

        for tool_call in tool_calls:
            tool_call_id = tool_call.get('id')
            if tool_call_id in results:
                result = results[tool_call_id]

                if "error" in result:
                    content = f"Error: {result['error']}"
                else:
                    content = str(result.get("result", ""))

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": content
                })

        return messages
