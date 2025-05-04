#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Definiciones de funciones para el asistente
------------------------------------------
Este archivo contiene las definiciones de todas las funciones que el asistente
puede llamar automáticamente, en formato compatible con la API de OpenAI.
"""

import json

# Definición de función para obtener el clima
WEATHER_FUNCTION = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Obtiene información meteorológica actual para una ubicación específica.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "La ubicación para la que se solicita el clima, por ejemplo 'Madrid, España'"
                },
                "units": {
                    "type": "string",
                    "enum": ["metric", "imperial"],
                    "description": "Sistema de unidades: metric (°C, km/h) o imperial (°F, mph)"
                }
            },
            "required": ["location"]
        }
    }
}

# Definición de función para búsqueda en Google con Serper.dev
GOOGLE_SEARCH_FUNCTION = {
    "type": "function",
    "function": {
        "name": "search_google",
        "description": "Busca información actualizada en Google sobre cualquier tema o pregunta.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Términos de búsqueda o pregunta para buscar en Google"
                },
                "language": {
                    "type": "string",
                    "enum": ["es-419", "en", "fr", "de", "it"],
                    "description": "Código de idioma para los resultados"
                },
                "country": {
                    "type": "string",
                    "enum": ["mx", "us", "es", "ar", "co", "pe", "cl"],
                    "description": "Código de país para contextualizar los resultados"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Número de resultados a devolver (1-10)"
                }
            },
            "required": ["query"]
        }
    }
}

# Definición de función para crear recordatorios
REMINDER_FUNCTION = {
    "type": "function",
    "function": {
        "name": "create_reminder",
        "description": "Crea un nuevo recordatorio para el usuario.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Título o descripción breve del recordatorio"
                },
                "time": {
                    "type": "string",
                    "description": "Hora del recordatorio en formato HH:MM o cantidad de tiempo relativo (ej. '5 minutos', '1 hora')"
                },
                "date": {
                    "type": "string",
                    "description": "Fecha del recordatorio en formato YYYY-MM-DD o día de la semana o 'hoy'/'mañana'"
                },
                "description": {
                    "type": "string",
                    "description": "Descripción detallada del recordatorio (opcional)"
                }
            },
            "required": ["title", "time"]
        }
    }
}

# Lista con todas las definiciones de funciones disponibles
AVAILABLE_FUNCTIONS = [
    WEATHER_FUNCTION,
    GOOGLE_SEARCH_FUNCTION,
    REMINDER_FUNCTION
]

def get_all_function_definitions():
    """
    Obtiene todas las definiciones de funciones disponibles.

    Returns:
        Lista de definiciones de funciones en formato para la API de OpenAI
    """
    return AVAILABLE_FUNCTIONS

def get_function_definition(function_name):
    """
    Obtiene la definición de una función específica por su nombre.

    Args:
        function_name: Nombre de la función

    Returns:
        Definición de la función o None si no existe
    """
    for function_def in AVAILABLE_FUNCTIONS:
        if function_def["function"]["name"] == function_name:
            return function_def
    return None
