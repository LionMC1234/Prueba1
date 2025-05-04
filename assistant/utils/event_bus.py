#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo EventBus
---------------
Sistema de bus de eventos para la comunicación entre componentes del asistente.
Implementa un patrón publicador-suscriptor (pub-sub) para desacoplar los componentes.
"""

import logging
import threading
import queue
import time
from typing import Dict, List, Callable, Any, Union, Optional

# Tipo para los manejadores de eventos
EventHandler = Callable[[Dict[str, Any]], None]

class EventBus:
    """
    Bus de eventos para comunicación entre componentes.
    Permite publicar eventos y suscribirse a ellos mediante callbacks.
    """

    def __init__(self, async_dispatch: bool = True):
        """
        Inicializa el bus de eventos.

        Args:
            async_dispatch: Si es True, los eventos se despachan en un hilo separado
        """
        self.logger = logging.getLogger("assistant.eventbus")
        self.subscribers: Dict[str, List[EventHandler]] = {}
        self.async_dispatch = async_dispatch
        self.running = False
        self.event_queue: queue.Queue = queue.Queue()
        self.dispatcher_thread: Optional[threading.Thread] = None

        if async_dispatch:
            self._start_dispatcher()

    def _start_dispatcher(self) -> None:
        """Inicia el hilo del despachador de eventos."""
        self.running = True
        self.dispatcher_thread = threading.Thread(
            target=self._event_dispatcher_loop,
            daemon=True,
            name="EventDispatcherThread"
        )
        self.dispatcher_thread.start()
        self.logger.debug("Despachador de eventos iniciado")

    def _event_dispatcher_loop(self) -> None:
        """Bucle principal del despachador de eventos."""
        while self.running:
            try:
                # Esperar un evento con timeout para poder comprobar periódicamente
                # si el bus sigue en ejecución
                try:
                    event_data = self.event_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Procesar el evento
                event_type = event_data.get("event_type", "")
                handlers = self.subscribers.get(event_type, [])

                if not handlers:
                    self.logger.debug(f"No hay suscriptores para el evento: {event_type}")
                    self.event_queue.task_done()
                    continue

                # Notificar a todos los suscriptores
                for handler in handlers:
                    try:
                        handler(event_data.get("data", {}))
                    except Exception as e:
                        self.logger.error(
                            f"Error en el manejador de eventos para {event_type}: {str(e)}",
                            exc_info=True
                        )

                self.event_queue.task_done()

            except Exception as e:
                self.logger.error(f"Error en el bucle del despachador: {str(e)}", exc_info=True)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Suscribe un manejador a un tipo de evento.

        Args:
            event_type: Tipo de evento al que suscribirse
            handler: Función de callback que se llamará cuando ocurra el evento
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []

        self.subscribers[event_type].append(handler)
        self.logger.debug(f"Nuevo suscriptor registrado para el evento: {event_type}")

    def unsubscribe(self, event_type: str, handler: EventHandler) -> bool:
        """
        Cancela la suscripción de un manejador a un tipo de evento.

        Args:
            event_type: Tipo de evento
            handler: Manejador a eliminar

        Returns:
            bool: True si el manejador fue eliminado, False si no existía
        """
        if event_type in self.subscribers and handler in self.subscribers[event_type]:
            self.subscribers[event_type].remove(handler)
            self.logger.debug(f"Suscriptor eliminado para el evento: {event_type}")
            return True
        return False

    def publish(self, event_type: str, data: Dict[str, Any] = None) -> None:
        """
        Publica un evento en el bus.

        Args:
            event_type: Tipo de evento a publicar
            data: Datos asociados al evento
        """
        if data is None:
            data = {}

        event_data = {
            "event_type": event_type,
            "data": data,
            "timestamp": time.time()
        }

        self.logger.debug(f"Evento publicado: {event_type}")

        if self.async_dispatch:
            # En modo asíncrono, encolar el evento para procesamiento
            self.event_queue.put(event_data)
        else:
            # En modo síncrono, procesar inmediatamente
            handlers = self.subscribers.get(event_type, [])
            for handler in handlers:
                try:
                    handler(data)
                except Exception as e:
                    self.logger.error(
                        f"Error en el manejador de eventos para {event_type}: {str(e)}",
                        exc_info=True
                    )

    def shutdown(self) -> None:
        """Detiene el bus de eventos y libera recursos."""
        if self.async_dispatch and self.running:
            self.running = False

            # Esperar a que el despachador termine (con timeout)
            if self.dispatcher_thread and self.dispatcher_thread.is_alive():
                self.dispatcher_thread.join(timeout=2.0)

            # Limpiar la cola de eventos
            with self.event_queue.mutex:
                self.event_queue.queue.clear()

            self.logger.debug("Bus de eventos detenido")
