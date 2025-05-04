#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo SystemInfo
----------------
Proporciona información sobre el sistema operativo y recursos del sistema.
"""

import os
import sys
import platform
import logging
import subprocess
import re
import json
from typing import Dict, Any, List, Tuple, Optional
import psutil
import socket
import locale
from datetime import datetime
import time

class SystemInfo:
    """
    Obtiene y proporciona información del sistema operativo y recursos.
    """

    def __init__(self):
        """Inicializa la clase de información del sistema."""
        self.logger = logging.getLogger("assistant.system")
        self.platform = platform.system().lower()
        self.logger.debug(f"Plataforma detectada: {self.platform}")

        # Cachear algunas informaciones que no cambian
        self._system_info = self._get_system_info()
        self._python_info = self._get_python_info()
        self._network_info = self._get_network_info()

    def get_all_info(self) -> Dict[str, Any]:
        """
        Obtiene toda la información del sistema.

        Returns:
            Diccionario con toda la información del sistema
        """
        info = {
            "system": self._system_info,
            "python": self._python_info,
            "resources": self.get_resource_usage(),
            "network": self._network_info
        }
        return info

    def _get_system_info(self) -> Dict[str, Any]:
        """
        Obtiene información del sistema operativo.

        Returns:
            Diccionario con información del sistema operativo
        """
        try:
            system_info = {
                "os": platform.system(),
                "os_release": platform.release(),
                "os_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "hostname": socket.gethostname(),
                "username": self._get_username(),
                "locale": locale.getdefaultlocale()[0],
                "timezone": time.tzname,
                "boot_time": self._get_boot_time()
            }

            # Información específica del sistema operativo
            if self.platform == "linux":
                system_info.update(self._get_linux_info())
            elif self.platform == "windows":
                system_info.update(self._get_windows_info())
            elif self.platform == "darwin":  # macOS
                system_info.update(self._get_macos_info())

            return system_info
        except Exception as e:
            self.logger.error(f"Error al obtener información del sistema: {str(e)}", exc_info=True)
            return {"error": str(e)}

    def _get_username(self) -> str:
        """
        Obtiene el nombre de usuario actual.

        Returns:
            Nombre de usuario
        """
        try:
            return os.getlogin()
        except:
            try:
                import getpass
                return getpass.getuser()
            except:
                return "unknown"

    def _get_boot_time(self) -> str:
        """
        Obtiene la fecha y hora de inicio del sistema.

        Returns:
            Fecha y hora de inicio del sistema en formato ISO
        """
        try:
            boot_time = psutil.boot_time()
            return datetime.fromtimestamp(boot_time).isoformat()
        except:
            return "unknown"

    def _get_linux_info(self) -> Dict[str, str]:
        """
        Obtiene información específica de Linux.

        Returns:
            Diccionario con información adicional de Linux
        """
        info = {"distro": ""}

        try:
            # Intentar obtener información de la distribución
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    os_release = {}
                    for line in f:
                        if "=" in line:
                            key, value = line.rstrip().split("=", 1)
                            os_release[key] = value.strip('"')

                    if "PRETTY_NAME" in os_release:
                        info["distro"] = os_release["PRETTY_NAME"]

            # Si no se pudo determinar la distribución
            if not info["distro"]:
                result = subprocess.run(["lsb_release", "-ds"],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      text=True,
                                      check=False)
                if result.returncode == 0:
                    info["distro"] = result.stdout.strip()

        except Exception as e:
            self.logger.debug(f"Error al obtener información de Linux: {str(e)}")

        return info

    def _get_windows_info(self) -> Dict[str, str]:
        """
        Obtiene información específica de Windows.

        Returns:
            Diccionario con información adicional de Windows
        """
        info = {}

        try:
            # Intentar obtener la versión de Windows usando WMI
            if platform.platform():
                info["windows_edition"] = platform.platform()

            # Intentar obtener información adicional con wmic
            try:
                result = subprocess.run(["wmic", "os", "get", "Caption,Version,BuildNumber", "/value"],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      text=True,
                                      check=False)
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()
                            if key == "Caption":
                                info["windows_caption"] = value
                            elif key == "BuildNumber":
                                info["build_number"] = value
            except:
                pass

        except Exception as e:
            self.logger.debug(f"Error al obtener información de Windows: {str(e)}")

        return info

    def _get_macos_info(self) -> Dict[str, str]:
        """
        Obtiene información específica de macOS.

        Returns:
            Diccionario con información adicional de macOS
        """
        info = {}

        try:
            # Intentar obtener la versión de macOS
            result = subprocess.run(["sw_vers"],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  text=True,
                                  check=False)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()
                        if key == "ProductName":
                            info["product_name"] = value
                        elif key == "ProductVersion":
                            info["product_version"] = value
                        elif key == "BuildVersion":
                            info["build_version"] = value

        except Exception as e:
            self.logger.debug(f"Error al obtener información de macOS: {str(e)}")

        return info

    def _get_python_info(self) -> Dict[str, Any]:
        """
        Obtiene información del entorno Python.

        Returns:
            Diccionario con información de Python
        """
        try:
            python_info = {
                "version": platform.python_version(),
                "implementation": platform.python_implementation(),
                "compiler": platform.python_compiler(),
                "executable": sys.executable,
                "packages": self._get_installed_packages()
            }
            return python_info
        except Exception as e:
            self.logger.error(f"Error al obtener información de Python: {str(e)}", exc_info=True)
            return {"error": str(e)}

    def _get_installed_packages(self) -> Dict[str, str]:
        """
        Obtiene los paquetes Python instalados.

        Returns:
            Diccionario con los paquetes instalados y sus versiones
        """
        packages = {}

        try:
            import pkg_resources
            for package in pkg_resources.working_set:
                packages[package.key] = package.version
        except:
            try:
                # Alternativa usando pip
                result = subprocess.run([sys.executable, "-m", "pip", "freeze"],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      text=True,
                                      check=False)
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if "==" in line:
                            name, version = line.split("==", 1)
                            packages[name] = version
            except:
                self.logger.warning("No se pudo obtener la lista de paquetes instalados")

        # Devolver solo una selección de paquetes relevantes
        relevant_packages = {}
        relevant_names = [
            "openai", "requests", "numpy", "scipy", "pandas", "tensorflow",
            "torch", "transformers", "nltk", "spacy", "scikit-learn",
            "matplotlib", "psutil", "pyaudio", "gtts", "pyttsx3", "speechrecognition"
        ]

        for name in relevant_names:
            if name in packages:
                relevant_packages[name] = packages[name]

        return relevant_packages

    def _get_network_info(self) -> Dict[str, Any]:
        """
        Obtiene información de red.

        Returns:
            Diccionario con información de red
        """
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)

            # Obtener todas las interfaces de red
            interfaces = {}
            for iface, addrs in psutil.net_if_addrs().items():
                # Ignorar interfaces virtuales y loopback
                if iface.startswith(("lo", "veth", "docker", "vmnet", "vbox")):
                    continue

                interfaces[iface] = []
                for addr in addrs:
                    if addr.family == socket.AF_INET:  # IPv4
                        interfaces[iface].append({
                            "ip": addr.address,
                            "netmask": addr.netmask,
                            "family": "IPv4"
                        })
                    elif addr.family == socket.AF_INET6:  # IPv6
                        interfaces[iface].append({
                            "ip": addr.address,
                            "netmask": addr.netmask,
                            "family": "IPv6"
                        })

            # Comprobar conectividad a Internet
            internet_connected = self._check_internet_connection()

            return {
                "hostname": hostname,
                "local_ip": local_ip,
                "interfaces": interfaces,
                "internet_connected": internet_connected
            }
        except Exception as e:
            self.logger.error(f"Error al obtener información de red: {str(e)}", exc_info=True)
            return {"error": str(e)}

    def _check_internet_connection(self) -> bool:
        """
        Comprueba si hay conexión a Internet.

        Returns:
            True si hay conexión a Internet, False en caso contrario
        """
        try:
            # Intentar conectar a Google DNS
            socket.create_connection(("8.8.8.8", 53), timeout=1)
            return True
        except:
            try:
                # Intentar resolver google.com
                socket.gethostbyname("google.com")
                return True
            except:
                return False

    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Obtiene información sobre el uso de recursos del sistema.

        Returns:
            Diccionario con información de uso de recursos
        """
        try:
            # CPU
            cpu_count = psutil.cpu_count(logical=True)
            cpu_physical_count = psutil.cpu_count(logical=False)
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # Memoria
            memory = psutil.virtual_memory()
            memory_total_mb = memory.total / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            memory_used_mb = memory.used / (1024 * 1024)
            memory_percent = memory.percent

            # Disco
            disk = psutil.disk_usage('/')
            disk_total_gb = disk.total / (1024 * 1024 * 1024)
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            disk_percent = disk.percent

            # Carga del sistema (solo para Linux y macOS)
            if self.platform in ["linux", "darwin"]:
                load_avg = os.getloadavg()
            else:
                load_avg = (0, 0, 0)

            # Información del proceso actual
            process = psutil.Process()
            process_cpu_percent = process.cpu_percent(interval=0.1)
            process_memory_info = process.memory_info()
            process_memory_mb = process_memory_info.rss / (1024 * 1024)

            return {
                "cpu": {
                    "count": cpu_count,
                    "physical_count": cpu_physical_count,
                    "percent": cpu_percent,
                    "load_avg": load_avg
                },
                "memory": {
                    "total_mb": round(memory_total_mb, 2),
                    "available_mb": round(memory_available_mb, 2),
                    "used_mb": round(memory_used_mb, 2),
                    "percent": memory_percent
                },
                "disk": {
                    "total_gb": round(disk_total_gb, 2),
                    "free_gb": round(disk_free_gb, 2),
                    "used_gb": round(disk_used_gb, 2),
                    "percent": disk_percent
                },
                "process": {
                    "pid": process.pid,
                    "cpu_percent": process_cpu_percent,
                    "memory_mb": round(process_memory_mb, 2),
                    "threads": process.num_threads()
                }
            }
        except Exception as e:
            self.logger.error(f"Error al obtener uso de recursos: {str(e)}", exc_info=True)
            return {"error": str(e)}

    def get_audio_devices(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Obtiene información sobre los dispositivos de audio disponibles.

        Returns:
            Diccionario con información de dispositivos de audio
        """
        devices = {"input": [], "output": []}

        try:
            import pyaudio

            p = pyaudio.PyAudio()
            info = p.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')

            for i in range(0, num_devices):
                device_info = p.get_device_info_by_index(i)

                if device_info.get('maxInputChannels') > 0:
                    devices["input"].append({
                        "index": i,
                        "name": device_info.get('name'),
                        "channels": device_info.get('maxInputChannels'),
                        "sample_rate": int(device_info.get('defaultSampleRate'))
                    })

                if device_info.get('maxOutputChannels') > 0:
                    devices["output"].append({
                        "index": i,
                        "name": device_info.get('name'),
                        "channels": device_info.get('maxOutputChannels'),
                        "sample_rate": int(device_info.get('defaultSampleRate'))
                    })

            p.terminate()
        except Exception as e:
            self.logger.warning(f"No se pudo obtener información de dispositivos de audio: {str(e)}")

        return devices

    def check_dependencies(self, required_packages: List[str]) -> Dict[str, bool]:
        """
        Comprueba si están instalados los paquetes requeridos.

        Args:
            required_packages: Lista de paquetes a comprobar

        Returns:
            Diccionario con el estado de cada paquete
        """
        status = {}

        for package in required_packages:
            try:
                __import__(package)
                status[package] = True
            except ImportError:
                status[package] = False

        return status

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la información del sistema a un diccionario.

        Returns:
            Diccionario con toda la información del sistema
        """
        return self.get_all_info()

    def to_json(self) -> str:
        """
        Convierte la información del sistema a formato JSON.

        Returns:
            Cadena JSON con la información del sistema
        """
        return json.dumps(self.get_all_info(), indent=2, ensure_ascii=False)
