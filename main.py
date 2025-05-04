#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Asistente Personal Virtual
--------------------------
Un asistente personal inteligente con capacidades de voz y procesamiento de lenguaje natural
utilizando la API de OpenAI (ChatGPT).

Este módulo sirve como punto de entrada principal al asistente.
"""

import sys
import os
import logging
import signal
from dotenv import load_dotenv
from assistant.core.assistant_manager import AssistantManager
from assistant.utils.config_manager import ConfigManager
from assistant.utils.logger import setup_logger

def signal_handler(sig, frame):
    """Manejador de señales para terminar el programa correctamente."""
    print("\nDeteniendo el asistente...")
    sys.exit(0)

def main():
    """Función principal que inicializa y ejecuta el asistente virtual."""
    # Configurar el manejador de señales para CTRL+C
    signal.signal(signal.SIGINT, signal_handler)

    # Cargar variables de entorno
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"Variables de entorno cargadas desde: {env_path}")
    else:
        print("Archivo .env no encontrado, usando variables de entorno del sistema si existen")

    # Configurar el logger
    setup_logger()
    logger = logging.getLogger("assistant")
    logger.info("Iniciando Asistente Personal Virtual")

    try:
        # Cargar configuración
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        config_manager = ConfigManager(config_path)
        config = config_manager.get_config()

        # Inicializar el asistente
        assistant = AssistantManager(config)

        # Iniciar el asistente
        logger.info("Asistente listo para interactuar")
        assistant.run()

    except Exception as e:
        logger.error(f"Error al iniciar el asistente: {str(e)}", exc_info=True)
        print(f"Error al iniciar el asistente: {str(e)}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())