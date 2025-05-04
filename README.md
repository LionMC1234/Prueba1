# Asistente Personal Virtual Inteligente

Un asistente personal virtual con capacidades avanzadas de procesamiento de lenguaje natural, reconocimiento de voz y llamadas a funciones inteligentes.

## Características principales

- Procesamiento de lenguaje natural utilizando GPT-4o de OpenAI
- Reconocimiento y síntesis de voz
- Habilidades específicas como consulta del clima, calendario y recordatorios
- **Nuevo: Sistema inteligente de llamadas a funciones**
- Bus de eventos para comunicación entre componentes
- Arquitectura modular y extensible

## Nuevo: Sistema inteligente de llamadas a funciones

Ahora el asistente puede tomar decisiones automáticas sobre cuándo necesita llamar a funciones específicas para responder adecuadamente a las consultas del usuario. Este sistema permite:

- Detección automática de cuándo se necesita información externa
- Ejecución transparente de funciones con los parámetros adecuados
- Generación de respuestas naturales incorporando los resultados de las funciones

Lee más sobre esta funcionalidad en [README_FUNCTION_CALLING.md](README_FUNCTION_CALLING.md)

## Estructura del proyecto

```
.
├── assistant/          # Módulos principales del asistente
│   ├── core/           # Componentes centrales
│   ├── modules/        # Módulos funcionales
│   ├── utils/          # Utilidades comunes
│   └── skills/         # Habilidades externas (plugins)
├── examples/           # Ejemplos de uso
├── config.json         # Configuración principal
├── main.py             # Punto de entrada principal
└── requirements.txt    # Dependencias
```

## Módulos principales

- **AssistantManager**: Coordina todos los componentes del asistente
- **AIProcessor**: Gestiona la comunicación con modelos de lenguaje (OpenAI)
- **SkillManager**: Administra las habilidades disponibles
- **VoiceInputManager**: Maneja el reconocimiento de voz
- **VoiceOutputManager**: Gestiona la síntesis de voz
- **FunctionCallingManager**: Nuevo sistema para la gestión de llamadas a funciones

## Habilidades y funciones disponibles

- **Clima**: Consulta información meteorológica
- **Hora/Fecha**: Proporciona información sobre la hora y fecha actual
- **Recordatorios**: Gestiona recordatorios y alarmas
- **Sistema**: Control del propio asistente

## Requisitos

- Python 3.8 o superior
- Clave API de OpenAI (para funciones de IA)
- Otras dependencias listadas en `requirements.txt`

## Instalación

1. Clonar el repositorio:
   ```
   git clone https://github.com/LionMC1234/Prueba1.git
   cd Prueba1
   ```

2. Instalar dependencias:
   ```
   pip install -r requirements.txt
   ```

3. Configurar variables de entorno:
   - Crear un archivo `.env` en la raíz del proyecto
   - Añadir `OPENAI_API_KEY=tu_clave_api_aqui`

## Uso

1. Ejecutar el asistente principal:
   ```
   python main.py
   ```

2. Probar el sistema de llamadas a funciones:
   ```
   python examples/function_calling_example.py
   ```

## Configuración

El archivo `config.json` contiene todas las configuraciones del asistente. Puedes ajustar:

- Configuración de IA (modelo, temperatura, etc.)
- Configuración de voz (entrada/salida)
- Configuración de habilidades específicas
- Parámetros del sistema

## Extendiendo el asistente

### Añadir nuevas habilidades

1. Crea una clase que herede de `Skill` en `assistant/skills/`
2. Implementa los métodos requeridos (initialize, process)
3. Registra comandos o patrones para tu habilidad

### Añadir nuevas funciones para llamadas automáticas

1. Crea una clase para la función (similar a `WeatherFunction`)
2. Implementa un método para obtener la definición de la función
3. Implementa el handler para la lógica de negocio
4. Registra la función en el procesador de IA

## Contribuyendo

Contribuciones son bienvenidas. Por favor, sigue estos pasos:

1. Haz fork del repositorio
2. Crea una rama para tu feature (`git checkout -b feature/amazing-feature`)
3. Haz commit de tus cambios (`git commit -m 'Add some feature'`)
4. Push a la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request
