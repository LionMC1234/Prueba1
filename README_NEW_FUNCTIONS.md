# Nuevo Sistema de Funciones del Asistente

Este documento describe la nueva implementación del sistema de funciones para el asistente virtual, en la que las definiciones de todas las funciones están centralizadas en un archivo separado.

## Características principales

- **Definiciones centralizadas**: Todas las definiciones de funciones están en un único archivo `function_definitions.py`
- **Implementación modular**: Cada función tiene su propio módulo específico
- **Gestor unificado**: Un gestor central (`FunctionManager`) maneja todas las funciones
- **Integración con OpenAI**: Compatible con el sistema de tools/functions de la API de OpenAI
- **Extensible**: Fácil de añadir nuevas funciones sin modificar el código central

## Estructura de archivos

```
assistant/functions/
├── __init__.py                  # Inicialización del paquete
├── function_definitions.py      # Definiciones centralizadas (formato JSON)
├── function_manager.py          # Gestor central de funciones
├── weather.py                   # Implementación de función del clima
└── google_search.py             # Implementación de búsqueda en Google
```

## Funciones disponibles

Actualmente el sistema incluye las siguientes funciones:

### 1. Obtener el clima (`get_weather`)

Proporciona información meteorológica actual y pronóstico para cualquier ubicación.

**Parámetros:**
- `location`: Ubicación para consultar el clima (ej. "Madrid, España")
- `units`: Sistema de unidades ("metric" o "imperial")

**Ejemplo de uso:**
```python
result = function_manager.execute_function("get_weather", location="Barcelona", units="metric")
```

### 2. Búsqueda en Google (`search_google`)

Realiza búsquedas en Google utilizando la API de Serper.dev para obtener información actualizada.

**Parámetros:**
- `query`: Términos de búsqueda
- `language`: Código de idioma (por defecto: "es-419" para español latinoamericano)
- `country`: Código de país (por defecto: "mx" para México)
- `num_results`: Número de resultados a devolver (1-10)

**Ejemplo de uso:**
```python
result = function_manager.execute_function("search_google",
                                          query="últimas noticias tecnología",
                                          language="es-419",
                                          country="mx",
                                          num_results=5)
```

## Cómo funciona el sistema

1. Las definiciones de todas las funciones están en formato JSON en `function_definitions.py`
2. Cada implementación de función está en su propio archivo (ej. `weather.py`, `google_search.py`)
3. El `FunctionManager` se encarga de registrar y ejecutar las funciones
4. Cuando el asistente necesita información externa:
   - Se envían todas las definiciones de funciones a la API de OpenAI
   - El modelo decide automáticamente si necesita llamar a alguna función
   - Si decide llamar a una función, el gestor ejecuta la función apropiada
   - Los resultados se devuelven al modelo para generar una respuesta final

## Cómo añadir una nueva función

1. **Definir la función en `function_definitions.py`:**
   ```python
   MI_NUEVA_FUNCION = {
       "type": "function",
       "function": {
           "name": "mi_funcion",
           "description": "Descripción de lo que hace mi función",
           "parameters": {
               "type": "object",
               "properties": {
                   "parametro1": {
                       "type": "string",
                       "description": "Descripción del parámetro"
                   },
                   # Más parámetros...
               },
               "required": ["parametro1"]
           }
       }
   }

   # Añadir a la lista de funciones disponibles
   AVAILABLE_FUNCTIONS.append(MI_NUEVA_FUNCION)
   ```

2. **Crear un módulo para implementar la función:**
   ```python
   # mi_funcion.py
   class MiFuncion:
       def __init__(self):
           # Inicialización
           pass

       def mi_funcion(self, parametro1, parametro2=None):
           # Implementación
           return {"resultado": "Datos procesados"}
   ```

3. **Registrar la función en `function_manager.py`:**
   ```python
   # Añadir la importación
   from assistant.functions.mi_funcion import MiFuncion

   # En el método _register_all_functions
   mi_funcion = MiFuncion()
   self.register_function("mi_funcion", mi_funcion.mi_funcion)
   ```

## Requisitos

- Python 3.8 o superior
- OpenAI SDK v1.0 o superior
- Para búsquedas en Google: API key de Serper.dev
- Dependencias adicionales listadas en requirements.txt

## Cómo probar el sistema

Ejecuta el script de ejemplo incluido:

```bash
python examples/new_function_system_example.py
```

## Comparación con el sistema anterior

| Característica | Sistema anterior | Nuevo sistema |
|----------------|-----------------|---------------|
| Definiciones | Distribuidas en cada clase | Centralizadas en un archivo |
| Registro | Mediante SkillManager | Mediante FunctionManager |
| Extensibilidad | Requiere modificar varios archivos | Solo añadir la función y su definición |
| Mantenimiento | Más complejo | Más sencillo y organizado |
| Dependencias | Integrado con el sistema de habilidades | Independiente y más modular |

## Notas importantes

- Es necesario configurar las API keys en el archivo `.env` o como variables de entorno
- Para la búsqueda en Google, se requiere una API key de Serper.dev
- El sistema utiliza simulación para los datos del clima por defecto, pero se puede conectar a una API real
