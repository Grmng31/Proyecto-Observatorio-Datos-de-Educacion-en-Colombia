import pandas as pd
import duckdb
from pathlib import Path
import os

print("=" * 60)
print("CREANDO MODELO ESTRELLA SABER (ICFES) EN DUCKDB")
print("=" * 60)

# Rutas
BASE_DIR = Path(__file__).parent.parent.parent
PROCESSED_ICFES = BASE_DIR / "datos" / "processed" / "icfes"
MODELOS_DIR = BASE_DIR / "datos" / "processed" / "modelos"

# Crear directorios
MODELOS_DIR.mkdir(parents=True, exist_ok=True)
(Path(MODELOS_DIR) / "saber").mkdir(exist_ok=True)

# Cargar datos del cruce
print("\nCargando datos del cruce Saber 11 - Saber Pro...")
df_cruce = pd.read_parquet(PROCESSED_ICFES / "cruce_saber_11_pro_completo.parquet")
print(f"  Total registros: {len(df_cruce):,}")

# ==========================================
# DIMENSION 1: dim_periodo (Periodos ICFES)
# ==========================================
print("\nCreando dimension periodo...")

# Extraer periodos unicos de Saber 11 y Saber Pro
periodos_11 = df_cruce[['anio_sb11', 'periodo_sb11']].drop_duplicates()
periodos_11.columns = ['anio', 'periodo']

periodos_pro = df_cruce[['anio_sbpro', 'periodo_pro']].drop_duplicates()
periodos_pro.columns = ['anio', 'periodo']

periodos = pd.concat([periodos_11, periodos_pro]).drop_duplicates()
periodos = periodos.sort_values('periodo').reset_index(drop=True)
periodos['id_periodo'] = range(1, len(periodos) + 1)

# Extraer semestre del periodo
periodos['semestre'] = periodos['periodo'].str[-1].astype(int)

print(f"  Periodos unicos: {len(periodos)}")

# ==========================================
# DIMENSION 2: dim_institucion (Colegios)
# ==========================================
print("\nCreando dimension institucion...")

instituciones = df_cruce[['cole_cod_dane_establecimiento', 'cole_nombre_establecimiento', 
                           'cole_cod_depto_ubicacion', 'cole_cod_mcpio_ubicacion']].drop_duplicates()
instituciones = instituciones.dropna(subset=['cole_cod_dane_establecimiento'])
instituciones = instituciones.reset_index(drop=True)
instituciones['id_institucion'] = range(1, len(instituciones) + 1)

print(f"  Instituciones unicas: {len(instituciones):,}")

# ==========================================
# DIMENSION 3: dim_estudiante_cohorte (Cohortes anonimizados)
# ==========================================
print("\nCreando dimension estudiante cohorte...")

# Agrupar por caracteristicas del estudiante (anonimizado)
cohortes = df_cruce[['estu_genero_11', 'estu_edad', 'estu_fechanacimiento']].drop_duplicates()
cohortes = cohortes.dropna(subset=['estu_genero_11'])
cohortes = cohortes.reset_index(drop=True)
cohortes['id_cohorte'] = range(1, len(cohortes) + 1)

# Calcular rango de edad
def rango_edad(edad):
    if pd.isna(edad) or edad == '':
        return 'ND'
    try:
        edad = int(float(edad))
    except (ValueError, TypeError):
        return 'ND'
    if edad < 15:
        return '12-14'
    elif edad < 18:
        return '15-17'
    elif edad < 21:
        return '18-20'
    elif edad < 25:
        return '21-24'
    else:
        return '25+'

cohortes['rango_edad'] = cohortes['estu_edad'].apply(rango_edad)

print(f"  Cohortes unicos: {len(cohortes):,}")

# ==========================================
# DIMENSION 4: dim_prueba (Tipo de prueba)
# ==========================================
print("\nCreando dimension prueba...")

pruebas = pd.DataFrame({
    'id_prueba': [1, 2],
    'nombre_prueba': ['Saber 11', 'Saber Pro'],
    'descripcion': ['Examen de estado para educacion media', 
                    'Examen para educacion superior'],
    'escala_puntaje': ['0-500', '0-500']
})

print(f"  Tipos de prueba: {len(pruebas)}")

# ==========================================
# TABLA DE HECHOS: fact_resultados_saber
# ==========================================
print("\nCreando tabla de hechos fact_resultados_saber...")

# Unir con dimensiones - evitar columnas duplicadas
fact = df_cruce.copy()

# Merge con periodos Saber 11
periodos_11 = periodos[['periodo', 'id_periodo']].copy()
periodos_11.columns = ['periodo_sb11', 'id_periodo_11']
fact = fact.merge(periodos_11, on='periodo_sb11', how='left')

# Merge con periodos Saber Pro
periodos_pro = periodos[['periodo', 'id_periodo']].copy()
periodos_pro.columns = ['periodo_pro', 'id_periodo_pro']
fact = fact.merge(periodos_pro, on='periodo_pro', how='left')

# Merge con instituciones
fact = fact.merge(instituciones[['cole_cod_dane_establecimiento', 'id_institucion']], 
                  on='cole_cod_dane_establecimiento', how='left')

# Merge con cohortes
fact = fact.merge(cohortes[['estu_genero_11', 'estu_edad', 'estu_fechanacimiento', 'id_cohorte']], 
                  on=['estu_genero_11', 'estu_edad', 'estu_fechanacimiento'], how='left')

# Seleccionar columnas de la tabla de hechos
fact_hechos = pd.DataFrame({
    'id_periodo_11': fact['id_periodo_11'],
    'id_periodo_pro': fact['id_periodo_pro'],
    'id_institucion': fact['id_institucion'],
    'id_cohorte': fact['id_cohorte'],
    # Puntajes Saber 11
    'punt_lenguaje': fact['punt_lenguaje'],
    'punt_matematicas': fact['punt_matematicas'],
    'punt_ingles': fact['punt_ingles'],
    # Puntajes Saber Pro
    'mod_comuni_escrita_punt': fact['mod_comuni_escrita_punt'],
    'mod_razona_cuantitat_punt': fact['mod_razona_cuantitat_punt'],
    'mod_ingles_punt': fact['mod_ingles_punt'],
    'mod_competen_ciudada_punt': fact['mod_competen_ciudada_punt'],
    'punt_global': fact['punt_global'],
    'percentil_global': fact['percentil_global'],
})

print(f"  Registros en tabla de hechos: {len(fact_hechos):,}")

# ==========================================
# GUARDAR EN DUCKDB
# ==========================================
print("\nGuardando en DuckDB...")

db_path = MODELOS_DIR / "saber" / "modelo_estrella_saber.duckdb"
if db_path.exists():
    os.remove(db_path)

conn = duckdb.connect(str(db_path))

# Crear tablas
print("  Creando tablas en DuckDB...")

# Dimensiones
conn.execute("""
CREATE TABLE dim_periodo AS 
SELECT id_periodo, periodo, anio, semestre 
FROM periodos 
ORDER BY periodo
""")

conn.execute("""
CREATE TABLE dim_institucion AS 
SELECT id_institucion, cole_cod_dane_establecimiento as codigo_dane, 
       cole_nombre_establecimiento as nombre, 
       cole_cod_depto_ubicacion as codigo_depto,
       cole_cod_mcpio_ubicacion as codigo_mcpio
FROM instituciones 
ORDER BY id_institucion
""")

conn.execute("""
CREATE TABLE dim_estudiante_cohorte AS 
SELECT id_cohorte, estu_genero_11 as genero, estu_edad as edad, 
       estu_fechanacimiento as fecha_nacimiento, rango_edad
FROM cohortes 
ORDER BY id_cohorte
""")

conn.execute("""
CREATE TABLE dim_prueba AS 
SELECT id_prueba, nombre_prueba, descripcion, escala_puntaje 
FROM pruebas
""")

# Tabla de hechos
conn.execute("""
CREATE TABLE fact_resultados_saber AS 
SELECT * FROM fact_hechos
""")

# Verificar
print("\n" + "=" * 60)
print("VERIFICANDO MODELO ESTRELLA SABER")
print("=" * 60)

print("\nDimensiones:")
for tabla in ['dim_periodo', 'dim_institucion', 'dim_estudiante_cohorte', 'dim_prueba']:
    count = conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    print(f"  {tabla}: {count:,} registros")

print("\nTabla de hechos:")
count = conn.execute("SELECT COUNT(*) FROM fact_resultados_saber").fetchone()[0]
print(f"  fact_resultados_saber: {count:,} registros")

# Estadisticas de puntajes
print("\nEstadisticas de puntajes:")
stats = conn.execute("""
SELECT 
    AVG(CAST(punt_lenguaje AS DOUBLE)) as avg_lenguaje,
    AVG(CAST(punt_matematicas AS DOUBLE)) as avg_matematicas,
    AVG(CAST(punt_ingles AS DOUBLE)) as avg_ingles,
    AVG(CAST(punt_global AS DOUBLE)) as avg_global,
    AVG(CAST(percentil_global AS DOUBLE)) as avg_percentil
FROM fact_resultados_saber
""").fetchone()

print(f"  Promedio Lenguaje (S11): {stats[0]:.1f}")
print(f"  Promedio Matematicas (S11): {stats[1]:.1f}")
print(f"  Promedio Ingles (S11): {stats[2]:.1f}")
print(f"  Promedio Global (SPro): {stats[3]:.1f}")
print(f"  Promedio Percentil (SPro): {stats[4]:.1f}")

conn.close()

print("\n" + "=" * 60)
print("MODELO ESTRELLA SABER CREADO EXITOSAMENTE")
print(f"Archivo: {db_path}")
print("=" * 60)