import sys
import streamlit as st # ## CAMBIOS A STREAMLIT ## Importar Streamlit
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import datetime
import os
import json
import pandas as pd # ## CAMBIOS A STREAMLIT ## Para manejar los datos en tablas de Streamlit

# --- CONFIGURACIÓN ---
SPREADSHEET_ID = '1T5Sm5evPLAOtY9pTzLoihtBgrGoX0dZGUOjpIBq2Xeg'
RANGE_NAME = 'Respuestas de formulario 1!A1:J'

# --- RUTA DEL ARCHIVO DE CREDENCIALES ---
# NOTA CRÍTICA: En producción (en GoDaddy), NO DEBES usar una ruta local como 'C:\Users\...'.
# Debes subir 'credentials.json' junto a tu aplicación y referenciarla de forma relativa.
# Por ejemplo, si lo subes a la misma carpeta de 'streamlit_app.py':
SERVICE_ACCOUNT_FILE = 'credentials.json' # ## CAMBIOS A STREAMLIT ## Ajustado para ruta relativa en servidor

# Índices de columnas (Python es base 0)
COL_TIMESTAMP = 0
COL_NOMBRE = 1
COL_RUN = 2
COL_TELEFONO = 3
COL_EMAIL = 4
COL_TORRE = 5
COL_DEPARTAMENTO = 6
COL_FECHA = 7
COL_HORA = 8
COL_ESTADO = 9

# ## CAMBIOS A STREAMLIT ##
# Las funciones de autenticación y carga de datos pueden mantenerse muy similares.
# Ya no necesitas una clase QWidget ni métodos init_ui, apply_dark_theme, etc.
# Streamlit maneja la UI por ti.

@st.cache_resource # ## CAMBIOS A STREAMLIT ## Decorador para cachear el servicio de Google
def authenticate_google_sheets():
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            st.error(f"Error: El archivo de credenciales no se encontró en la ruta: {SERVICE_ACCOUNT_FILE}")
            return None

        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Error de autenticación con Google Sheets: {e}")
        return None

@st.cache_data(ttl=30) # ## CAMBIOS A STREAMLIT ## Decorador para cachear datos y refrescar cada 30 segundos
def load_reservations_data():
    service = authenticate_google_sheets()
    if not service:
        return pd.DataFrame() # Devuelve un DataFrame vacío si la autenticación falla

    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
        values = result.get('values', [])

        if not values:
            st.info("No se encontraron datos en la hoja de cálculo.")
            return pd.DataFrame()

        # ## CAMBIOS A STREAMLIT ##
        # Convertir a DataFrame de Pandas para facilitar el manejo y la visualización en Streamlit
        # Asumiendo que la primera fila son los encabezados
        df = pd.DataFrame(values[1:], columns=values[0] if values else [])
        return df

    except HttpError as err:
        error_message = f"Ocurrió un error con la API de Google Sheets: {err}"
        if err.resp.status == 404:
            error_message = f"La hoja '{SPREADSHEET_ID}' o el rango '{RANGE_NAME}' no se encontró. Verifica el ID y el nombre de la hoja."
        elif err.resp.status == 403:
            sa_email = "Desconocido"
            try:
                with open(SERVICE_ACCOUNT_FILE, 'r') as f:
                    creds_data = json.load(f)
                    sa_email = creds_data.get('client_email', 'Desconocido')
            except Exception:
                pass
            error_message = f"No tienes permisos para acceder a la hoja. Asegúrate de haber compartido la hoja con la cuenta de servicio: {sa_email}."
        st.error(f"Error al cargar datos: {error_message}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Ocurrió un error general al cargar las reservas: {e}")
        return pd.DataFrame()

# ## CAMBIOS A STREAMLIT ##
# La lógica principal de la aplicación Streamlit

def main():
    st.set_page_config(layout="wide", page_title="Visor de Reservas - Tiempo Real") # Configura el diseño de la página
    st.title("Sistema de Visor de Reservas")

    # ## CAMBIOS A STREAMLIT ##
    # Aplicar un tema oscuro con estilos de Streamlit (no PyQt5 CSS)
    # Streamlit ya tiene temas claros/oscuros. Puedes añadir CSS personalizado si lo deseas.
    st.markdown(
        """
        <style>
        .stButton>button {
            background-color: #4CAF50; /* Verde */
            color: white;
            border-radius: 8px;
            padding: 8px 15px;
            margin: 5px;
            border: none;
        }
        .stButton>button:hover {
            background-color: #45a049;
        }
        .stTextInput>div>div>input, .stDateInput>div>div>input, .stSelectbox>div>div>div {
            background-color: #252525;
            border: 1px solid #555555;
            border-radius: 5px;
            padding: 6px;
            color: #FFFFFF;
        }
        /* Estilos para el texto de las tablas si es necesario, Streamlit maneja mucho esto */
        </style>
        """,
        unsafe_allow_html=True
    )

    # Controles de Filtro
    st.subheader("Filtros de Búsqueda")
    col1, col2, col3, col4 = st.columns([1, 1, 2, 0.5]) # Distribución de columnas para filtros

    with col1:
        st.write("Fecha:")
        date_filter = st.date_input("Selecciona una fecha", datetime.date.today())

    with col2:
        st.write("Estado:")
        status_filter = st.selectbox("Selecciona un estado",
                                     ["Todos", "CONFIRMADA", "RECHAZADA - Slot ocupado", "ERROR - Fecha inválida"])

    with col3:
        st.write("Buscar por Nombre, RUN o Email:")
        search_box = st.text_input("Buscar", placeholder="Nombre, RUN o Email")

    with col4:
        st.write("") # Espacio para alinear el botón
        if st.button("Actualizar Datos"):
            st.cache_data.clear() # Limpia la caché para forzar la recarga
            st.success("Datos actualizados manualmente.")

    # Cargar todos los datos
    all_reservations_df = load_reservations_data()

    if not all_reservations_df.empty:
        # Aplicar filtros
        filtered_df = all_reservations_df.copy()

        # Filtrar por fecha
        # Asegúrate de que la columna 'Fecha' en tu DF de Pandas tenga el formato correcto para comparar
        # Asumiendo que 'Fecha' en Google Sheets está en 'dd/MM/yyyy'
        if 'Fecha' in filtered_df.columns:
            # Convertir la columna 'Fecha' del DataFrame a formato datetime para una comparación robusta
            try:
                # Intenta inferir el formato, si falla, usa el formato explícito
                filtered_df['Fecha_dt'] = pd.to_datetime(filtered_df['Fecha'], format='%d/%m/%Y', errors='coerce')
                selected_date_dt = pd.to_datetime(date_filter).date()
                filtered_df = filtered_df[filtered_df['Fecha_dt'].dt.date == selected_date_dt]
            except Exception as e:
                st.warning(f"No se pudo filtrar por fecha debido a un error de formato: {e}. Asegúrate que la columna 'Fecha' en tu Google Sheet esté en 'dd/MM/yyyy'.")


        # Filtrar por estado
        if status_filter != "Todos" and 'Estado de la reserva' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Estado de la reserva'].str.strip().str.upper() == status_filter.upper()]

        # Filtrar por búsqueda
        if search_box:
            search_text_lower = search_box.lower()
            # Asegúrate que las columnas existan antes de intentar acceder a ellas
            mask = False
            if 'Nombre Completo' in filtered_df.columns:
                mask |= filtered_df['Nombre Completo'].astype(str).str.lower().str.contains(search_text_lower, na=False)
            if 'RUN' in filtered_df.columns:
                mask |= filtered_df['RUN'].astype(str).str.lower().str.contains(search_text_lower, na=False)
            if 'Correo Electrónico' in filtered_df.columns:
                mask |= filtered_df['Correo Electrónico'].astype(str).str.lower().str.contains(search_text_lower, na=False)
            filtered_df = filtered_df[mask]

        # Mostrar tabla de reservas
        st.subheader("Reservas Actuales")
        # ## CAMBIOS A STREAMLIT ## st.dataframe es la forma de mostrar tablas
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        # Mostrar mensaje de cuantas reservas se muestran
        st.info(f"Mostrando {len(filtered_df)} de {len(all_reservations_df)} reservas.")

    else:
        st.info("No hay datos para mostrar o hubo un error al cargar.")

if __name__ == '__main__':
    main()
