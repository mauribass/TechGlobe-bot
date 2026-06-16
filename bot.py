"""
Bot de Soporte Técnico Nivel 1 — TechGlobe SRL
"""

import csv
import re   # permite buscar patrones dentro de texto
import logging  # permite registrar lo que va pasando mientras el programa corre, similar a un print()
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============================================================
# CONFIGURACIÓN
# ============================================================

TOKEN = "8677218997:AAEXEKDQqgjDGHsFVEgSUepqya_5isa76LY"  # Reemplazá con tu token real

ARCHIVO_TICKETS = "tickets.csv"
ARCHIVO_SOLUCIONES = "soluciones.csv"

# ============================================================
# ESTADOS DE LA MÁQUINA DE ESTADOS (FSM)
# ============================================================

INICIO      = "INICIO"
NOMBRE      = "NOMBRE"
SECTOR      = "SECTOR"
TIPO        = "TIPO"
DESCRIPCION = "DESCRIPCION"
RESOLUCION  = "RESOLUCION"
FIN         = "FIN"

# ============================================================
# DICCIONARIO DE DATOS DE LA EMPRESA (Reglas de Negocio)
# ============================================================

# Lista oficial de sectores autorizados en TechGlobe SRL
SECTORES_AUTORIZADOS = [
    "Administración",
    "Ventas",
    "Desarrollo",
    "Logística",
    "Recursos Humanos"
]

CATEGORIAS = {
    "1️⃣ Hardware": "Hardware",
    "2️⃣ Software": "Software",
    "3️⃣ Red": "Red",
    "4️⃣ Otro": "Otro"
}

# ============================================================
# LOGGING
# ============================================================

# configuracion del sistema de registro de eventos (logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO # filtro de gravedad 
)

# ============================================================
# BASE DE DATOS — SOLUCIONES CONOCIDAS (Gateway 1)
# ============================================================

def cargar_soluciones() -> dict:
    # Carga el CSV de soluciones conocidas en un diccionario
    soluciones = {}
    try:
        with open(ARCHIVO_SOLUCIONES, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                soluciones[row["clave"].lower()] = row["solucion"]
    except FileNotFoundError:
        # Si el archivo no existe, registramos el aviso y devolvemos el diccionario vacío
        logging.warning(f"El archivo {ARCHIVO_SOLUCIONES} no fue encontrado. Se iniciará sin soluciones predefinidas.")
    return soluciones


def buscar_solucion(descripcion: str, soluciones: dict) -> str | None:
    """
    Gateway 1: ¿El problema es conocido?
    Busca palabras clave de la descripción en la base de datos.
    Retorna la solución si existe, None si no existe.
    """
    descripcion_lower = descripcion.lower()
    for clave, solucion in soluciones.items():
        if clave in descripcion_lower:
            return solucion
    return None

# ============================================================
# BASE DE DATOS — TICKETS (Persistencia)
# ============================================================

def inicializar_csv():
    # Crea el archivo de tickets con su encabezado solo si no existe
    try:
        # Intentamos abrir en modo 'x' (exclusive creation). Fallará si el archivo ya existe.
        with open(ARCHIVO_TICKETS, "x", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ticket_id", "chat_id", "nombre", "sector",
                "tipo_problema", "descripcion", "resuelto",
                "derivado_it", "fecha_hora"
            ])
            logging.info(f"Archivo {ARCHIVO_TICKETS} creado exitosamente con sus encabezados.")
    except FileExistsError:
        # Si el archivo ya existía, no hacemos nada y el flujo continúa normalmente
        logging.info(f"El archivo {ARCHIVO_TICKETS} ya existe. No es necesario inicializarlo.")


def obtener_proximo_id() -> int:
    """Genera el próximo ID de ticket de forma autoincremental leyendo el archivo mediante try/except."""
    try:
        with open(ARCHIVO_TICKETS, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            filas = list(reader)
            return len(filas)  # encabezado + filas existentes = próximo id
    except FileNotFoundError:
        # Si por alguna razón el archivo no existe todavía, el primer ID será 1
        return 1


def registrar_ticket(datos: dict):
    """Guarda un ticket en el CSV (modo append)."""
    with open(ARCHIVO_TICKETS, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datos["ticket_id"], datos["chat_id"], datos["nombre"],
            datos["sector"], datos["tipo_problema"], datos["descripcion"],
            datos["resuelto"], datos["derivado_it"], datos["fecha_hora"]
        ])

# ============================================================
# VALIDACIONES — CAMINO INFELIZ
# ============================================================

def validar_nombre(texto: str) -> bool:
    """Solo letras y espacios, mínimo 2 caracteres."""
    return bool(re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]{2,}$", texto.strip())) # caracteres permitidos


def validar_sector(texto: str) -> bool:
    """
    Validación de regla de negocio dinámica.
    Verifica si el sector ingresado existe dentro de los sectores autorizados corporativos.
    """
    texto_limpio = texto.strip().lower()
    # Compara contra la lista oficial pasando todo a minúsculas para evitar fallas de tipeo menores
    return any(sector.lower() == texto_limpio for sector in SECTORES_AUTORIZADOS)

def obtener_nombre_sector_real(texto: str) -> str:
    """Devuelve el formato estético original del sector (ej: de 'ventas' a 'Ventas')."""
    texto_limpio = texto.strip().lower()
    for sector in SECTORES_AUTORIZADOS:
        if sector.lower() == texto_limpio:
            return sector
    return texto  # Por seguridad


def validar_tipo(texto: str) -> bool:
    """Debe ser 1, 2, 3 o 4."""
    return texto.strip() in CATEGORIAS


def validar_descripcion(texto: str) -> bool:
    """Mínimo 10 caracteres."""
    return len(texto.strip()) >= 10

# ============================================================
# MANEJADORES — LÓGICA DE LA FSM
# ============================================================
# async es obligatorio para la libreria de telegram, Define que la función es asincrónica
# Significa que el bot puede procesar los mensajes de muchos usuarios al mismo tiempo sin quedarse "congelado" esperando a que responda uno solo.

async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Evento: /start recibido
    Transición: CUALQUIER ESTADO → INICIO → NOMBRE
    Acción: Reinicia sesión y solicita nombre
    """
    # Reinicia el estado (camino infeliz: /start en medio del flujo)
    context.user_data.clear()
    context.user_data["estado"] = NOMBRE

    # traduccion de await: "Envía este mensaje por internet a los servidores de Telegram y, mientras esperás la confirmación de recibido, seguí atendiendo a otros usuarios".
    await update.message.reply_text(
        "¡Bienvenido al soporte técnico de *TechGlobe SRL*!\n\n"
        "Voy a ayudarte a registrar y resolver tu incidente técnico.\n\n"
        "Para comenzar, ¿cuál es tu *nombre completo*?",
        parse_mode="Markdown", # aplica estilo de texto
        reply_markup=ReplyKeyboardRemove() 
    )


async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador principal de la FSM."""
    texto = update.message.text.strip()
    estado = context.user_data.get("estado", INICIO)

    # ── Estado: NOMBRE ──────────────────────────────────────
    if estado == NOMBRE:
        if not validar_nombre(texto):
            await update.message.reply_text(
                "⚠️ El nombre solo puede contener letras y espacios.\n"
                "Por favor ingresá tu nombre nuevamente:"
            )
            return

        context.user_data["nombre"] = texto
        context.user_data["estado"] = SECTOR

        # Teclado dinámico con la lista de sectores autorizados corporativos
        botones_sectores = [[sec] for sec in SECTORES_AUTORIZADOS]
        teclado_sectores = ReplyKeyboardMarkup(botones_sectores, one_time_keyboard=True, resize_keyboard=True)

        await update.message.reply_text(
            f"Gracias, *{texto}*.\n\n"
            "¿En qué *sector* trabajás? Seleccioná una opción de la lista corporativa:",
            parse_mode="Markdown",
            reply_markup=teclado_sectores
        )

    # ── Estado: SECTOR ──────────────────────────────────────
    elif estado == SECTOR:
        if not validar_sector(texto):
            # Camino infeliz: El sector no pertenece a la organización
            botones_sectores = [[sec] for sec in SECTORES_AUTORIZADOS]
            teclado_sectores = ReplyKeyboardMarkup(botones_sectores, one_time_keyboard=True, resize_keyboard=True)
            
            await update.message.reply_text(
                "⚠️ El sector ingresado no está registrado en la base de datos de TechGlobe SRL.\n"
                "Por favor, seleccioná un sector válido usando los botones:",
                reply_markup=teclado_sectores
            )
            return

        # Guardamos el formato prolijo del sector
        sector_real = obtener_nombre_sector_real(texto)
        context.user_data["sector"] = sector_real
        context.user_data["estado"] = TIPO

        # Configuración del teclado de categorías
        botones_tipo = [
            ["1️⃣ Hardware", "2️⃣ Software"],
            ["3️⃣ Red", "4️⃣ Otro"]
        ]
        teclado_tipo = ReplyKeyboardMarkup(botones_tipo, one_time_keyboard=True, resize_keyboard=True)

        await update.message.reply_text(
            f"Sector validado: *{sector_real}*.\n\n"
            "¿Qué tipo de problema tenés? Seleccioná una opción con los botones de abajo:",
            parse_mode="Markdown",
            reply_markup=teclado_tipo
        )

    # ── Estado: TIPO ────────────────────────────────────────
    elif estado == TIPO:
        if not validar_tipo(texto):
            botones_tipo = [["1️⃣ Hardware", "2️⃣ Software"], ["3️⃣ Red", "4️⃣ Otro"]]
            teclado_tipo = ReplyKeyboardMarkup(botones_tipo, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "⚠️ Opción no válida. Por favor, utilizá los botones en pantalla para elegir la categoría:",
                reply_markup=teclado_tipo
            )
            return

        context.user_data["tipo"] = CATEGORIAS[texto]
        context.user_data["estado"] = DESCRIPCION
        
        await update.message.reply_text(
            f"Categoría seleccionada: *{CATEGORIAS[texto]}*.\n\n"
            "Describí brevemente el problema que tenés (mínimo 10 caracteres):",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )

    # ── Estado: DESCRIPCION ─────────────────────────────────
    elif estado == DESCRIPCION:
        if not validar_descripcion(texto):
            await update.message.reply_text(
                "⚠️ La descripción es muy breve.\n"
                "Por favor describí el problema con más detalle (mínimo 10 caracteres):"
            )
            return

        context.user_data["descripcion"] = texto

        botones_resolucion = [["🟢 Sí", "🔴 No"]]
        teclado_resolucion = ReplyKeyboardMarkup(botones_resolucion, one_time_keyboard=True, resize_keyboard=True)

        soluciones = cargar_soluciones()
        solucion = buscar_solucion(texto, soluciones)

        if solucion:
            context.user_data["solucion_encontrada"] = True
            context.user_data["estado"] = RESOLUCION
            await update.message.reply_text(
                "Encontré una solución para tu problema:\n\n"
                f"*{solucion}*\n\n"
                "¿Pudiste resolver el problema con estas instrucciones?",
                parse_mode="Markdown",
                reply_markup=teclado_resolucion
            )
        else:
            context.user_data["solucion_encontrada"] = False
            context.user_data["estado"] = RESOLUCION
            await update.message.reply_text(
                "No encontré una solución estándar para tu problema en la base de datos.\n\n"
                "¿Pudiste resolver el problema por tu cuenta?",
                parse_mode="Markdown",
                reply_markup=teclado_resolucion
            )

    # ── Estado: RESOLUCION ──────────────────────────────────
    elif estado == RESOLUCION:
        respuesta = texto.lower()

        if "sí" in respuesta or "si" in respuesta or respuesta == "🟢 sí":
            resuelto = True
        elif "no" in respuesta or respuesta == "🔴 no":
            resuelto = False
        else:
            botones_resolucion = [["🟢 Sí", "🔴 No"]]
            teclado_resolucion = ReplyKeyboardMarkup(botones_resolucion, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "⚠️ Por favor, respondé utilizando los botones de la pantalla:",
                parse_mode="Markdown",
                reply_markup=teclado_resolucion
            )
            return

        ticket_id = obtener_proximo_id()
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M")

        datos_ticket = {
            "ticket_id":    ticket_id,
            "chat_id":      update.effective_chat.id,
            "nombre":       context.user_data.get("nombre", ""),
            "sector":       context.user_data.get("sector", ""),
            "tipo_problema": context.user_data.get("tipo", ""),
            "descripcion":  context.user_data.get("descripcion", ""),
            "resuelto":     resuelto,
            "derivado_it":  not resuelto,
            "fecha_hora":   fecha_hora
        }

        registrar_ticket(datos_ticket)

        if resuelto:
            await update.message.reply_text(
                f"*¡Perfecto!* El ticket #{ticket_id} fue cerrado como resuelto.\n\n"
                f"Fecha: {fecha_hora}\n"
                f"Empleado: {datos_ticket['nombre']} — {datos_ticket['sector']}\n"
                f"Tipo: {datos_ticket['tipo_problema']}\n\n"
                "Gracias por usar el soporte de TechGlobe. Si tenés otro problema, escribí /start.",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text(
                f"*Ticket #{ticket_id} generado y derivado al equipo de IT.*\n\n"
                f"Fecha: {fecha_hora}\n"
                f"Empleado: {datos_ticket['nombre']} — {datos_ticket['sector']}\n"
                f"Tipo: {datos_ticket['tipo_problema']}\n"
                f"Descripción: {datos_ticket['descripcion']}\n\n"
                "Un técnico de IT se pondrá en contacto a la brevedad. Si tenés otro problema, escribí /start.",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )

        context.user_data["estado"] = FIN

    # ── Estado: FIN o INICIO (sin /start) ───────────────────
    else:
        if estado == FIN:
            # Transición automática: FIN → NOMBRE (Reseteo amigable)
            context.user_data.clear()
            context.user_data["estado"] = NOMBRE
            
            await update.message.reply_text(
                "*Detecté que iniciaste una nueva consulta.*\n\n"
                "Vamos a registrar otro incidente técnico de cero.\n\n"
                "Para comenzar, ¿cuál es tu *nombre completo*?",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            # Manejo del estado INICIO real (cuando entran al bot sin mandar /start por primera vez)
            await update.message.reply_text(
                "¡Hola! Para iniciar el proceso de soporte técnico, por favor presioná o escribí /start.",
                reply_markup=ReplyKeyboardRemove()
            )

# ============================================================
# MAIN — INICIALIZACIÓN DEL BOT
# ============================================================

def main():
    inicializar_csv()

    app = Application.builder().token(TOKEN).build()

    # Registrar manejadores
    app.add_handler(CommandHandler("start", comando_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))

    print("Bot de TechGlobe iniciado. Presioná Ctrl+C para detenerlo.")
    app.run_polling()


if __name__ == "__main__":
    main()