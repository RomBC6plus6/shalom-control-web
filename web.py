from datetime import datetime
from urllib.parse import quote
import pandas as pd
import streamlit as st

# Configuración de la página Web
st.set_page_config(
    page_title="Gestión de Almacén Shalom", page_icon="📦", layout="wide"
)

st.title("Sistema de Control y Notificación de Almacén - Shalom")
st.write(
    "Herramienta web para la detección de paquetes retenidos y generación de avisos por WhatsApp."
)

# -----------------------------------------------------------------------------
# FUNCIONES DE PROCESAMIENTO (MOTOR BACKEND)
# -----------------------------------------------------------------------------

def cargar_datos(archivo):
    if archivo.name.endswith(".csv"):
        df = pd.read_csv(archivo)
    else:
        # Lee tanto .xlsx como .xls nativo de Shalom
        df = pd.read_excel(archivo)

    df.columns = df.columns.str.strip()
    df["F.SALIDA"] = pd.to_datetime(df["F.SALIDA"], errors="coerce")
    df["TELF. DESTINATARIO"] = (
        df["TELF. DESTINATARIO"].astype(str).str.replace(".0", "", regex=False).str.strip()
    )
    return df


def filtrar_datos(df, dias_min, dias_max):
    fecha_hoy = datetime.now()
    df["DIAS_EN_ALMACEN"] = (fecha_hoy - df["F.SALIDA"]).dt.days

    condicion = df["DIAS_EN_ALMACEN"] >= dias_min
    if dias_max is not None:
        condicion = condicion & (df["DIAS_EN_ALMACEN"] <= dias_max)

    return df[condicion].copy()


def generar_notificaciones(df_alertas):
    mensajes = []
    for _, fila in df_alertas.iterrows():
        # Mapeo ajustado al Excel real de Shalom
        nombre = fila["DESTINATARIO"]
        guia = fila["N° GUIA"]
        dias = fila["DIAS_EN_ALMACEN"]
        telefono = str(fila["TELF. DESTINATARIO"]).strip()

        if not telefono.startswith("51") and len(telefono) == 9:
            telefono_completo = f"51{telefono}"
        else:
            telefono_completo = telefono

        texto = (
            f"Hola {nombre}, te saludamos de Shalom. "
            f"Tu paquete con Nº de Guía {guia} tiene {dias} días en almacén. "
            f"Por favor acércate a recogerlo para evitar devoluciones."
        )

        mensaje_cod = quote(texto)
        enlace = f"https://wa.me/{telefono_completo}?text={mensaje_cod}"

        mensajes.append(
            {
                "Cliente": nombre,
                "Guía": guia,
                "Días Retenido": dias,
                "Teléfono": telefono,
                "Acción WhatsApp": enlace,
            }
        )
    return pd.DataFrame(mensajes)


# -----------------------------------------------------------------------------
# INTERFAZ GRÁFICA INTERACTIVA (STREAMLIT)
# -----------------------------------------------------------------------------

# Panel lateral de controles
st.sidebar.header("⚙️ Configuración del Filtro")
dias_minimos = st.sidebar.slider(
    "Días mínimos retenido:", min_value=1, max_value=60, value=15
)
usar_maximo = st.sidebar.checkbox("Definir límite máximo de días")

dias_maximos = None
if usar_maximo:
    dias_maximos = st.sidebar.number_input(
        "Días máximos:", min_value=dias_minimos + 1, value=30
    )

# Cargar archivo Excel (Soporte para .xls, .xlsx y .csv)
archivo_subido = st.file_uploader(
    "📁 Sube aquí el archivo descargado del sistema de Shalom (.xls, .xlsx o .csv)",
    type=["xls", "xlsx", "csv"],
)

if archivo_subido is not None:
    try:
        # Cargar y filtrar
        datos_originales = cargar_datos(archivo_subido)
        datos_filtrados = filtrar_datos(
            datos_originales, dias_minimos, dias_maximos
        )

        st.success(
            f"✅ Se encontraron **{len(datos_filtrados)} paquetes** con {dias_minimos} o más días de retención."
        )

        if len(datos_filtrados) > 0:
            reporte_mensajes = generar_notificaciones(datos_filtrados)

            # Mostrar tabla interactiva con botones clickeables en pantalla
            st.subheader("📋 Lista de Notificaciones Pendientes")

            st.dataframe(
                reporte_mensajes,
                column_config={
                    "Acción WhatsApp": st.column_config.LinkColumn(
                        "Notificar Cliente", display_text="📱 Enviar WhatsApp"
                    )
                },
                use_container_width=True,
                hide_index=True,
            )

    except Exception as e:
        st.error(f"❌ Ocurrió un error al procesar el archivo: {e}")
else:
    st.info("👆 Carga un archivo para comenzar la prueba en vivo.")
