#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo AIProcessor
----------------
Gestiona la comunicación con modelos de IA para procesar el lenguaje natural.
Implementa la integración con OpenAI (ChatGPT) y otros modelos de IA.
"""

import os
import json
import time
import logging
import threading
import queue
import re
from typing import Dict, Any, List, Callable, Optional, Union, Tuple
import requests
from requests.exceptions import RequestException, Timeout
import openai
from openai import OpenAI
import tiktoken

from assistant.utils.logger import LoggingContext
from assistant.utils.event_bus import EventBus
from assistant.utils.api_manager import ApiManager, ApiManagerError
from assistant.modules.function_calling import FunctionCallingManager, FunctionRegistry

class AIProcessorError(Exception):
    """Excepción específica para errores del procesador de IA."""
    pass

class AIProcessor:
    """
    Procesador de IA para interactuar con modelos de lenguaje natural.
    Proporciona una interfaz unificada para diferentes proveedores de IA.
    """

    def __init__(self, config: Dict[str, Any], event_bus: EventBus):
        """
        Inicializa el procesador de IA.

        Args:
            config: Configuración del procesador de IA
            event_bus: Bus de eventos para comunicación entre componentes
        """
        self.logger = logging.getLogger("assistant.ai")
        self.config = config
        self.event_bus = event_bus
        self.client = None
        self.tokenizer = None

        # Estado interno
        self.processing = False
        self.response_queue = queue.Queue()
        self.streaming_thread = None

        # Inicializar el gestor de API
        self.api_manager = ApiManager({"ai": config})

        # Inicializar el registro de funciones y el gestor de llamadas a funciones
        self.function_registry = FunctionRegistry()
        self.function_calling_manager = FunctionCallingManager(config, event_bus, self.function_registry)

        # Inicializar el cliente según el proveedor
        self._init_client()

        self.logger.info(f"Procesador de IA inicializado con proveedor: {self.config['provider']}")

    def _init_client(self) -> None:
        """
        Inicializa el cliente de IA según el proveedor configurado.

        Raises:
            AIProcessorError: Si hay un error al inicializar el cliente
        """
        provider = self.config["provider"].lower()

        try:
            # Configurar el cliente según el proveedor
            if provider == "openai":
                # Obtener credenciales y configuración
                try:
                    api_key = self.api_manager.get_api_key("openai")
                    api_endpoint = self.api_manager.get_api_endpoint("openai")
                except ApiManagerError as e:
                    raise AIProcessorError(str(e))

                # Crear cliente de OpenAI
                self.client = OpenAI(
                    api_key=api_key,
                    base_url=api_endpoint
                )

                # Inicializar el tokenizador para contar tokens
                model = self.config["model"]
                try:
                    self.tokenizer = tiktoken.encoding_for_model(model)
                except:
                    self.tokenizer = tiktoken.get_encoding("cl100k_base")  # Codificación por defecto

                self.logger.debug(f"Cliente OpenAI inicializado con modelo: {model}")

            elif provider == "azure_openai":
                # Obtener credenciales y configuración
                try:
                    api_key = self.api_manager.get_api_key("azure_openai")
                    api_endpoint = self.api_manager.get_api_endpoint("azure_openai")
                except ApiManagerError as e:
                    raise AIProcessorError(str(e))

                # Crear cliente para Azure OpenAI
                self.client = OpenAI(
                    api_key=api_key,
                    base_url=api_endpoint
                )

                # Inicializar el tokenizador para contar tokens
                model = self.config["model"]
                try:
                    self.tokenizer = tiktoken.encoding_for_model(model)
                except:
                    self.tokenizer = tiktoken.get_encoding("cl100k_base")

            elif provider == "local":
                # Implementar integración con modelos locales
                # (ej. llama.cpp, huggingface)
                self.logger.warning("Soporte para modelos locales no implementado completamente")
                pass

            else:
                raise AIProcessorError(f"Proveedor de IA no soportado: {provider}")

        except Exception as e:
            self.logger.error(f"Error al inicializar el cliente de IA: {str(e)}", exc_info=True)
            raise AIProcessorError(f"Error al inicializar cliente: {str(e)}")

    def _count_tokens(self, text: str) -> int:
        """
        Cuenta el número de tokens en un texto.

        Args:
            text: Texto a analizar

        Returns:
            Número de tokens
        """
        if self.tokenizer:
            return len(self.tokenizer.encode(text))

        # Estimación aproximada si no hay tokenizador
        return len(text.split()) * 1.3

    def _prepare_messages(self,
                        user_input: str,
                        conversation_history: List[Dict[str, str]],
                        system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Prepara los mensajes para enviar al modelo.

        Args:
            user_input: Texto del usuario
            conversation_history: Historial de conversación
            system_prompt: Prompt de sistema personalizado (opcional)

        Returns:
            Lista de mensajes formateados para la API
        """
        # Usar el system prompt de la configuración si no se proporciona uno específico
        if system_prompt is None:
            system_prompt = self.config.get("system_prompt", "")

        # Crear el mensaje del sistema
        messages = [{"role": "system", "content": system_prompt}]

        # Añadir la historia de conversación
        if conversation_history:
            # Limitar el tamaño de la historia según la configuración
            max_turns = self.config.get("context_window_size", 10)
            recent_history = conversation_history[-max_turns*2:] if len(conversation_history) > max_turns*2 else conversation_history
            messages.extend(recent_history)

        # Asegurarse de que el último mensaje sea el del usuario
        if not conversation_history or conversation_history[-1]["role"] != "user" or conversation_history[-1]["content"] != user_input:
            messages.append({"role": "user", "content": user_input})

        return messages

    def register_function(self, function_def: Dict[str, Any], handler: Callable) -> None:
        """
        Registra una función que puede ser llamada por el asistente.

        Args:
            function_def: Definición de la función en formato compatible con OpenAI
            handler: Función Python que implementa la funcionalidad
        """
        self.function_registry.register_function(function_def, handler)

    def process_input(self,
                     user_input: str,
                     conversation_history: Optional[List[Dict[str, str]]] = None,
                     system_prompt: Optional[str] = None) -> None:
        """
        Procesa el texto del usuario y genera una respuesta.

        Args:
            user_input: Texto del usuario
            conversation_history: Historial de conversación
            system_prompt: Prompt de sistema personalizado (opcional)
        """
        if not user_input.strip():
            return

        if conversation_history is None:
            conversation_history = []

        try:
            # Preparar los mensajes
            messages = self._prepare_messages(user_input, conversation_history, system_prompt)

            # Elegir modo de procesamiento (streaming o completo)
            if self.config.get("stream_response", True):
                # Iniciar hilo para streaming
                self.streaming_thread = threading.Thread(
                    target=self._process_streaming,
                    args=(messages,),
                    daemon=True
                )
                self.streaming_thread.start()
            else:
                # Procesar la respuesta completa
                self._process_complete(messages)

        except Exception as e:
            error_msg = f"Error al procesar entrada: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            # Publicar evento de error
            self.event_bus.publish("error", {
                "source": "ai_processor",
                "message": error_msg,
                "critical": False
            })

    def _process_complete(self, messages: List[Dict[str, str]]) -> None:
        """
        Procesa la entrada del usuario y genera una respuesta completa.

        Args:
            messages: Lista de mensajes para la API
        """
        provider = self.config["provider"].lower()
        model = self.config["model"]

        with LoggingContext(self.logger, "process_complete") as log_ctx:
            try:
                self.processing = True

                # Procesar según el proveedor
                if provider == "openai" or provider == "azure_openai":
                    # Obtener las definiciones de funciones
                    tools = self.function_calling_manager.prepare_functions_for_api()

                    # Configurar parámetros
                    params = {
                        "model": model,
                        "messages": messages,
                        "max_tokens": self.config.get("max_tokens", 2048),
                        "temperature": self.config.get("temperature", 0.7),
                        "top_p": self.config.get("top_p", 1.0),
                        "frequency_penalty": self.config.get("frequency_penalty", 0.0),
                        "presence_penalty": self.config.get("presence_penalty", 0.0)
                    }

                    # Añadir herramientas/funciones si están disponibles
                    if tools:
                        params["tools"] = tools

                    # Realizar la llamada a la API
                    log_ctx.log(f"Enviando solicitud a {provider} con {len(messages)} mensajes y {len(tools) if tools else 0} herramientas")
                    response = self.client.chat.completions.create(**params)
                    self.logger.warning(f"Respuesta: {response}")

                    # Verificar si hay llamadas a funciones
                    if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                        tool_calls = [
                            {
                                "id": tc.id,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in response.choices[0].message.tool_calls
                        ]

                        # Ejecutar las funciones llamadas
                        log_ctx.log(f"Recibidas {len(tool_calls)} llamadas a funciones")

                        # Crear nuevo mensaje con la respuesta del modelo
                        model_message = {
                            "role": "assistant",
                            "content": response.choices[0].message.content if response.choices[0].message.content else None,
                            "tool_calls": tool_calls
                        }

                        # Añadir el mensaje del modelo al historial
                        complete_messages = messages + [model_message]

                        # Procesar llamadas a funciones
                        function_results = self.function_calling_manager.handle_tool_calls(tool_calls)

                        # Formatear resultados para API
                        function_messages = self.function_calling_manager.format_function_results_for_api(
                            tool_calls, function_results
                        )

                        # Añadir mensajes de resultados de funciones al historial
                        complete_messages.extend(function_messages)

                        # Segunda llamada a la API con los resultados de las funciones
                        second_params = {
                            "model": model,
                            "messages": complete_messages,
                            "max_tokens": self.config.get("max_tokens", 2048),
                            "temperature": self.config.get("temperature", 0.7),
                            "top_p": self.config.get("top_p", 1.0),
                            "frequency_penalty": self.config.get("frequency_penalty", 0.0),
                            "presence_penalty": self.config.get("presence_penalty", 0.0)
                        }

                        # Si hay herramientas, incluirlas en la segunda llamada
                        if tools:
                            second_params["tools"] = tools

                        log_ctx.log("Enviando segunda solicitud con resultados de funciones")
                        second_response = self.client.chat.completions.create(**second_params)
                        self.logger.warning(f"Respuesta1: {second_response}")

                        # Extractar la respuesta final
                        ai_response = second_response.choices[0].message.content
                        self.logger.warning(f"Respuesta2: {ai_response}")

                        # Publicar un evento con la información de las llamadas a funciones
                        self.event_bus.publish("functions_called", {
                            "tool_calls": tool_calls,
                            "results": function_results
                        })
                    else:
                        # No hay llamadas a funciones, solo extraer la respuesta directa
                        ai_response = response.choices[0].message.content

                    log_ctx.log(f"Respuesta recibida: {len(ai_response)} caracteres")

                    # Publicar la respuesta
                    self.event_bus.publish("ai_response_received", {
                        "response": ai_response,
                        "model": model,
                        "prompt_tokens": response.usage.prompt_tokens if hasattr(response, 'usage') else None,
                        "completion_tokens": response.usage.completion_tokens if hasattr(response, 'usage') else None,
                        "total_tokens": response.usage.total_tokens if hasattr(response, 'usage') else None
                    })

                elif provider == "local":
                    # Implementación para modelos locales
                    # TODO: Implementar integración con modelos locales
                    pass

                else:
                    raise AIProcessorError(f"Proveedor no soportado: {provider}")

            except Exception as e:
                error_msg = f"Error en la API de IA: {str(e)}"
                self.logger.error(error_msg, exc_info=True)

                # Publicar evento de error
                self.event_bus.publish("error", {
                    "source": "ai_processor",
                    "message": error_msg,
                    "critical": False
                })

                # Publicar respuesta de error genérica
                self.event_bus.publish("ai_response_received", {
                    "response": "Lo siento, ha ocurrido un error al procesar tu consulta. Por favor, inténtalo de nuevo.",
                    "error": str(e)
                })

            finally:
                self.processing = False

    def _process_streaming(self, messages: List[Dict[str, str]]) -> None:
        """
        Procesa la entrada del usuario y genera una respuesta en streaming.

        Args:
            messages: Lista de mensajes para la API
        """
        provider = self.config["provider"].lower()
        model = self.config["model"]

        with LoggingContext(self.logger, "process_streaming") as log_ctx:
            try:
                self.processing = True

                # Limpiar la cola de respuestas
                with self.response_queue.mutex:
                    self.response_queue.queue.clear()

                # Procesar según el proveedor
                if provider == "openai" or provider == "azure_openai":
                    # Obtener las definiciones de funciones
                    tools = self.function_calling_manager.prepare_functions_for_api()

                    # Configurar parámetros
                    params = {
                        "model": model,
                        "messages": messages,
                        "max_tokens": self.config.get("max_tokens", 2048),
                        "temperature": self.config.get("temperature", 0.7),
                        "top_p": self.config.get("top_p", 1.0),
                        "frequency_penalty": self.config.get("frequency_penalty", 0.0),
                        "presence_penalty": self.config.get("presence_penalty", 0.0),
                        "stream": True
                    }

                    # Añadir herramientas/funciones si están disponibles
                    if tools:
                        params["tools"] = tools

                    # Realizar la llamada a la API con streaming
                    log_ctx.log(f"Iniciando streaming con {len(messages)} mensajes y {len(tools) if tools else 0} herramientas")
                    response_stream = self.client.chat.completions.create(**params)

                    # Inicializar variables para acumular la respuesta
                    collected_chunks = []
                    collected_messages = []
                    collected_tool_calls = []
                    has_tool_calls = False

                    # Procesar cada parte del streaming
                    for chunk in response_stream:
                        collected_chunks.append(chunk)

                        # Verificar llamadas a funciones
                        if (hasattr(chunk.choices[0], 'delta') and
                            hasattr(chunk.choices[0].delta, 'tool_calls') and
                            chunk.choices[0].delta.tool_calls):
                            has_tool_calls = True
                            # El streaming con tool_calls es más complejo, vamos a recopilar los datos
                            for tool_call_delta in chunk.choices[0].delta.tool_calls:
                                collected_tool_calls.append(tool_call_delta)

                        # Extraer el contenido del chunk
                        content = ""
                        if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content'):
                            content = chunk.choices[0].delta.content
                            if content:
                                collected_messages.append(content)
                                # Agregar a la cola para procesamiento externo
                                self.response_queue.put(content)

                    # Si tenemos llamadas a funciones, terminamos el streaming y procesamos las llamadas
                    if has_tool_calls:
                        log_ctx.log("Detectadas llamadas a funciones durante streaming, cambiando a modo completo")

                        # Reconstruct tool calls from streaming chunks (this is complex)
                        # Para simplificar, hacemos una nueva llamada no streaming para obtener las tool calls completas
                        non_stream_params = dict(params)
                        non_stream_params["stream"] = False
                        complete_response = self.client.chat.completions.create(**non_stream_params)

                        # Extraer las llamadas a funciones
                        if hasattr(complete_response.choices[0].message, 'tool_calls'):
                            tool_calls = [
                                {
                                    "id": tc.id,
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments
                                    }
                                }
                                for tc in complete_response.choices[0].message.tool_calls
                            ]

                            # Crear nuevo mensaje con la respuesta del modelo
                            model_message = {
                                "role": "assistant",
                                "content": complete_response.choices[0].message.content if complete_response.choices[0].message.content else None,
                                "tool_calls": tool_calls
                            }

                            # Añadir el mensaje del modelo al historial
                            complete_messages = messages + [model_message]

                            # Procesar llamadas a funciones
                            function_results = self.function_calling_manager.handle_tool_calls(tool_calls)

                            # Formatear resultados para API
                            function_messages = self.function_calling_manager.format_function_results_for_api(
                                tool_calls, function_results
                            )

                            # Añadir mensajes de resultados de funciones al historial
                            complete_messages.extend(function_messages)

                            # Segunda llamada a la API con los resultados de las funciones
                            second_params = {
                                "model": model,
                                "messages": complete_messages,
                                "max_tokens": self.config.get("max_tokens", 2048),
                                "temperature": self.config.get("temperature", 0.7),
                                "top_p": self.config.get("top_p", 1.0),
                                "frequency_penalty": self.config.get("frequency_penalty", 0.0),
                                "presence_penalty": self.config.get("presence_penalty", 0.0)
                            }

                            # Si hay herramientas, incluirlas en la segunda llamada
                            if tools:
                                second_params["tools"] = tools

                            log_ctx.log("Enviando segunda solicitud con resultados de funciones")
                            second_response = self.client.chat.completions.create(**second_params)

                            # Extraer la respuesta final
                            full_response = second_response.choices[0].message.content

                            # Señalizar el final del streaming con la respuesta completa
                            with self.response_queue.mutex:
                                self.response_queue.queue.clear()
                            self.response_queue.put(full_response)
                            self.response_queue.put(None)  # Señal de fin

                            # Publicar un evento con la información de las llamadas a funciones
                            self.event_bus.publish("functions_called", {
                                "tool_calls": tool_calls,
                                "results": function_results
                            })

                            # Publicar la respuesta completa
                            self.event_bus.publish("ai_response_received", {
                                "response": full_response,
                                "model": model,
                                "streaming": True
                            })

                            return  # Terminamos aquí para evitar la publicación duplicada

                    # Si no hay llamadas a funciones, procesamos normalmente
                    # Combinar todos los fragmentos en la respuesta final
                    full_response = "".join(collected_messages)
                    log_ctx.log(f"Streaming completo: {len(full_response)} caracteres")

                    # Señalizar el final del streaming
                    self.response_queue.put(None)

                    # Publicar la respuesta completa
                    self.event_bus.publish("ai_response_received", {
                        "response": full_response,
                        "model": model,
                        "streaming": True
                    })

                elif provider == "local":
                    # Implementación para modelos locales
                    # TODO: Implementar integración con modelos locales
                    pass

                else:
                    raise AIProcessorError(f"Proveedor no soportado: {provider}")

            except Exception as e:
                error_msg = f"Error en streaming de IA: {str(e)}"
                self.logger.error(error_msg, exc_info=True)

                # Publicar evento de error
                self.event_bus.publish("error", {
                    "source": "ai_processor",
                    "message": error_msg,
                    "critical": False
                })

                # Publicar respuesta de error genérica
                self.event_bus.publish("ai_response_received", {
                    "response": "Lo siento, ha ocurrido un error al procesar tu consulta. Por favor, inténtalo de nuevo.",
                    "error": str(e)
                })

                # Señalizar el final del streaming
                self.response_queue.put(None)

            finally:
                self.processing = False

    def get_next_chunk(self, timeout: float = 0.1) -> Optional[str]:
        """
        Obtiene el siguiente fragmento de la respuesta en streaming.

        Args:
            timeout: Tiempo máximo de espera en segundos

        Returns:
            Fragmento de texto o None si no hay más fragmentos
        """
        try:
            return self.response_queue.get(timeout=timeout)
        except queue.Empty:
            return ""

    def is_processing(self) -> bool:
        """
        Indica si el procesador está generando una respuesta.

        Returns:
            True si está procesando, False en caso contrario
        """
        return self.processing

    def close(self) -> None:
        """Libera los recursos utilizados por el procesador."""
        self.logger.debug("Cerrando procesador de IA")
        # No es necesario cerrar el cliente de OpenAI explícitamente
