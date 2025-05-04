#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo de función para obtener el clima
---------------------------------------
Implementa una función para obtener datos del clima que puede ser llamada automáticamente
por el asistente cuando detecta que el usuario está preguntando sobre el clima.
"""

import logging
import requests
import json
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta

class WeatherFunction:
    """
    Implementa funciones relacionadas con el clima para ser utilizadas
    por el sistema de llamada a funciones.
    """

    def __init__(self, config: Dict[str, Any], api_key: Optional[str] = None):
        """
        Inicializa la función de clima.

        Args:
            config: Configuración para el servicio de clima
            api_key: API key para el servicio (opcional, puede estar en config)
        """
        self.logger = logging.getLogger("assistant.functions.weather")
        self.config = config
        self.api_key = api_key or config.get("api_key")
        self.default_location = config.get("default_location", "Madrid, España")
        self.units = config.get("units", "metric")
        self.lang = config.get("lang", "es")

    def get_weather_function_definition(self) -> Dict[str, Any]:
        """
        Obtiene la definición de la función para la API de OpenAI.

        Returns:
            Definición de la función en formato compatible con OpenAI
        """
        return {
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

    def get_weather(self, location: str, units: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene la información del clima para una ubicación.

        Args:
            location: La ubicación para consultar el clima
            units: Sistema de unidades (metric o imperial)

        Returns:
            Información del clima
        """
        units = units or self.units
        location = location or self.default_location

        self.logger.info(f"Obteniendo clima para {location} en unidades {units}")

        try:
            # Para este ejemplo, simulamos una respuesta
            # En un caso real, aquí haríamos una llamada a la API de clima
            # Ejemplo: api.openweathermap.org/data/2.5/weather?q={location}&appid={API key}

            # Simulación de respuesta
            temp = 22 if units == "metric" else 72
            condition = "despejado"
            humidity = 65
            wind_speed = 12 if units == "metric" else 7.5
            wind_unit = "km/h" if units == "metric" else "mph"
            temp_unit = "°C" if units == "metric" else "°F"

            # Formatear resultado
            timestamp = datetime.now().strftime("%H:%M:%S")
            result = {
                "location": location,
                "current_conditions": {
                    "temperature": f"{temp}{temp_unit}",
                    "condition": condition,
                    "humidity": f"{humidity}%",
                    "wind": f"{wind_speed} {wind_unit}",
                    "timestamp": timestamp
                },
                "forecast": "No hay pronóstico de lluvia para las próximas horas."
            }

            self.logger.debug(f"Datos de clima generados: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Error al obtener el clima: {str(e)}", exc_info=True)
            return {
                "error": f"Error al obtener datos del clima: {str(e)}",
                "location": location
            }
