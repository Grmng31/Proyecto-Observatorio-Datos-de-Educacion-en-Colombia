"""
Script para crear el Modelo Estrella SABER desde el archivo de cruce
====================================================================
Genera dimensiones y tabla de hechos desde cruce_saber_11_pro_completo.parquet
"""

import pandas as pd
import duckdb
from pathlib import Path
import os

# Rutas
BASE_DIR = Path(__file__).parent.parent.parent
CRUCE_PATH = BASE_DIR / 'datos' / 'processed' / 'icfes' / 'cruce_saber_11_pro_limpio.parquet'
MODELOS_DIR = BASE_DIR / 'datos' / 'processed' / 'modelos'
SABER_DIR = MODELOS_DIR / 'saber'
SABER_DIR.mkdir(parents=True, exist_ok=True)

DUCKDB_PATH = SABER_DIR / 'modelo_estrella_saber.duckdb'

def crear_modelo_estrella_saber():
    print("=" * 80)
    print("CREANDO MODELO ESTRELLA SABER DESDE CRUCE")
    print("=" * 80)
    
    # Verificar archivo de cruce - usar el limpio si existe, sino el original
    cruce_limpio_path = BASE_DIR / 'datos' / 'processed' / 'icfes' / 'cruce_saber_11_pro_limpio.parquet'
    cruce_original_path = BASE_DIR / 'datos' / 'processed' / 'icfes' / 'cruce_saber_11_pro_completo.parquet'
    
    if cruce_limpio_path.exists():
        cruce_path = cruce_limpio_path
    elif cruce_original_path.exists():
        cruce_path = cruce_original_path
    else:
        print(f"ERROR: No se encontro el archivo de cruce")
        return
    
    print(f"\nLeyendo cruce desde: {cruce_path}")
    df = pd.read_parquet(cruce_path)
    print(f"  Registros: {len(df):,}")
    print(f"  Columnas: {len(df.columns)}")
    
    # Eliminar DuckDB si existe
    if DUCKDB_PATH.exists():
        os.remove(DUCKDB_PATH)
        print(f"\nEliminando DuckDB existente: {DUCKDB_PATH}")
    
    # Crear conexion DuckDB
    print(f"\nCreando DuckDB: {DUCKDB_PATH}")
    con = duckdb.connect(str(DUCKDB_PATH))
    
    # ==========================================
    # DIMENSION: PERIODO (desde Saber Pro - 2015-2024)
    # ==========================================
    print("\n" + "=" * 60)
    print("GENERANDO DIMENSION PERIODO...")
    print("=" * 60)
    
    dim_periodo = df[['anio_sbpro', 'periodo_sbpro']].drop_duplicates().copy()
    dim_periodo.columns = ['anio', 'periodo']
    dim_periodo = dim_periodo.sort_values('periodo').reset_index(drop=True)
    dim_periodo['id_periodo'] = dim_periodo.index + 1
    
    # Extraer semestre del periodo
    dim_periodo['semestre'] = dim_periodo['periodo'].astype(str).str[-1].astype(int)
    
    dim_periodo = dim_periodo[['id_periodo', 'periodo', 'anio', 'semestre']]
    
    print(f"  Registros: {len(dim_periodo)}")
    print(f"  Periodos: {dim_periodo['periodo'].min()} - {dim_periodo['periodo'].max()}")
    
    con.register('dim_periodo_src', dim_periodo)
    con.execute("""
        CREATE TABLE dim_periodo AS 
        SELECT * FROM dim_periodo_src
    """)
    
    # ==========================================
    # DIMENSION: INSTITUCION
    # ==========================================
    print("\n" + "=" * 60)
    print("GENERANDO DIMENSION INSTITUCION...")
    print("=" * 60)
    
    dim_institucion = df[['cole_cod_dane_establecimiento', 'cole_nombre_establecimiento', 
                          'cole_cod_depto_ubicacion', 'cole_cod_mcpio_ubicacion']].drop_duplicates().copy()
    dim_institucion = dim_institucion.dropna(subset=['cole_cod_dane_establecimiento'])
    dim_institucion.columns = ['codigo_dane', 'nombre', 'codigo_depto', 'codigo_mcpio']
    dim_institucion = dim_institucion.sort_values('codigo_dane').reset_index(drop=True)
    dim_institucion['id_institucion'] = dim_institucion.index + 1
    
    dim_institucion = dim_institucion[['id_institucion', 'codigo_dane', 'nombre', 'codigo_depto', 'codigo_mcpio']]
    
    print(f"  Registros: {len(dim_institucion):,}")
    
    con.register('dim_institucion_src', dim_institucion)
    con.execute("""
        CREATE TABLE dim_institucion AS 
        SELECT * FROM dim_institucion_src
    """)
    
    # ==========================================
    # DIMENSION: ESTUDIANTE COHORTE
    # ==========================================
    print("\n" + "=" * 60)
    print("GENERANDO DIMENSION ESTUDIANTE COHORTE...")
    print("=" * 60)
    
    dim_cohorte = df[['estu_genero_11', 'estu_edad', 'estu_depto_presentacion_11', 
                      'estu_mcpio_presentacion_11']].drop_duplicates().copy()
    dim_cohorte.columns = ['genero', 'edad', 'codigo_depto', 'codigo_mcpio']
    dim_cohorte = dim_cohorte.dropna(subset=['genero'])
    dim_cohorte = dim_cohorte.sort_values(['genero', 'edad']).reset_index(drop=True)
    dim_cohorte['id_cohorte'] = dim_cohorte.index + 1
    
    dim_cohorte = dim_cohorte[['id_cohorte', 'genero', 'edad', 'codigo_depto', 'codigo_mcpio']]
    
    print(f"  Registros: {len(dim_cohorte):,}")
    
    con.register('dim_cohorte_src', dim_cohorte)
    con.execute("""
        CREATE TABLE dim_estudiante_cohorte AS 
        SELECT * FROM dim_cohorte_src
    """)
    
    # ==========================================
    # TABLA DE HECHOS: RESULTADOS SABER
    # ==========================================
    print("\n" + "=" * 60)
    print("GENERANDO TABLA DE HECHOS RESULTADOS SABER...")
    print("=" * 60)
    
    # Convertir columnas de puntaje a numericas
    punt_cols = ['punt_global', 'punt_lenguaje', 'punt_matematicas', 'punt_ingles',
                 'mod_comuni_escrita_punt', 'mod_razona_cuantitat_punt', 'mod_ingles_punt', 'mod_competen_ciudada_punt']
    for col in punt_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Seleccionar columnas para fact table (usando periodo_sbpro para años 2015-2024)
    fact_cols = ['periodo_sbpro', 'cole_cod_dane_establecimiento', 'estu_genero_11', 'estu_edad',
                 'estu_depto_presentacion_11', 'estu_mcpio_presentacion_11'] + punt_cols
    
    fact_df = df[fact_cols].copy()
    fact_df = fact_df.dropna(subset=['periodo_sbpro', 'cole_cod_dane_establecimiento'])
    
    # Hacer join con dimensiones para obtener IDs
    con.register('fact_src', fact_df)
    
    # Crear tabla de hechos con joins (usando periodo_sbpro)
    con.execute("""
        CREATE TABLE fact_resultados_saber AS 
        SELECT 
            p.id_periodo,
            i.id_institucion,
            c.id_cohorte,
            f.punt_lenguaje,
            f.punt_matematicas,
            f.punt_ingles,
            f.mod_comuni_escrita_punt,
            f.mod_razona_cuantitat_punt,
            f.mod_ingles_punt,
            f.mod_competen_ciudada_punt,
            f.punt_global
        FROM fact_src f
        LEFT JOIN dim_periodo p ON f.periodo_sbpro = p.periodo
        LEFT JOIN dim_institucion i ON f.cole_cod_dane_establecimiento = i.codigo_dane
        LEFT JOIN dim_estudiante_cohorte c ON 
            f.estu_genero_11 = c.genero AND 
            f.estu_edad = c.edad AND
            f.estu_depto_presentacion_11 = c.codigo_depto AND
            f.estu_mcpio_presentacion_11 = c.codigo_mcpio
    """)
    
    # Verificar conteos
    total_hechos = con.execute("SELECT COUNT(*) FROM fact_resultados_saber").fetchone()[0]
    nulos_periodo = con.execute("SELECT COUNT(*) FROM fact_resultados_saber WHERE id_periodo IS NULL").fetchone()[0]
    nulos_institucion = con.execute("SELECT COUNT(*) FROM fact_resultados_saber WHERE id_institucion IS NULL").fetchone()[0]
    nulos_cohorte = con.execute("SELECT COUNT(*) FROM fact_resultados_saber WHERE id_cohorte IS NULL").fetchone()[0]
    
    print(f"  Registros en fact_resultados_saber: {total_hechos:,}")
    print(f"  Nulos en id_periodo: {nulos_periodo:,}")
    print(f"  Nulos en id_institucion: {nulos_institucion:,}")
    print(f"  Nulos en id_cohorte: {nulos_cohorte:,}")
    
    # ==========================================
    # RESUMEN FINAL
    # ==========================================
    print("\n" + "=" * 60)
    print("RESUMEN DEL MODELO ESTRELLA SABER")
    print("=" * 60)
    
    print("\nTablas creadas:")
    for table in ['dim_periodo', 'dim_institucion', 'dim_estudiante_cohorte', 'fact_resultados_saber']:
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count:,} registros")
    
    print(f"\nArchivo DuckDB: {DUCKDB_PATH}")
    print(f"Tamano: {os.path.getsize(DUCKDB_PATH) / (1024 * 1024):.2f} MB")
    
    # Cerrar conexion
    con.close()
    
    print("\n" + "=" * 80)
    print("MODELO ESTRELLA SABER CREADO EXITOSAMENTE")
    print("=" * 80)

if __name__ == "__main__":
    crear_modelo_estrella_saber()