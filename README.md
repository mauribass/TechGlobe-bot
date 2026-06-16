# Bot de Soporte Técnico Nivel 1 — TechGlobe SRL

Bot de Telegram que automatiza el proceso de soporte técnico nivel 1 para TechGlobe SRL. Permite a los empleados reportar incidentes técnicos, recibir soluciones estándar automáticas y generar tickets derivados al equipo de IT, todo desde Telegram.

---

## Requisitos previos

- Python 3.10 o superior
- Una cuenta de Telegram
- Un token de bot creado con [@BotFather](https://t.me/BotFather)

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/techglobe-soporte-bot.git
cd techglobe-soporte-bot
```

### 2. Crear un entorno virtual (recomendado)

```bash
python -m venv venv

# En Windows:
venv\Scripts\activate

# En Linux/macOS:
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install python-telegram-bot
```

### 4. Configurar el token

Abrí el archivo `bot.py` y reemplazá la línea:

```python
TOKEN = "TU_TOKEN_AQUI"
```

con el token que te dio BotFather al crear tu bot.

---

## Archivos necesarios

El bot necesita dos archivos CSV en la misma carpeta que `bot.py`:

### `soluciones.csv` — Base de datos de soluciones conocidas (Gateway 1)

Creá este archivo con el siguiente formato:

```
clave,solucion
excel,Cerrá y volvé a abrir Excel. Si el problema persiste, reparalo desde Panel de Control > Programas.
impresora,Verificá que la impresora esté encendida y conectada. Intentá imprimir una página de prueba desde Dispositivos e impresoras.
internet,Reiniciá el router desenchufándolo 30 segundos. Si el problema persiste, contactá a tu proveedor de internet.
contraseña,Utilizá el portal de autoservicio en intranet.techglobe.com/reset para restablecer tu contraseña.
pantalla,Verificá que el cable de video esté bien conectado. Intentá con otro puerto HDMI/VGA del monitor.
```

Podés agregar tantas filas como quieras. La columna `clave` es la palabra que el bot buscará dentro de la descripción del usuario.

### `tickets.csv` — Base de datos de tickets (se crea automáticamente)

Este archivo lo genera el bot automáticamente al iniciarse. No necesitás crearlo manualmente.

---

## Ejecución

```bash
python bot.py
```

Deberías ver en la consola:

```
Bot de TechGlobe iniciado. Presioná Ctrl+C para detenerlo.
```

Para detener el bot, presioná `Ctrl+C`.

---

## Uso del bot

1. Buscá tu bot en Telegram por su nombre de usuario.
2. Enviá el comando `/start` para iniciar el proceso.
3. Seguí las instrucciones del bot: nombre → sector → tipo de problema → descripción.
4. El bot intentará resolver el problema automáticamente. Si no puede, generará un ticket para el equipo de IT.

---

## Estructura del proyecto

```
techglobe-soporte-bot/
│
├── bot.py               # Código principal del bot
├── Dockerfile           # Imagen Docker para empaquetar y ejecutar el bot
├── requirements.txt     # Dependencias de Python
├── soluciones.csv       # Base de datos de soluciones conocidas (crear manualmente)
├── tickets.csv          # Registro de tickets (se genera automáticamente)
└── README.md            # Este archivo
```

---

## Estructura del `tickets.csv`

Cada ticket registrado contiene los siguientes campos:

| Campo | Descripción |
|---|---|
| `ticket_id` | Número único autoincremental |
| `chat_id` | ID del chat de Telegram |
| `nombre` | Nombre del empleado |
| `sector` | Sector de la empresa |
| `tipo_problema` | Hardware / Software / Red / Otro |
| `descripcion` | Descripción del incidente |
| `resuelto` | True si fue resuelto con solución estándar |
| `derivado_it` | True si fue escalado al equipo de IT |
| `fecha_hora` | Fecha y hora de creación del ticket |

---

## Sectores habilitados

El bot valida que el empleado pertenezca a uno de los siguientes sectores de TechGlobe SRL:

- Administración
- Ventas
- Desarrollo
- Logística
- Recursos Humanos

---

## Despliegue con Docker

El proyecto incluye un `Dockerfile` para empaquetar y ejecutar el bot en un contenedor, sin necesidad de instalar Python ni dependencias en la máquina host.

### Requisitos previos

- [Docker](https://www.docker.com/get-started) instalado en el sistema.

### 1. Crear el archivo `requirements.txt`

Antes de construir la imagen, asegurate de tener un archivo `requirements.txt` en la raíz del proyecto con el siguiente contenido:

```
python-telegram-bot
```

### 2. Configurar el token

Editá `bot.py` y reemplazá el token antes de construir la imagen:

```python
TOKEN = "TU_TOKEN_AQUI"
```

### 3. Construir la imagen

Desde la raíz del proyecto, ejecutá:

```bash
docker build -t techglobe-bot .
```

Esto descarga la imagen base de Python, instala las dependencias y copia el código dentro del contenedor.

### 4. Ejecutar el contenedor

```bash
docker run -d --name soporte-techglobe techglobe-bot
```

| Flag | Descripción |
|---|---|
| `-d` | Ejecuta el contenedor en segundo plano (modo detached) |
| `--name soporte-techglobe` | Asigna un nombre al contenedor para identificarlo fácilmente |

### 5. Verificar que el bot está corriendo

```bash
docker logs soporte-techglobe
```

Deberías ver en los logs:

```
Bot de TechGlobe iniciado. Presioná Ctrl+C para detenerlo.
```

### 6. Detener y eliminar el contenedor

```bash
docker stop soporte-techglobe
docker rm soporte-techglobe
```

### Sobre la persistencia de datos con Docker

Por defecto, el archivo `tickets.csv` se genera **dentro del contenedor** y se pierde si el contenedor es eliminado. Para conservar los tickets entre reinicios, montá un volumen local:

```bash
docker run -d --name soporte-techglobe \
  -v $(pwd)/tickets.csv:/app/tickets.csv \
  -v $(pwd)/soluciones.csv:/app/soluciones.csv \
  techglobe-bot
```

Esto mantiene ambos archivos CSV en tu máquina local y el contenedor los lee y escribe directamente allí.

> **Nota para Windows (PowerShell):** reemplazá `$(pwd)` por `${PWD}`.

---

## Posibles errores y soluciones

| Error | Causa probable | Solución |
|---|---|---|
| `Unauthorized` al iniciar | Token incorrecto | Verificá el token en `bot.py` |
| `ModuleNotFoundError: telegram` | Librería no instalada | Ejecutá `pip install python-telegram-bot` |
| El archivo `soluciones.csv` no existe | No fue creado manualmente | Crealo según el formato indicado arriba |
| El bot no responde | El proceso fue detenido | Volvé a ejecutar `python bot.py` |
| `docker: command not found` | Docker no está instalado | Instalalo desde https://www.docker.com/get-started |
| `COPY failed: requirements.txt not found` | Falta el archivo `requirements.txt` | Crealo con el contenido indicado en la sección Docker |
| Los tickets se pierden al reiniciar el contenedor | Los CSV están dentro del contenedor | Usá la opción `-v` para montar volúmenes locales |

---

## Notas técnicas

- El bot utiliza una **Máquina de Estados Finito (FSM)** para gestionar el flujo conversacional de cada usuario de forma independiente.
- La persistencia se implementa mediante archivos CSV, sin necesidad de servidor de base de datos.
- El manejo de errores de entrada (camino infeliz) está integrado en cada paso del flujo.
- El bot puede atender múltiples usuarios simultáneamente gracias al uso de funciones `async`.

---

## Tecnologías utilizadas

- **Python 3.x**
- **python-telegram-bot** — Wrapper de la API de Telegram
- **CSV** — Persistencia de datos
- **Telegram Bot API**
- **Docker** — Empaquetado y despliegue del bot en contenedor
