# Sistema Inteligente de Llamadas a Funciones para el Asistente Virtual

Este documento describe el sistema inteligente de llamadas a funciones implementado en el asistente personal virtual, que permite al asistente decidir automáticamente cuándo necesita llamar a funciones específicas para responder a las consultas del usuario.

## Características principales

- **Decisión automática**: El asistente determina cuándo necesita información externa para responder adecuadamente.
- **Ejecución transparente**: El sistema maneja la ejecución de funciones y la incorporación de sus resultados sin intervención del usuario.
- **Extensible**: Diseñado para facilitar la adición de nuevas funciones y capacidades.
- **Sistema basado en herramientas de OpenAI**: Utiliza la funcionalidad de herramientas/funciones del API de OpenAI.

## Componentes del sistema

### 1. FunctionRegistry

Clase encargada de registrar y mantener un catálogo de funciones disponibles con sus definiciones en formato compatible con la API de OpenAI.

```python
function_registry = FunctionRegistry()
function_registry.register_function(function_def, handler)
```

### 2. FunctionCallingManager

Gestiona el proceso de llamadas a funciones, incluyendo la preparación de definiciones para la API, ejecución de funciones llamadas y formateo de resultados.

```python
function_manager = FunctionCallingManager(config, event_bus, function_registry)
```

### 3. Implementaciones de funciones

Clases específicas que implementan la lógica de negocio para cada función que puede ser llamada por el asistente:

- `WeatherFunction`: Obtiene información del clima para una ubicación
- `ReminderFunction`: Gestiona la creación de recordatorios

## Flujo de trabajo

1. Se registran las funciones disponibles en el sistema, con su definición y handler.
2. El usuario realiza una consulta al asistente.
3. La consulta se envía al modelo de IA junto con las definiciones de funciones disponibles.
4. El modelo decide si necesita llamar a alguna función para responder adecuadamente.
5. Si el modelo decide llamar a una función:
   - El sistema ejecuta la función con los parámetros proporcionados por el modelo
   - Los resultados se envían de vuelta al modelo
   - El modelo genera una respuesta final incorporando la información obtenida
6. Si el modelo no necesita llamar a ninguna función, responde directamente.

## Ejemplo de uso

```python
# Crear instancias de funciones
weather_function = WeatherFunction(config)
reminder_function = ReminderFunction(config)

# Registrar funciones en el procesador de IA
ai_processor.register_function(
    weather_function.get_weather_function_definition(),
    weather_function.get_weather
)

ai_processor.register_function(
    reminder_function.get_reminder_function_definition(),
    reminder_function.create_reminder
)

# El asistente ahora puede usar estas funciones automáticamente cuando sea necesario
ai_processor.process_input("¿Cómo está el clima en Barcelona?")
ai_processor.process_input("Crea un recordatorio para llamar a mamá mañana a las 5 PM")
ai_processor.process_input("¿Qué es la inteligencia artificial?")  # No requiere función
```

## Cómo probar el sistema

Ejecuta el script de ejemplo que demuestra el funcionamiento del sistema:

```
python examples/function_calling_example.py
```

Este ejemplo muestra cómo el asistente decide automáticamente cuándo necesita llamar a una función y cuándo puede responder directamente basado en su conocimiento.

## Cómo extender el sistema

Para añadir una nueva función al sistema:

1. Crea una nueva clase que implemente la función (similar a `WeatherFunction` o `ReminderFunction`).
2. Implementa un método para obtener la definición de la función en formato OpenAI.
3. Implementa el handler de la función que realizará la lógica de negocio.
4. Registra la función en el procesador de IA.

## Requisitos

- Python 3.8 o superior
- OpenAI Python SDK (versión 1.0 o superior)
- Otras dependencias definidas en `requirements.txt`

## Notas importantes

- Asegúrate de tener configurada la variable de entorno `OPENAI_API_KEY` con tu clave de API de OpenAI.
- Para funciones que requieran recursos externos (APIs web, bases de datos, etc.), asegúrate de manejar apropiadamente los errores y tiempos de espera.
- El sistema está diseñado para ser no bloqueante, utilizando el patrón de eventos para manejar las respuestas asíncronas.
