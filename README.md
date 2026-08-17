# QM Juan Bosch - Sistema de Control de Caja

Aplicación web para registrar y controlar ingresos de efectivo y transferencias bancarias (Banco Popular, BHD, Banco de Reservas) de la sucursal QM Courier en Ciudad Juan Bosch.

## Características

- Registro de pagos por efectivo o transferencia
- Asociación a cliente + número de casillero
- Dashboard diario y por rango de fechas
- Totales por banco y efectivo
- Generación de PDF y archivo de texto (TXT/CSV)
- Cuadre mensual y por rango de fechas personalizado
- Acceso desde cualquier dispositivo (celular, tablet, PC)

## Stack

- **Frontend/Backend**: Streamlit
- **Base de datos**: Supabase (PostgreSQL)
- **Hosting gratuito**: Streamlit Community Cloud

## Configuración (paso a paso)

### 1. Crear proyecto en Supabase (gratis)

1. Entra a [https://supabase.com](https://supabase.com) y crea una cuenta.
2. Crea un nuevo proyecto (elige región cercana, ejemplo: South America o US East).
3. Espera a que se cree (1-2 minutos).
4. Ve a **Project Settings → API** y copia:
   - Project URL
   - `anon` `public` key

### 2. Crear la tabla de pagos

En el SQL Editor de Supabase ejecuta este código:

```sql
-- Tabla principal de pagos
CREATE TABLE payments (
  id BIGSERIAL PRIMARY KEY,
  fecha DATE NOT NULL DEFAULT CURRENT_DATE,
  hora TIME DEFAULT CURRENT_TIME,
  nombre_cliente TEXT NOT NULL,
  casillero TEXT NOT NULL,
  monto NUMERIC(12,2) NOT NULL CHECK (monto > 0),
  metodo TEXT NOT NULL CHECK (metodo IN ('Efectivo', 'Banco Popular', 'BHD', 'Banco de Reservas')),
  referencia TEXT,
  notas TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para consultas rápidas
CREATE INDEX idx_payments_fecha ON payments(fecha);
CREATE INDEX idx_payments_metodo ON payments(metodo);
CREATE INDEX idx_payments_casillero ON payments(casillero);

-- Tabla de configuración simple (opcional)
CREATE TABLE config (
  key TEXT PRIMARY KEY,
  value TEXT
);

-- Insertar clave de recordatorio de iPlus (opcional)
INSERT INTO config (key, value) VALUES ('iplus_password_reminder', '');
```

### 3. Desplegar la aplicación

1. Sube esta carpeta completa a un repositorio de GitHub (puede ser privado o público).
2. Ve a [https://share.streamlit.io](https://share.streamlit.io) e inicia sesión con GitHub.
3. Crea una nueva app apuntando a este repositorio y al archivo `app.py`.
4. En **Secrets** de Streamlit agrega:

```toml
SUPABASE_URL = "https://tu-proyecto.supabase.co"
SUPABASE_KEY = "tu-anon-key"
APP_PASSWORD = "tu-clave-segura-para-entrar-al-sistema"
```

5. Despliega.

## Uso diario

1. Entra a la URL de Streamlit.
2. Introduce la contraseña de la aplicación.
3. Registra los pagos del día.
4. Usa el menú "Reportes" para ver totales del día, del mes o de un rango de fechas.
5. Genera PDF o archivo de texto del cierre.

## Notas importantes

- La contraseña de iPlus **nunca se usa automáticamente**. Solo puedes anotar un recordatorio.
- Cambia la contraseña de la aplicación periódicamente.
- El plan gratuito de Supabase pausa el proyecto después de 7 días sin actividad. Entra al menos una vez por semana o considera el plan Pro (~US$25) si lo usas diariamente.
- Streamlit Community Cloud se duerme después de ~12 horas sin visitas. Al entrar se despierta en 20-40 segundos.
