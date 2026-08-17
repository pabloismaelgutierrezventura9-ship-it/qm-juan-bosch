import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# ====================== CONFIGURACIÓN ======================
st.set_page_config(
    page_title="QM Juan Bosch - Control de Caja",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados - alto contraste
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1a365d 0%, #2b6cb0 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
        color: white !important;
    }
    .main-header p {
        margin: 0.3rem 0 0 0;
        opacity: 0.95;
        font-size: 1rem;
        color: #e2e8f0 !important;
    }

    /* Métricas con alto contraste */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e0 !important;
        border-radius: 10px !important;
        padding: 14px 16px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    }
    div[data-testid="stMetric"] label {
        color: #2d3748 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #1a202c !important;
        font-weight: 700 !important;
        font-size: 1.35rem !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color: #2f855a !important;
    }

    /* Sidebar */
    div[data-testid="stSidebar"] {
        background-color: #edf2f7 !important;
    }
    div[data-testid="stSidebar"] * {
        color: #1a202c !important;
    }

    /* Login */
    .login-box {
        max-width: 420px;
        margin: 4rem auto;
        padding: 2rem;
        background: white;
        border-radius: 16px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        text-align: center;
    }

    /* Tablas más legibles */
    .stDataFrame {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

METODOS = ["Efectivo", "Banco Popular", "BHD", "Banco de Reservas"]

# ====================== CONEXIÓN SUPABASE ======================
@st.cache_resource
def get_supabase():
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error conectando a Supabase: {e}")
        return None

supabase = get_supabase()

# ====================== AUTENTICACIÓN ======================
def check_password():
    def password_entered():
        correct = st.secrets.get("APP_PASSWORD") or os.getenv("APP_PASSWORD") or "qm2026"
        if st.session_state.get("password") == correct:
            st.session_state["authenticated"] = True
            if "password" in st.session_state:
                del st.session_state["password"]
        else:
            st.session_state["authenticated"] = False

    if st.session_state.get("authenticated"):
        return True

    st.markdown("""
    <div class="login-box">
        <h1 style="color:#1a365d; margin-bottom:0.2rem;">📦 QM Juan Bosch</h1>
        <p style="color:#4a5568; margin-bottom:1.5rem;">Control de Caja · Sucursal Ciudad Juan Bosch</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.text_input("Contraseña de acceso", type="password", key="password", on_change=password_entered)
        st.caption("Ingresa la contraseña configurada para esta aplicación.")
    return False

# ====================== BASE DE DATOS ======================
def insert_payment(data: dict):
    if not supabase:
        st.error("No hay conexión a la base de datos. Revisa los Secrets de Streamlit.")
        return False
    try:
        supabase.table("payments").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

def get_payments(fecha_inicio: date = None, fecha_fin: date = None, metodo: str = None):
    if not supabase:
        return pd.DataFrame()
    try:
        query = supabase.table("payments").select("*").order("fecha", desc=True).order("hora", desc=True)
        if fecha_inicio:
            query = query.gte("fecha", fecha_inicio.isoformat())
        if fecha_fin:
            query = query.lte("fecha", fecha_fin.isoformat())
        if metodo and metodo != "Todos":
            query = query.eq("metodo", metodo)
        res = query.execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df["monto"] = pd.to_numeric(df["monto"])
            df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
        return df
    except Exception as e:
        st.error(f"Error al consultar: {e}")
        return pd.DataFrame()

def get_totales(df: pd.DataFrame):
    if df.empty:
        return {m: 0.0 for m in METODOS} | {"Total": 0.0}
    totales = df.groupby("metodo")["monto"].sum().to_dict()
    for m in METODOS:
        if m not in totales:
            totales[m] = 0.0
    totales["Total"] = float(df["monto"].sum())
    return totales

# ====================== REPORTES ======================
def generar_texto(df: pd.DataFrame, titulo: str, totales: dict) -> str:
    lineas = []
    lineas.append("=" * 62)
    lineas.append(f"  {titulo}")
    lineas.append("  QM Juan Bosch · Control de Caja")
    lineas.append(f"  Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    lineas.append("=" * 62)
    lineas.append("")
    lineas.append("RESUMEN POR MÉTODO DE PAGO")
    lineas.append("-" * 42)
    for m in METODOS:
        lineas.append(f"  {m:<22}: RD$ {totales.get(m, 0):>12,.2f}")
    lineas.append("-" * 42)
    lineas.append(f"  {'TOTAL GENERAL':<22}: RD$ {totales.get('Total', 0):>12,.2f}")
    lineas.append("")
    lineas.append("DETALLE DE PAGOS")
    lineas.append("-" * 62)
    if df.empty:
        lineas.append("  (Sin registros en el período)")
    else:
        for _, row in df.iterrows():
            ref = f" | Ref: {row['referencia']}" if pd.notna(row.get("referencia")) and row.get("referencia") else ""
            lineas.append(
                f"  {row['fecha']} | {str(row.get('hora', ''))[:8]} | "
                f"{str(row['nombre_cliente'])[:22]:<22} | "
                f"Cas: {str(row['casillero']):<8} | "
                f"{row['metodo']:<16} | "
                f"RD$ {row['monto']:>10,.2f}{ref}"
            )
    lineas.append("")
    lineas.append("=" * 62)
    lineas.append("Fin del reporte · QM Juan Bosch")
    return "\n".join(lineas)

def generar_pdf(df: pd.DataFrame, titulo: str, totales: dict) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Encabezado
    pdf.set_fill_color(26, 54, 93)
    pdf.rect(0, 0, 210, 28, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "QM Juan Bosch - Control de Caja", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, titulo, ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.ln(4)

    # Resumen
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "RESUMEN POR METODO DE PAGO", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for m in METODOS:
        pdf.cell(0, 7, f"{m}: RD$ {totales.get(m, 0):,.2f}", ln=True)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, f"TOTAL GENERAL: RD$ {totales.get('Total', 0):,.2f}", ln=True)
    pdf.ln(6)

    # Detalle
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "DETALLE DE PAGOS", ln=True)

    if df.empty:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, "(Sin registros en el periodo)", ln=True)
    else:
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(230, 240, 255)
        pdf.cell(22, 7, "Fecha", border=1, fill=True)
        pdf.cell(48, 7, "Cliente", border=1, fill=True)
        pdf.cell(22, 7, "Casillero", border=1, fill=True)
        pdf.cell(38, 7, "Metodo", border=1, fill=True)
        pdf.cell(25, 7, "Monto", border=1, fill=True)
        pdf.cell(35, 7, "Referencia", border=1, fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 8)
        for _, row in df.iterrows():
            pdf.cell(22, 6, str(row["fecha"]), border=1)
            pdf.cell(48, 6, str(row["nombre_cliente"])[:24], border=1)
            pdf.cell(22, 6, str(row["casillero"])[:12], border=1)
            pdf.cell(38, 6, str(row["metodo"])[:18], border=1)
            pdf.cell(25, 6, f"{row['monto']:,.2f}", border=1)
            ref = str(row.get("referencia") or "")[:18]
            pdf.cell(35, 6, ref, border=1)
            pdf.ln()

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "QM Juan Bosch · Sucursal Ciudad Juan Bosch · Republica Dominicana", align="C")

    # Asegurar bytes puros para Streamlit (compatible con fpdf2)
    try:
        output = pdf.output(dest="S")
    except TypeError:
        output = pdf.output()
    if isinstance(output, str):
        return output.encode("latin-1")
    return bytes(output)

# ====================== INTERFAZ ======================
def mostrar_header():
    st.markdown("""
    <div class="main-header">
        <h1>📦 QM Juan Bosch</h1>
        <p>Control de Caja · Sucursal Ciudad Juan Bosch · QM Courier</p>
    </div>
    """, unsafe_allow_html=True)

def main():
    if not check_password():
        return

    # Sidebar
    st.sidebar.markdown("### 📦 QM Juan Bosch")
    st.sidebar.caption("Control de Caja")
    st.sidebar.markdown("---")

    menu = st.sidebar.radio(
        "Menú principal",
        ["Registrar pago", "Dashboard / Cuadre", "Historial", "Configuración"],
        index=0
    )

    st.sidebar.markdown("---")
    st.sidebar.info("Versión 1.1 · Gratuita")

    # ---------- REGISTRAR PAGO ----------
    if menu == "Registrar pago":
        mostrar_header()
        st.subheader("➕ Registrar pago recibido")

        with st.form("form_pago", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                fecha = st.date_input("Fecha", value=date.today())
                nombre = st.text_input("Nombre del cliente *", placeholder="Ej: Juan Pedro")
                casillero = st.text_input("Número de casillero *", placeholder="Ej: 12345")
            with col2:
                monto = st.number_input("Monto (RD$) *", min_value=0.01, step=50.0, format="%.2f")
                metodo = st.selectbox("Método de pago *", METODOS)
                referencia = st.text_input("Referencia de transferencia (opcional)")

            notas = st.text_area("Notas (opcional)", height=70)
            submitted = st.form_submit_button("💾 Guardar pago", type="primary", use_container_width=True)

            if submitted:
                if not nombre.strip() or not casillero.strip() or monto <= 0:
                    st.error("Completa los campos obligatorios: Nombre, Casillero y Monto.")
                else:
                    data = {
                        "fecha": fecha.isoformat(),
                        "hora": datetime.now().strftime("%H:%M:%S"),
                        "nombre_cliente": nombre.strip(),
                        "casillero": casillero.strip(),
                        "monto": float(monto),
                        "metodo": metodo,
                        "referencia": referencia.strip() or None,
                        "notas": notas.strip() or None,
                    }
                    if insert_payment(data):
                        st.success(f"✅ Pago de **RD$ {monto:,.2f}** registrado correctamente ({metodo}).")
                        st.balloons()

    # ---------- DASHBOARD / CUADRE ----------
    elif menu == "Dashboard / Cuadre":
        mostrar_header()
        st.subheader("📊 Dashboard y Cuadre")

        tab1, tab2, tab3 = st.tabs(["📅 Hoy", "📆 Este mes", "🔍 Rango personalizado"])

        # --- Hoy ---
        with tab1:
            hoy = date.today()
            df_hoy = get_payments(fecha_inicio=hoy, fecha_fin=hoy)
            totales_hoy = get_totales(df_hoy)

            st.markdown(f"**Resumen del día:** {hoy.strftime('%d/%m/%Y')}")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("💵 Efectivo", f"RD$ {totales_hoy.get('Efectivo', 0):,.2f}")
            c2.metric("🏦 Popular", f"RD$ {totales_hoy.get('Banco Popular', 0):,.2f}")
            c3.metric("🏦 BHD", f"RD$ {totales_hoy.get('BHD', 0):,.2f}")
            c4.metric("🏦 Reservas", f"RD$ {totales_hoy.get('Banco de Reservas', 0):,.2f}")
            c5.metric("💰 TOTAL", f"RD$ {totales_hoy.get('Total', 0):,.2f}")

            if not df_hoy.empty:
                st.dataframe(
                    df_hoy[["fecha", "hora", "nombre_cliente", "casillero", "metodo", "monto", "referencia"]],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hay pagos registrados hoy.")

            col_pdf, col_txt = st.columns(2)
            with col_pdf:
                pdf_bytes = generar_pdf(df_hoy, f"Cierre del día {hoy.strftime('%d/%m/%Y')}", totales_hoy)
                st.download_button("📄 Descargar PDF", data=pdf_bytes,
                                   file_name=f"cierre_dia_{hoy.strftime('%Y%m%d')}.pdf",
                                   mime="application/pdf", use_container_width=True)
            with col_txt:
                txt = generar_texto(df_hoy, f"Cierre del día {hoy.strftime('%d/%m/%Y')}", totales_hoy)
                st.download_button("📝 Descargar TXT", data=txt.encode("utf-8"),
                                   file_name=f"cierre_dia_{hoy.strftime('%Y%m%d')}.txt",
                                   mime="text/plain", use_container_width=True)

        # --- Este mes ---
        with tab2:
            hoy = date.today()
            inicio_mes = hoy.replace(day=1)
            df_mes = get_payments(fecha_inicio=inicio_mes, fecha_fin=hoy)
            totales_mes = get_totales(df_mes)

            st.markdown(f"**Resumen del mes:** {inicio_mes.strftime('%B %Y').title()}")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("💵 Efectivo", f"RD$ {totales_mes.get('Efectivo', 0):,.2f}")
            c2.metric("🏦 Popular", f"RD$ {totales_mes.get('Banco Popular', 0):,.2f}")
            c3.metric("🏦 BHD", f"RD$ {totales_mes.get('BHD', 0):,.2f}")
            c4.metric("🏦 Reservas", f"RD$ {totales_mes.get('Banco de Reservas', 0):,.2f}")
            c5.metric("💰 TOTAL MES", f"RD$ {totales_mes.get('Total', 0):,.2f}")

            if not df_mes.empty:
                st.dataframe(
                    df_mes[["fecha", "nombre_cliente", "casillero", "metodo", "monto"]],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hay pagos registrados este mes.")

            col_pdf, col_txt = st.columns(2)
            with col_pdf:
                pdf_bytes = generar_pdf(df_mes, f"Cuadre del mes {inicio_mes.strftime('%B %Y')}", totales_mes)
                st.download_button("📄 PDF del mes", data=pdf_bytes,
                                   file_name=f"cuadre_mes_{inicio_mes.strftime('%Y%m')}.pdf",
                                   mime="application/pdf", use_container_width=True)
            with col_txt:
                txt = generar_texto(df_mes, f"Cuadre del mes {inicio_mes.strftime('%B %Y')}", totales_mes)
                st.download_button("📝 TXT del mes", data=txt.encode("utf-8"),
                                   file_name=f"cuadre_mes_{inicio_mes.strftime('%Y%m')}.txt",
                                   mime="text/plain", use_container_width=True)

        # --- Rango personalizado ---
        with tab3:
            st.markdown("**Cuadre por rango de fechas**")
            col_a, col_b = st.columns(2)
            with col_a:
                fecha_ini = st.date_input("Desde", value=date.today().replace(day=1), key="rango_ini")
            with col_b:
                fecha_fin = st.date_input("Hasta", value=date.today(), key="rango_fin")

            if fecha_ini > fecha_fin:
                st.warning("La fecha de inicio no puede ser posterior a la fecha de fin.")
            else:
                df_rango = get_payments(fecha_inicio=fecha_ini, fecha_fin=fecha_fin)
                totales_rango = get_totales(df_rango)

                st.markdown(f"**Período:** {fecha_ini.strftime('%d/%m/%Y')} → {fecha_fin.strftime('%d/%m/%Y')}")
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("💵 Efectivo", f"RD$ {totales_rango.get('Efectivo', 0):,.2f}")
                c2.metric("🏦 Popular", f"RD$ {totales_rango.get('Banco Popular', 0):,.2f}")
                c3.metric("🏦 BHD", f"RD$ {totales_rango.get('BHD', 0):,.2f}")
                c4.metric("🏦 Reservas", f"RD$ {totales_rango.get('Banco de Reservas', 0):,.2f}")
                c5.metric("💰 TOTAL", f"RD$ {totales_rango.get('Total', 0):,.2f}")

                if not df_rango.empty:
                    st.dataframe(
                        df_rango[["fecha", "nombre_cliente", "casillero", "metodo", "monto", "referencia"]],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No hay pagos en el rango seleccionado.")

                col_pdf, col_txt, col_csv = st.columns(3)
                titulo_rango = f"Cuadre del {fecha_ini.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}"
                with col_pdf:
                    pdf_bytes = generar_pdf(df_rango, titulo_rango, totales_rango)
                    st.download_button("📄 PDF", data=pdf_bytes,
                                       file_name=f"cuadre_{fecha_ini}_{fecha_fin}.pdf",
                                       mime="application/pdf", use_container_width=True)
                with col_txt:
                    txt = generar_texto(df_rango, titulo_rango, totales_rango)
                    st.download_button("📝 TXT", data=txt.encode("utf-8"),
                                       file_name=f"cuadre_{fecha_ini}_{fecha_fin}.txt",
                                       mime="text/plain", use_container_width=True)
                with col_csv:
                    if not df_rango.empty:
                        csv = df_rango.to_csv(index=False).encode("utf-8")
                        st.download_button("📊 CSV", data=csv,
                                           file_name=f"cuadre_{fecha_ini}_{fecha_fin}.csv",
                                           mime="text/csv", use_container_width=True)

    # ---------- HISTORIAL ----------
    elif menu == "Historial":
        mostrar_header()
        st.subheader("📋 Historial de pagos")

        col1, col2, col3 = st.columns(3)
        with col1:
            f_ini = st.date_input("Desde", value=date.today() - timedelta(days=30), key="hist_ini")
        with col2:
            f_fin = st.date_input("Hasta", value=date.today(), key="hist_fin")
        with col3:
            filtro_metodo = st.selectbox("Método", ["Todos"] + METODOS)

        df = get_payments(fecha_inicio=f_ini, fecha_fin=f_fin,
                          metodo=filtro_metodo if filtro_metodo != "Todos" else None)

        if df.empty:
            st.info("No se encontraron pagos con los filtros seleccionados.")
        else:
            st.dataframe(
                df[["fecha", "hora", "nombre_cliente", "casillero", "metodo", "monto", "referencia", "notas"]],
                use_container_width=True,
                hide_index=True
            )
            st.caption(f"Total de registros: **{len(df)}** | Suma: **RD$ {df['monto'].sum():,.2f}**")

    # ---------- CONFIGURACIÓN ----------
    elif menu == "Configuración":
        mostrar_header()
        st.subheader("⚙️ Configuración")

        st.info("La contraseña de iPlus **nunca se usa automáticamente**. Solo es un recordatorio.")
        st.text_input("Recordatorio de contraseña iPlus (solo ayuda)", type="password",
                      help="Cámbiala cada mes cuando actualices la de iPlus")

        st.markdown("---")
        st.markdown("**Información del sistema**")
        st.write("- **Nombre:** QM Juan Bosch")
        st.write("- **Sucursal:** Ciudad Juan Bosch, República Dominicana")
        st.write("- **Bancos:** Banco Popular · BHD · Banco de Reservas · Efectivo")
        st.write("- **Versión:** 1.1 (gratuita)")

        st.markdown("---")
        st.warning("Cambia la contraseña de acceso de esta aplicación periódicamente y nunca compartas las credenciales de iPlus.")

if __name__ == "__main__":
    main()
