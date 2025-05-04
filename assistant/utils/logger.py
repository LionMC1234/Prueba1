#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo Logger
------------
Configura el sistema de registro (logging) del asistente.
"""

import os
import logging
import logging.handlers
import time
import json
from typing import Dict, Any, Optional
from pathlib import Path

class JsonFormatter(logging.Formatter):
    """
    Formateador de logs en formato JSON estructurado.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Formatea el registro de log en JSON.

        Args:
            record: Registro de log a formatear

        Returns:
            Registro formateado en JSON
        """
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }

        # Agregar información de la excepción si existe
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }

        # Agregar información extra si existe
        if hasattr(record, "extra") and record.extra:
            log_data["extra"] = record.extra

        return json.dumps(log_data, ensure_ascii=False)

class CustomLogger(logging.Logger):
    """
    Logger personalizado con funciones adicionales.
    """

    def __init__(self, name: str, level: int = logging.NOTSET):
        """
        Inicializa el logger personalizado.

        Args:
            name: Nombre del logger
            level: Nivel de log
        """
        super().__init__(name, level)
        self.metrics: Dict[str, Any] = {}

    def log_with_extra(self, level: int, msg: str, extra: Dict[str, Any] = None, **kwargs) -> None:
        """
        Registra un mensaje con información extra.

        Args:
            level: Nivel de log
            msg: Mensaje
            extra: Información extra
            **kwargs: Argumentos adicionales para el método log
        """
        if extra is None:
            extra = {}

        # Crear un objeto LogRecord personalizado
        record = self.makeRecord(
            self.name, level, "(unknown file)", 0, msg,
            args=(), exc_info=kwargs.get("exc_info"),
            func=kwargs.get("func"), extra={"extra": extra}
        )

        self.handle(record)

    def start_timer(self, name: str) -> None:
        """
        Inicia un temporizador para medir el tiempo de una operación.

        Args:
            name: Nombre del temporizador
        """
        self.metrics[f"timer_{name}"] = time.time()

    def stop_timer(self, name: str, log_level: int = logging.DEBUG) -> float:
        """
        Detiene un temporizador y registra el tiempo transcurrido.

        Args:
            name: Nombre del temporizador
            log_level: Nivel de log para registrar el tiempo

        Returns:
            Tiempo transcurrido en segundos
        """
        if f"timer_{name}" not in self.metrics:
            self.warning(f"Temporizador '{name}' no encontrado")
            return 0.0

        elapsed = time.time() - self.metrics[f"timer_{name}"]

        if log_level is not None:
            self.log(log_level, f"Tiempo para '{name}': {elapsed:.4f} segundos")

        return elapsed

    def collect_metric(self, name: str, value: Any) -> None:
        """
        Registra una métrica personalizada.

        Args:
            name: Nombre de la métrica
            value: Valor de la métrica
        """
        self.metrics[f"metric_{name}"] = value
        self.debug(f"Métrica '{name}': {value}")

def setup_logger(config: Dict[str, Any] = None) -> None:
    """
    Configura el sistema de logs del asistente.

    Args:
        config: Configuración del sistema de logs. Si no se proporciona,
               se utilizan valores por defecto.
    """
    if config is None:
        config = {
            "log_level": "INFO",
            "log_file": "logs/assistant.log",
            "log_rotation": True,
            "max_log_size": 10,  # MB
            "backup_count": 5,
            "console_output": True,
            "json_format": False,
        }

    # Registrar la clase de logger personalizada
    logging.setLoggerClass(CustomLogger)

    # Obtener el logger raíz del asistente
    logger = logging.getLogger("assistant")

    # Establecer el nivel de log
    log_level_name = config.get("log_level", "INFO")
    log_level = getattr(logging, log_level_name, logging.INFO)
    logger.setLevel(log_level)

    # Eliminar handlers existentes
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Crear directorio de logs si no existe
    log_file = config.get("log_file", "logs/assistant.log")
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # Configurar los formateadores
    if config.get("json_format", False):
        file_formatter = JsonFormatter()
    else:
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )

    # Configurar el handler para archivo con rotación
    if config.get("log_rotation", True):
        max_bytes = config.get("max_log_size", 10) * 1024 * 1024  # Convertir MB a bytes
        backup_count = config.get("backup_count", 5)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
    else:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')

    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Configurar el handler para la consola
    if config.get("console_output", True):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)

        # Solo enviar a la consola los mensajes de nivel INFO o superior
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    # Log inicial
    logger.info("Sistema de logs inicializado")
    logger.debug(f"Nivel de log configurado a: {log_level_name}")

    # Configurar el comportamiento de las excepciones no manejadas
    def handle_exception(exc_type, exc_value, exc_traceback):
        """Manejador global de excepciones no capturadas."""
        # Ignorar excepciones de teclado (Ctrl+C)
        if issubclass(exc_type, KeyboardInterrupt):
            return

        logger.critical("Excepción no manejada:", exc_info=(exc_type, exc_value, exc_traceback))

    # logging.basicConfig(level=logging.INFO)  # Configuración básica para otros loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)  # Silenciar logs detallados de urllib3


def get_logger(name: str) -> CustomLogger:
    """
    Obtiene un logger para un componente específico.

    Args:
        name: Nombre del componente

    Returns:
        Logger configurado para el componente
    """
    return logging.getLogger(f"assistant.{name}")


class LoggingContext:
    """
    Contexto para agrupar logs y medir el tiempo de operaciones.

    Ejemplo:
    ```
    with LoggingContext(logger, "operación_compleja") as log_ctx:
        # Hacer operación
        log_ctx.log("Paso intermedio completado")
    # Al salir del contexto, se registra el tiempo total
    ```
    """

    def __init__(self, logger: logging.Logger, operation_name: str, level: int = logging.DEBUG):
        """
        Inicializa el contexto de logging.

        Args:
            logger: Logger a utilizar
            operation_name: Nombre de la operación
            level: Nivel de log
        """
        self.logger = logger
        self.operation_name = operation_name
        self.level = level
        self.start_time = None

    def __enter__(self) -> 'LoggingContext':
        """
        Inicia el contexto de logging.

        Returns:
            El propio objeto LoggingContext
        """
        self.start_time = time.time()
        self.logger.log(self.level, f"Iniciando: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Finaliza el contexto de logging y registra el tiempo total.

        Args:
            exc_type: Tipo de excepción si ocurrió alguna
            exc_val: Valor de la excepción
            exc_tb: Traceback de la excepción
        """
        elapsed = time.time() - self.start_time

        if exc_type is not None:
            self.logger.error(
                f"Error en {self.operation_name}: {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb)
            )

        self.logger.log(self.level, f"Completado: {self.operation_name} en {elapsed:.4f} segundos")

    def log(self, message: str, level: int = None) -> None:
        """
        Registra un mensaje dentro del contexto.

        Args:
            message: Mensaje a registrar
            level: Nivel de log opcional (usa el nivel del contexto por defecto)
        """
        if level is None:
            level = self.level

        self.logger.log(level, f"[{self.operation_name}] {message}")
