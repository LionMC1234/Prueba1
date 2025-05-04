#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo de función para obtener el clima
---------------------------------------
Implementa una función para obtener datos del clima en tiempo real utilizando
la API de OpenWeatherMap cuando el asistente detecta consultas sobre el clima.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta

class WeatherFunction:
    """
    Implementa funciones relacionadas con el clima utilizando la API de OpenWeatherMap
    para obtener datos meteorológicos en tiempo real.
    """

    def __init__(self, api_key: Optional[str] = None, default_location: str = "Madrid, España"):
        """
        Inicializa la función de clima.

        Args:
            api_key: API key para OpenWeatherMap (opcional, puede tomarse de las variables de entorno)
            default_location: Ubicación por defecto para consultas sin ubicación específica
        """
        self.logger = logging.getLogger("assistant.functions.weather")

        # Obtener API key desde parámetro o variable de entorno
        self.api_key = api_key or os.environ.get("OPENWEATHERMAP_API_KEY", "")
        self.default_location = default_location

        if not self.api_key:
            self.logger.warning("API key para OpenWeatherMap no configurada. Se utilizarán datos simulados.")

    def get_weather(self, location: str, units: str = "metric") -> Dict[str, Any]:
        """
        Obtiene la información del clima en tiempo real para una ubicación.

        Args:
            location: La ubicación para consultar el clima
            units: Sistema de unidades (metric o imperial)

        Returns:
            Información del clima de OpenWeatherMap
        """
        location = location or self.default_location
        units = units.lower() if units else "metric"

        self.logger.info(f"Obteniendo clima para {location} en unidades {units}")

        try:
            # Si tenemos API key, obtener datos reales de OpenWeatherMap
            if self.api_key:
                return self._get_real_weather_data(location, units)
            else:
                # En caso contrario, usar datos simulados como fallback
                self.logger.warning("Usando datos simulados porque no se proporcionó API key para OpenWeatherMap")
                return self._get_simulated_weather_data(location, units)

        except Exception as e:
            error_msg = f"Error al obtener el clima: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "location": location
            }

    def _get_real_weather_data(self, location: str, units: str) -> Dict[str, Any]:
        """
        Obtiene datos reales del clima usando la API de OpenWeatherMap.

        Args:
            location: Ubicación para la consulta
            units: Sistema de unidades (metric o imperial)

        Returns:
            Datos del clima
        """
        self.logger.debug(f"Realizando consulta a OpenWeatherMap para: {location}")

        # Obtener datos actuales
        current_weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={self.api_key}&units={units}&lang=es"
        current_response = requests.get(current_weather_url, timeout=10)

        # Verificar respuesta
        if current_response.status_code != 200:
            error_details = current_response.json() if current_response.text else {"message": "Sin detalles"}
            error_msg = f"Error en API de OpenWeatherMap ({current_response.status_code}): {error_details.get('message', 'Error desconocido')}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

        current_data = current_response.json()

        # Extraer coordenadas para el pronóstico
        lat = current_data["coord"]["lat"]
        lon = current_data["coord"]["lon"]

        # Obtener pronóstico
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={self.api_key}&units={units}&lang=es"
        forecast_response = requests.get(forecast_url, timeout=10)

        # Verificar respuesta
        if forecast_response.status_code != 200:
            error_details = forecast_response.json() if forecast_response.text else {"message": "Sin detalles"}
            error_msg = f"Error en API de OpenWeatherMap - Pronóstico ({forecast_response.status_code}): {error_details.get('message', 'Error desconocido')}"
            self.logger.error(error_msg)
            # Continuamos con los datos actuales aunque falle el pronóstico
            forecast_data = None
        else:
            forecast_data = forecast_response.json()

        # Procesar datos actuales
        temp_unit = "°C" if units == "metric" else "°F"
        wind_unit = "km/h" if units == "metric" else "mph"

        # Formatear respuesta
        processed_data = {
            "location": current_data["name"] + (f", {current_data['sys']['country']}" if "country" in current_data["sys"] else ""),
            "current_conditions": {
                "temperature": f"{current_data['main']['temp']:.1f}{temp_unit}",
                "condition": current_data["weather"][0]["description"].capitalize(),
                "humidity": f"{current_data['main']['humidity']}%",
                "wind": f"{current_data['wind']['speed']} {wind_unit}",
                "pressure": f"{current_data['main']['pressure']} hPa",
                "feels_like": f"{current_data['main']['feels_like']:.1f}{temp_unit}",
                "timestamp": datetime.fromtimestamp(current_data["dt"]).strftime("%Y-%m-%d %H:%M:%S")
            },
            "sunrise": datetime.fromtimestamp(current_data["sys"]["sunrise"]).strftime("%H:%M"),
            "sunset": datetime.fromtimestamp(current_data["sys"]["sunset"]).strftime("%H:%M"),
            "forecast": [],
            "source": "OpenWeatherMap"
        }

        # Procesar pronóstico si disponible
        if forecast_data:
            # Agrupar por día y obtener datos de cada día
            forecast_days = {}

            for item in forecast_data["list"]:
                dt = datetime.fromtimestamp(item["dt"])
                day_key = dt.strftime("%Y-%m-%d")

                if day_key not in forecast_days:
                    forecast_days[day_key] = {
                        "day": self._get_day_name(dt),
                        "temperatures": [],
                        "conditions": [],
                        "humidity": [],
                        "wind": []
                    }

                forecast_days[day_key]["temperatures"].append(item["main"]["temp"])
                forecast_days[day_key]["conditions"].append(item["weather"][0]["description"])
                forecast_days[day_key]["humidity"].append(item["main"]["humidity"])
                forecast_days[day_key]["wind"].append(item["wind"]["speed"])

            # Procesar los datos agrupados
            forecast_list = []
            for day_key, data in sorted(forecast_days.items()):
                # Obtener valores medios o más frecuentes
                avg_temp = sum(data["temperatures"]) / len(data["temperatures"])
                # Encontrar la condición más frecuente
                conditions = data["conditions"]
                most_common_condition = max(set(conditions), key=conditions.count)
                avg_humidity = sum(data["humidity"]) / len(data["humidity"])
                avg_wind = sum(data["wind"]) / len(data["wind"])

                forecast_list.append({
                    "day": data["day"],
                    "temperature": f"{avg_temp:.1f}{temp_unit}",
                    "condition": most_common_condition.capitalize(),
                    "humidity": f"{avg_humidity:.0f}%",
                    "wind": f"{avg_wind:.1f} {wind_unit}"
                })

            # Limitar a próximos 3 días
            processed_data["forecast"] = forecast_list[:3]

        self.logger.debug(f"Datos de clima obtenidos de OpenWeatherMap para {location}")
        return processed_data

    def _get_day_name(self, dt: datetime) -> str:
        """
        Obtiene el nombre del día en español.

        Args:
            dt: Objeto datetime

        Returns:
            Nombre del día en español
        """
        days = {
            0: "Hoy" if dt.date() == datetime.now().date() else "Lunes",
            1: "Hoy" if dt.date() == datetime.now().date() else "Martes",
            2: "Hoy" if dt.date() == datetime.now().date() else "Miércoles",
            3: "Hoy" if dt.date() == datetime.now().date() else "Jueves",
            4: "Hoy" if dt.date() == datetime.now().date() else "Viernes",
            5: "Hoy" if dt.date() == datetime.now().date() else "Sábado",
            6: "Hoy" if dt.date() == datetime.now().date() else "Domingo"
        }

        tomorrow = (datetime.now() + timedelta(days=1)).date()
        if dt.date() == tomorrow:
            return "Mañana"

        return days[dt.weekday()]

    def _get_simulated_weather_data(self, location: str, units: str) -> Dict[str, Any]:
        """
        Genera datos simulados del clima para demostración (fallback).

        Args:
            location: Ubicación para la consulta
            units: Sistema de unidades

        Returns:
            Datos simulados del clima
        """
        # Esta función es igual que la anterior, para mantener compatibilidad
        # cuando no se dispone de API key

        # Simulación básica basada en la ubicación
        location_lower = location.lower()

        # Determinar temperatura base según la ubicación mencionada
        if any(city in location_lower for city in ["madrid", "españa", "spain"]):
            base_temp = 22
        elif any(city in location_lower for city in ["barcelona", "cataluña"]):
            base_temp = 24
        elif any(city in location_lower for city in ["nueva york", "new york"]):
            base_temp = 18
        elif any(city in location_lower for city in ["tokio", "tokyo", "japón", "japan"]):
            base_temp = 20
        elif any(city in location_lower for city in ["sydney", "australia"]):
            base_temp = 26
        elif any(city in location_lower for city in ["moscú", "moscow", "rusia"]):
            base_temp = 10
        elif any(city in location_lower for city in ["dubai", "emiratos"]):
            base_temp = 35
        elif any(city in location_lower for city in ["oslo", "noruega"]):
            base_temp = 8
        elif any(city in location_lower for city in ["río", "rio", "brasil", "brazil"]):
            base_temp = 30
        else:
            # Temperatura por defecto para otras ciudades
            base_temp = 23

        # Ajustar según el sistema de unidades
        if units == "imperial":
            temp = round(base_temp * 9/5 + 32)  # Convertir a Fahrenheit
            temp_unit = "°F"
            wind_speed = round(base_temp / 2)  # Valor simulado
            wind_unit = "mph"
        else:  # metric
            temp = base_temp
            temp_unit = "°C"
            wind_speed = round(base_temp / 1.6)  # Valor simulado
            wind_unit = "km/h"

        # Generar condiciones aleatorias basadas en la temperatura
        if temp > 30:
            condition = "Soleado"
            humidity = 45
        elif temp > 25:
            condition = "Mayormente soleado"
            humidity = 55
        elif temp > 20:
            condition = "Parcialmente nublado"
            humidity = 65
        elif temp > 15:
            condition = "Nublado"
            humidity = 70
        elif temp > 10:
            condition = "Lluvioso"
            humidity = 80
        elif temp > 5:
            condition = "Lluvia ligera"
            humidity = 85
        elif temp > 0:
            condition = "Lluvia y nieve"
            humidity = 90
        else:
            condition = "Nevado"
            humidity = 95

        # Formatear resultado
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Crear el pronóstico para los próximos días
        forecast = []
        days = ["Hoy", "Mañana", "Pasado mañana"]

        for i, day in enumerate(days):
            # Variación de temperatura para los días siguientes
            variation = [-2, 1, 0][i]
            day_temp = temp + variation

            forecast.append({
                "day": day,
                "condition": condition,
                "temperature": f"{day_temp}{temp_unit}",
                "humidity": f"{humidity}%",
                "wind": f"{wind_speed} {wind_unit}"
            })

        # Hora local para amanecer y atardecer (simulado)
        now = datetime.now()
        sunrise = (now.replace(hour=7, minute=30, second=0)).strftime("%H:%M")
        sunset = (now.replace(hour=20, minute=15, second=0)).strftime("%H:%M")

        # Armar respuesta
        result = {
            "location": location,
            "current_conditions": {
                "temperature": f"{temp}{temp_unit}",
                "condition": condition,
                "humidity": f"{humidity}%",
                "wind": f"{wind_speed} {wind_unit}",
                "pressure": "1015 hPa",
                "feels_like": f"{temp - 2}{temp_unit}",
                "timestamp": timestamp
            },
            "sunrise": sunrise,
            "sunset": sunset,
            "forecast": forecast,
            "source": "Simulación (datos no reales)",
            "note": "Esta es una simulación para propósitos de demostración. Para obtener datos reales, configura la API key de OpenWeatherMap."
        }

        self.logger.debug(f"Datos de clima simulados generados para {location}: {temp}{temp_unit}, {condition}")
        return result
