#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo de función para gestionar recordatorios
---------------------------------------------
Implementa una función para crear recordatorios que puede ser llamada automáticamente
por el asistente cuando detecta que el usuario está pidiendo crear un recordatorio.
"""

import logging
import json
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timedelta
import threading
import time

class ReminderFunction:
    """
    Implementa funciones relacionadas con recordatorios para ser utilizadas
    por el sistema de llamada a funciones.
    """

    def __init__(self, config: Dict[str, Any], event_bus=None):
        """
        Inicializa la función de recordatorios.

        Args:
            config: Configuración para el servicio de recordatorios
            event_bus: Bus de eventos para notificar recordatorios
        """
        self.logger = logging.getLogger("assistant.functions.reminders")
        self.config = config
        self.event_bus = event_bus

        # Almacenamiento de recordatorios (en una aplicación real esto estaría en una base de datos)
        self.reminders: List[Dict[str, Any]] = []

        # Hilo para verificar recordatorios
        self.check_thread = None
        self.running = False

        # Iniciar el hilo de verificación si event_bus está disponible
        if self.event_bus:
            self.start_checking()

    def get_reminder_function_definition(self) -> Dict[str, Any]:
        """
        Obtiene la definición de la función para la API de OpenAI.

        Returns:
            Definición de la función en formato compatible con OpenAI
        """
        return {
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

    def create_reminder(self,
                       title: str,
                       time: str,
                       date: Optional[str] = None,
                       description: Optional[str] = None) -> Dict[str, Any]:
        """
        Crea un nuevo recordatorio.

        Args:
            title: Título del recordatorio
            time: Hora del recordatorio
            date: Fecha del recordatorio (opcional)
            description: Descripción detallada (opcional)

        Returns:
            Información del recordatorio creado
        """
        self.logger.info(f"Creando recordatorio: {title} para {date} {time}")

        try:
            # Parsear la fecha y hora
            reminder_datetime = self._parse_datetime(time, date)

            # Crear el recordatorio
            reminder_id = len(self.reminders) + 1
            reminder = {
                "id": reminder_id,
                "title": title,
                "datetime": reminder_datetime,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "notified": False
            }

            # Guardar el recordatorio
            self.reminders.append(reminder)

            # Formatear la respuesta
            response = {
                "id": reminder_id,
                "title": title,
                "time": reminder_datetime.strftime("%H:%M"),
                "date": reminder_datetime.strftime("%Y-%m-%d"),
                "description": description,
                "message": f"Recordatorio '{title}' creado para el {reminder_datetime.strftime('%d/%m/%Y')} a las {reminder_datetime.strftime('%H:%M')}."
            }

            self.logger.debug(f"Recordatorio creado: {response}")
            return response

        except Exception as e:
            error_msg = f"Error al crear recordatorio: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "title": title,
                "time": time,
                "date": date
            }

    def _parse_datetime(self, time_str: str, date_str: Optional[str] = None) -> datetime:
        """
        Parsea la fecha y hora de strings a datetime.

        Args:
            time_str: String con la hora
            date_str: String con la fecha (opcional)

        Returns:
            Objeto datetime
        """
        now = datetime.now()
        result_date = now.date()
        result_time = now.time()

        # Procesar la fecha
        if date_str:
            # Caso fecha específica en formato YYYY-MM-DD
            if "-" in date_str and len(date_str.split("-")) == 3:
                try:
                    result_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            # Caso "hoy"
            elif date_str.lower() in ["hoy", "today"]:
                result_date = now.date()

            # Caso "mañana"
            elif date_str.lower() in ["mañana", "tomorrow"]:
                result_date = (now + timedelta(days=1)).date()

            # Caso día de la semana
            else:
                days = {
                    "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2, "jueves": 3,
                    "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6,
                    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                    "friday": 4, "saturday": 5, "sunday": 6
                }

                day_name = date_str.lower()
                if day_name in days:
                    target_weekday = days[day_name]
                    current_weekday = now.weekday()
                    days_ahead = (target_weekday - current_weekday) % 7
                    if days_ahead == 0:  # Si es el mismo día de la semana, ir al de la próxima semana
                        days_ahead = 7
                    result_date = (now + timedelta(days=days_ahead)).date()

        # Procesar la hora
        if ":" in time_str:
            # Formato HH:MM
            try:
                time_parts = time_str.split(":")
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                result_time = datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
            except ValueError:
                pass
        else:
            # Formato relativo ("5 minutos", "1 hora", etc.)
            parts = time_str.lower().split()
            if len(parts) >= 2:
                try:
                    amount = int(parts[0])
                    unit = parts[1].rstrip("s")  # Eliminar 's' final si existe

                    if unit in ["minuto", "minute"]:
                        result_datetime = now + timedelta(minutes=amount)
                        return result_datetime
                    elif unit in ["hora", "hour"]:
                        result_datetime = now + timedelta(hours=amount)
                        return result_datetime
                    elif unit in ["día", "dia", "day"]:
                        result_datetime = now + timedelta(days=amount)
                        return result_datetime
                except ValueError:
                    pass

        # Combinar fecha y hora
        result_datetime = datetime.combine(result_date, result_time)

        # Si la hora ya pasó y no se especificó fecha, asumir que es para mañana
        if result_datetime < now and not date_str:
            result_datetime = datetime.combine(result_date + timedelta(days=1), result_time)

        return result_datetime

    def start_checking(self) -> None:
        """
        Inicia el hilo de verificación de recordatorios.
        """
        if self.check_thread is not None and self.check_thread.is_alive():
            return

        self.running = True
        self.check_thread = threading.Thread(target=self._check_reminders_loop, daemon=True)
        self.check_thread.start()
        self.logger.info("Hilo de verificación de recordatorios iniciado")

    def stop_checking(self) -> None:
        """
        Detiene el hilo de verificación de recordatorios.
        """
        self.running = False
        if self.check_thread:
            self.check_thread.join(timeout=1.0)
        self.logger.info("Hilo de verificación de recordatorios detenido")

    def _check_reminders_loop(self) -> None:
        """
        Bucle para verificar recordatorios pendientes.
        """
        while self.running:
            now = datetime.now()

            for reminder in self.reminders:
                if not reminder["notified"]:
                    reminder_time = datetime.fromisoformat(reminder["datetime"])
                    if reminder_time <= now:
                        # Notificar recordatorio
                        reminder["notified"] = True
                        self._notify_reminder(reminder)

            # Esperar antes de la próxima verificación
            time.sleep(60)  # Verificar cada minuto

    def _notify_reminder(self, reminder: Dict[str, Any]) -> None:
        """
        Notifica un recordatorio vencido.

        Args:
            reminder: Datos del recordatorio
        """
        if self.event_bus:
            self.logger.info(f"Notificando recordatorio: {reminder['title']}")

            # Publicar evento de recordatorio
            self.event_bus.publish("reminder_triggered", {
                "id": reminder["id"],
                "title": reminder["title"],
                "description": reminder.get("description", ""),
                "datetime": reminder["datetime"]
            })
        else:
            self.logger.warning("No se puede notificar recordatorio: no hay event_bus")

    def get_active_reminders(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de recordatorios activos (no notificados).

        Returns:
            Lista de recordatorios activos
        """
        return [r for r in self.reminders if not r["notified"]]

    def get_all_reminders(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista completa de recordatorios.

        Returns:
            Lista de todos los recordatorios
        """
        return self.reminders

    def clear_notified_reminders(self) -> int:
        """
        Elimina los recordatorios ya notificados.

        Returns:
            Número de recordatorios eliminados
        """
        before_count = len(self.reminders)
        self.reminders = [r for r in self.reminders if not r["notified"]]
        return before_count - len(self.reminders)
