"""
Script para Materializar Dimensiones Compartidas - Sprint 2
============================================================
Crea dimensiones compartidas (dim_institucion, dim_programa, dim_municipio, dim_periodo)
desde los modelos estrella PTE, SNIES y SABER.
"""

import duckdb
import pandas as pd
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).parent.parent.parent
MODELOS_DIR = BASE_DIR / 'datos' / 'processed' / 'modelos'
OUTPUT_DIR = MODELOS_DIR / 'dimensiones_compartidas'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Rutas a modelos estrella
PTE_DB = MODELOS_DIR / 'pte' / 'modelo_estrella_pte.duckdb'
SNIES_DB = MODELOS_DIR / 'snies' / 'modelo_estrella_snies.duckdb'
SABER_DB = MODELOS_DIR / 'saber' / 'modelo_estrella_saber.duckdb'

# Output
OUTPUT_DB = OUTPUT_DIR / 'dimensiones_compartidas.duckdb'

def materializar_dimensiones():
    print("=" * 80)
    print("MATERIALIZANDO DIMENSIONES COMPARTIDAS - SPRINT 2")
    print("=" * 80)
    
    # Eliminar DuckDB si existe
    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()
        print(f"\nEliminando DuckDB existente: {OUTPUT_DB}")
    
    # Crear conexion de salida
    con_out = duckdb.connect(str(OUTPUT_DB))
    
    # Conexiones a modelos
    con_pte = duckdb.connect(str(PTE_DB), read_only=True)
    con_snies = duckdb.connect(str(SNIES_DB), read_only=True)
    con_saber = duckdb.connect(str(SABER_DB), read_only=True)
    
    # ==========================================
    # 1. DIM_PERIODO (desde PTE y SABER)
    # ==========================================
    print("\n" + "=" * 60)
    print("1. DIM_PERIODO")
    print("=" * 60)
    
    # Desde PTE
    pte_periodos = con_pte.execute("""
        SELECT DISTINCT 
            anio_proceso as anio,
            anio_proceso || '01' as periodo,
            1 as semestre
        FROM dim_periodo
        ORDER BY anio_proceso
    """).df()
    
    # Desde SABER
    saber_periodos = con_saber.execute("""
        SELECT DISTINCT 
            anio as anio,
            periodo,
            semestre
        FROM dim_periodo
        ORDER BY periodo
    """).df()
    
    # Combinar y eliminar duplicados
    all_periodos = pd.concat([pte_periodos, saber_periodos], ignore_index=True)
    all_periodos = all_periodos.drop_duplicates(subset=['periodo']).sort_values('periodo').reset_index(drop=True)
    all_periodos['id_periodo'] = range(1, len(all_periodos) + 1)
    
    # Guardar en DuckDB
    con_out.register('periodos_src', all_periodos)
    con_out.execute("""
        CREATE TABLE dim_periodo AS 
        SELECT id_periodo, periodo, anio, semestre
        FROM periodos_src
        ORDER BY periodo
    """)
    
    count = con_out.execute("SELECT COUNT(*) FROM dim_periodo").fetchone()[0]
    print(f"  Registros: {count}")
    print(f"  Rango: {con_out.execute('SELECT MIN(periodo), MAX(periodo) FROM dim_periodo').fetchone()}")
    
    # ==========================================
    # 2. DIM_MUNICIPIO (desde SABER - unico con codigos DANE)
    # ==========================================
    print("\n" + "=" * 60)
    print("2. DIM_MUNICIPIO")
    print("=" * 60)
    
    # Desde SABER - obtener municipios unicos con codigos DANE
    saber_municipios = con_saber.execute("""
        SELECT DISTINCT 
            codigo_depto as depto_codigo,
            codigo_mcpio as mcpio_codigo
        FROM dim_institucion
        WHERE codigo_depto IS NOT NULL AND codigo_mcpio IS NOT NULL
    """).df()
    
    # Limpiar valores flotantes a enteros
    for col in ['depto_codigo', 'mcpio_codigo']:
        saber_municipios[col] = saber_municipios[col].astype(float).astype(int).astype(str)
    
    # Combinar
    all_municipios = saber_municipios.drop_duplicates().sort_values(['depto_codigo', 'mcpio_codigo']).reset_index(drop=True)
    all_municipios['id_municipio'] = range(1, len(all_municipios) + 1)
    
    # Guardar en DuckDB
    con_out.register('municipios_src', all_municipios)
    con_out.execute("""
        CREATE TABLE dim_municipio AS 
        SELECT id_municipio, depto_codigo, mcpio_codigo
        FROM municipios_src
        ORDER BY depto_codigo, mcpio_codigo
    """)
    
    count = con_out.execute("SELECT COUNT(*) FROM dim_municipio").fetchone()[0]
    print(f"  Registros: {count}")
    
    # ==========================================
    # 3. DIM_INSTITUCION (colegios y universidades)
    # ==========================================
    print("\n" + "=" * 60)
    print("3. DIM_INSTITUCION")
    print("=" * 60)
    
    # Desde SABER - colegios (instituciones de educacion media)
    saber_inst = con_saber.execute("""
        SELECT DISTINCT 
            codigo_dane,
            nombre,
            codigo_depto,
            codigo_mcpio,
            'media' as nivel
        FROM dim_institucion
        WHERE codigo_dane IS NOT NULL
    """).df()
    
    # Desde SNIES - instituciones de educacion superior
    snies_inst = con_snies.execute("""
        SELECT DISTINCT 
            codigo_institucion as codigo_dane,
            nombre_institucion as nombre,
            NULL as codigo_depto,
            NULL as codigo_mcpio,
            'superior' as nivel
        FROM fact_matriculas
        WHERE codigo_institucion IS NOT NULL
    """).df()
    
    # Combinar
    all_inst = pd.concat([snies_inst, saber_inst], ignore_index=True)
    all_inst = all_inst.drop_duplicates(subset=['codigo_dane']).sort_values('codigo_dane').reset_index(drop=True)
    all_inst['id_institucion'] = range(1, len(all_inst) + 1)
    
    # Guardar en DuckDB
    con_out.register('instituciones_src', all_inst)
    con_out.execute("""
        CREATE TABLE dim_institucion AS 
        SELECT id_institucion, codigo_dane, nombre, codigo_depto, codigo_mcpio, nivel
        FROM instituciones_src
        ORDER BY codigo_dane
    """)
    
    count = con_out.execute("SELECT COUNT(*) FROM dim_institucion").fetchone()[0]
    print(f"  Registros: {count}")
    
    # ==========================================
    # 4. DIM_PROGRAMA (solo SNIES - educacion superior)
    # ==========================================
    print("\n" + "=" * 60)
    print("4. DIM_PROGRAMA")
    print("=" * 60)
    
    # Desde SNIES - programas academicos
    programas = con_snies.execute("""
        SELECT DISTINCT 
            nombre_programa as nombre,
            nivel_formacion as nivel,
            metodologia
        FROM fact_matriculas
        WHERE nombre_programa IS NOT NULL
    """).df()
    
    programas = programas.dropna(subset=['nombre']).sort_values('nombre').reset_index(drop=True)
    programas['codigo_programa'] = 'PROG_' + programas.index.astype(str).str.zfill(5)
    programas['id_programa'] = range(1, len(programas) + 1)
    
    # Guardar en DuckDB
    con_out.register('programas_src', programas)
    con_out.execute("""
        CREATE TABLE dim_programa AS 
        SELECT id_programa, codigo_programa, nombre, nivel, metodologia
        FROM programas_src
        ORDER BY nombre
    """)
    
    count = con_out.execute("SELECT COUNT(*) FROM dim_programa").fetchone()[0]
    print(f"  Registros: {count}")
    
    # ==========================================
    # RESUMEN FINAL
    # ==========================================
    print("\n" + "=" * 60)
    print("RESUMEN DE DIMENSIONES COMPARTIDAS")
    print("=" * 60)
    
    print("\nTablas creadas:")
    for table in ['dim_periodo', 'dim_municipio', 'dim_institucion', 'dim_programa']:
        count = con_out.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count:,} registros")
    
    print(f"\nArchivo DuckDB: {OUTPUT_DB}")
    print(f"Tamano: {OUTPUT_DB.stat().st_size / (1024 * 1024):.2f} MB")
    
    # Cerrar conexiones
    con_pte.close()
    con_snies.close()
    con_saber.close()
    con_out.close()
    
    print("\n" + "=" * 80)
    print("DIMENSIONES COMPARTIDAS MATERIALIZADAS EXITOSAMENTE")
    print("=" * 80)

if __name__ == "__main__":
    materializar_dimensiones()