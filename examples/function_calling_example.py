#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ejemplo de uso del sistema de llamadas a funciones
-------------------------------------------------
Este script demuestra cómo el asistente puede tomar decisiones automáticas sobre
cuándo llamar a funciones basado en la entrada del usuario.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Añadir el directorio raíz al path para importar los módulos del asistente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assistant.utils.event_bus import EventBus
from assistant.utils.logger import setup_logger
from assistant.modules.ai_processor import AIProcessor
from assistant.modules.function_calling import FunctionCallingManager, FunctionRegistry
from assistant.modules.weather_function import WeatherFunction
from assistant.modules.reminder_function import ReminderFunction

def setup_environment():
    """Configura el entorno de ejecución."""
    # Cargar variables de entorno
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"Variables de entorno cargadas desde: {env_path}")
    else:
        print("Archivo .env no encontrado, asegúrate de configurar OPENAI_API_KEY en las variables de entorno")

    # Configurar logger
    setup_logger()

def main():
    """Función principal del ejemplo."""
    setup_environment()
    logger = logging.getLogger("example")
    logger.info("Iniciando ejemplo de llamadas a funciones")

    # Crear el bus de eventos
    event_bus = EventBus()

    # Configurar manejadores de eventos
    event_bus.subscribe("ai_response_received", handle_ai_response)
    event_bus.subscribe("functions_called", handle_function_call)
    event_bus.subscribe("error", handle_error)

    # Configuración básica para el ejemplo
    ai_config = {
        "provider": "openai",
        "model": "gpt-4o",  # Asegúrate de usar un modelo que soporte herramientas/funciones
        "max_tokens": 2048,
        "temperature": 0.7,
        "system_prompt": "Eres un asistente personal virtual inteligente, útil, educado y conciso. Responde de manera clara y eficiente a las preguntas y solicitudes del usuario.",
        "stream_response": False  # Desactivamos streaming para este ejemplo para simplicidad
    }

    # Crear el procesador de IA
    ai_processor = AIProcessor(ai_config, event_bus)

    # Configurar las funciones de clima y recordatorios
    weather_config = {
        "default_location": "Madrid, España",
        "units": "metric"
    }

    reminders_config = {
        "notification_sound": True,
        "advance_notice": 5
    }

    # Crear las funciones
    weather_function = WeatherFunction(weather_config)
    reminder_function = ReminderFunction(reminders_config, event_bus)

    # Registrar las funciones en el procesador de IA
    ai_processor.register_function(
        weather_function.get_weather_function_definition(),
        weather_function.get_weather
    )

    ai_processor.register_function(
        reminder_function.get_reminder_function_definition(),
        reminder_function.create_reminder
    )

    logger.info("Sistema inicializado, listo para procesar consultas")
    print("\n=== Ejemplo de Sistema Inteligente de Llamadas a Funciones ===\n")
    print("Puedes hacer pruebas como:")
    print("- ¿Cómo está el clima en Barcelona?")
    print("- Crea un recordatorio para llamar al médico mañana a las 10:00")
    print("- ¿Qué es la inteligencia artificial?")
    print("- Escribe 'salir' para terminar")
    print("\nEl asistente decidirá automáticamente si necesita llamar a una función o no\n")

    # Historial de conversación
    conversation_history = []

    # Bucle principal
    while True:
        try:
            # Obtener entrada del usuario
            user_input = input("\nTú: ")

            if user_input.lower() in ["salir", "exit", "quit"]:
                break

            # Procesar con el asistente
            ai_processor.process_input(user_input, conversation_history)

            # Esperar respuesta (en una aplicación real tendríamos un bucle de eventos)
            # Aquí se ejecutarán los manejadores de eventos registrados

        except KeyboardInterrupt:
            print("\nFinalizando programa...")
            break
        except Exception as e:
            logger.error(f"Error: {str(e)}", exc_info=True)
            print(f"\nError: {str(e)}")

    logger.info("Programa finalizado")
    print("\n¡Gracias por probar el ejemplo!")

def handle_ai_response(data):
    """Maneja las respuestas del asistente."""
    response = data.get("response", "")
    print(f"\nAsistente: {response}")

def handle_function_call(data):
    """Maneja la información de llamadas a funciones."""
    tool_calls = data.get("tool_calls", [])
    results = data.get("results", {})

    for tool_call in tool_calls:
        function_name = tool_call.get("function", {}).get("name", "")
        function_args = tool_call.get("function", {}).get("arguments", "{}")
        tool_call_id = tool_call.get("id", "")

        # Obtener el resultado si existe
        result = results.get(tool_call_id, {})

        # Mostrar información de depuración
        print(f"\n[DEBUG] Llamada a función detectada: {function_name}")
        print(f"[DEBUG] Argumentos: {function_args}")

        if "error" in result:
            print(f"[DEBUG] Error: {result['error']}")
        else:
            print(f"[DEBUG] Resultado: {json.dumps(result.get('result', {}), indent=2, ensure_ascii=False)}")

def handle_error(data):
    """Maneja errores reportados."""
    message = data.get("message", "Error desconocido")
    source = data.get("source", "sistema")
    print(f"\n[ERROR] Error en {source}: {message}")

if __name__ == "__main__":
    main()
