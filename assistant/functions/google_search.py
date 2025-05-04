#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo de función para búsqueda en Google
-----------------------------------------
Implementa una función para buscar información en Google utilizando la API de Serper.dev
"""

import os
import json
import logging
import http.client
from typing import Dict, Any, Optional, List
from urllib.parse import quote

class GoogleSearchFunction:
    """
    Implementa la funcionalidad de búsqueda en Google usando la API de Serper.dev
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa la función de búsqueda en Google.

        Args:
            api_key: API key para Serper.dev (opcional, puede tomarse de las variables de entorno)
        """
        self.logger = logging.getLogger("assistant.functions.google_search")

        # Obtener API key desde parámetro o variable de entorno
        self.api_key = api_key or os.environ.get("SERPER_API_KEY", "")

        if not self.api_key:
            self.logger.warning("API key para Serper.dev no configurada. La búsqueda en Google no funcionará correctamente.")

    def search_google(self,
                     query: str,
                     language: str = "es-419",
                     country: str = "mx",
                     num_results: int = 5) -> Dict[str, Any]:
        """
        Realiza una búsqueda en Google utilizando la API de Serper.dev.

        Args:
            query: Consulta de búsqueda
            language: Código de idioma (por defecto: es-419 para español de Latinoamérica)
            country: Código de país (por defecto: mx para México)
            num_results: Número de resultados a devolver (1-10)

        Returns:
            Resultados de la búsqueda formateados
        """
        try:
            self.logger.info(f"Realizando búsqueda en Google: '{query}'")

            # Validar parámetros
            num_results = min(max(1, num_results), 10)  # Entre 1 y 10

            # Crear conexión HTTPS
            conn = http.client.HTTPSConnection("google.serper.dev")

            # Preparar payload
            payload = json.dumps({
                "q": query,
                "gl": country,
                "hl": language,
                "num": num_results
            })

            # Preparar headers
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }

            # Realizar la solicitud
            conn.request("POST", "/search", payload, headers)

            # Obtener respuesta
            response = conn.getresponse()
            data = response.read()

            # Procesar respuesta
            if response.status != 200:
                error_message = f"Error en la API de Serper.dev: {response.status} {response.reason}"
                self.logger.error(error_message)
                return {
                    "error": error_message,
                    "query": query
                }

            # Parsear JSON de respuesta
            raw_results = json.loads(data.decode("utf-8"))

            # Formatear resultados para una respuesta más útil
            formatted_results = self._format_search_results(raw_results, query)

            self.logger.debug(f"Búsqueda completada: {len(formatted_results.get('organic', []))} resultados orgánicos encontrados")
            return formatted_results

        except Exception as e:
            error_message = f"Error al realizar búsqueda en Google: {str(e)}"
            self.logger.error(error_message, exc_info=True)
            return {
                "error": error_message,
                "query": query
            }

    def _format_search_results(self, raw_results: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Formatea los resultados crudos de la API para una presentación más limpia.

        Args:
            raw_results: Resultados crudos de la API
            query: Consulta original

        Returns:
            Resultados formateados
        """
        formatted = {
            "query": query,
            "organic": [],
            "knowledge_graph": None,
            "answer_box": None,
            "total_results": raw_results.get("searchParameters", {}).get("totalResults", ""),
            "time_taken": raw_results.get("searchParameters", {}).get("processingTimeMs", 0)
        }

        # Procesar resultados orgánicos
        if "organic" in raw_results:
            for result in raw_results["organic"][:10]:  # Máximo 10 resultados
                formatted_result = {
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "position": result.get("position", 0)
                }
                formatted["organic"].append(formatted_result)

        # Procesar knowledge graph si existe
        if "knowledgeGraph" in raw_results:
            kg = raw_results["knowledgeGraph"]
            formatted["knowledge_graph"] = {
                "title": kg.get("title", ""),
                "type": kg.get("type", ""),
                "description": kg.get("description", ""),
                "attributes": kg.get("attributes", {})
            }

        # Procesar answer box si existe
        if "answerBox" in raw_results:
            ab = raw_results["answerBox"]
            formatted["answer_box"] = {
                "title": ab.get("title", ""),
                "answer": ab.get("answer", ""),
                "snippet": ab.get("snippet", "")
            }

        return formatted
