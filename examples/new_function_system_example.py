#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ejemplo del nuevo sistema de funciones
-------------------------------------
Este script demuestra cómo usar el nuevo sistema de funciones con
definiciones centralizadas en un archivo separado.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI

# Añadir el directorio raíz al path para importar los módulos del asistente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assistant.utils.logger import setup_logger
from assistant.functions.function_manager import FunctionManager

def setup_environment():
    """Configura el entorno de ejecución."""
    # Cargar variables de entorno
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"Variables de entorno cargadas desde: {env_path}")
    else:
        print("Archivo .env no encontrado, asegúrate de configurar OPENAI_API_KEY y SERPER_API_KEY en las variables de entorno")

    # Configurar logger
    setup_logger()

def main():
    """Función principal del ejemplo."""
    setup_environment()
    logger = logging.getLogger("example")
    logger.info("Iniciando ejemplo del nuevo sistema de funciones")

    # Inicializar el gestor de funciones
    function_manager = FunctionManager()

    # Obtener las definiciones de funciones para la API
    tools = function_manager.get_all_functions()

    # Inicializar el cliente de OpenAI
    client = OpenAI()

    # Historial de mensajes
    messages = [{
        "role": "system",
        "content": "Eres un asistente personal virtual inteligente. Utiliza las funciones disponibles cuando sea necesario para proporcionar información precisa y actualizada. Responde de manera clara y concisa."
    }]

    print("\n=== Ejemplo del Nuevo Sistema de Funciones ===\n")
    print("Puedes hacer pruebas como:")
    print("- ¿Cómo está el clima en Barcelona?")
    print("- Busca información sobre inteligencia artificial")
    print("- ¿Qué es la energía renovable?")
    print("- Escribe 'salir' para terminar")
    print("\nEl sistema utilizará las funciones definidas en function_definitions.py automáticamente cuando sea necesario\n")

    # Bucle principal
    while True:
        try:
            # Obtener entrada del usuario
            user_input = input("\nTú: ")

            if user_input.lower() in ["salir", "exit", "quit"]:
                break

            # Añadir mensaje del usuario al historial
            messages.append({"role": "user", "content": user_input})

            # Realizar llamada a la API con las herramientas/funciones
            response = client.chat.completions.create(
                model="gpt-4o",  # O el modelo que prefieras que soporte herramientas
                messages=messages,
                tools=tools
            )

            # Obtener la respuesta del asistente
            assistant_message = response.choices[0].message

            # Añadir mensaje del asistente al historial
            messages.append(assistant_message)

            # Verificar si hay llamadas a herramientas/funciones
            if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                print("\nAsistente: Necesito consultar información externa...")

                # Procesar cada llamada a función
                for tool_call in assistant_message.tool_calls:
                    function_call = {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }

                    # Ejecutar la función
                    result = function_manager.handle_function_call(function_call)

                    # Formatear el resultado para la API
                    messages.append(
                        function_manager.format_function_results_for_api(tool_call.id, result)
                    )

                    # Mostrar información de depuración
                    print(f"\n[DEBUG] Función llamada: {tool_call.function.name}")
                    print(f"[DEBUG] Argumentos: {tool_call.function.arguments}")

                    if "error" in result:
                        print(f"[DEBUG] Error: {result['error']}")
                    else:
                        # Abreviamos la salida para que no sea demasiado larga
                        result_summary = str(result)[:150] + "..." if len(str(result)) > 150 else str(result)
                        print(f"[DEBUG] Resultado (resumido): {result_summary}")

                # Segunda llamada para obtener la respuesta final
                second_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )

                # Obtener respuesta final
                final_response = second_response.choices[0].message.content
                messages.append({"role": "assistant", "content": final_response})
                print(f"\nAsistente: {final_response}")

            else:
                # No se llamó a ninguna función, mostrar la respuesta directa
                print(f"\nAsistente: {assistant_message.content}")

        except KeyboardInterrupt:
            print("\nFinalizando programa...")
            break
        except Exception as e:
            logger.error(f"Error: {str(e)}", exc_info=True)
            print(f"\nError: {str(e)}")
            # Intenta continuar con la siguiente iteración

    logger.info("Programa finalizado")
    print("\n¡Gracias por probar el nuevo sistema de funciones!")

if __name__ == "__main__":
    main()
