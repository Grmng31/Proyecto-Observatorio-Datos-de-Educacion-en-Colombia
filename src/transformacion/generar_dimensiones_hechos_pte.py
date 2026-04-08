import pandas as pd
import numpy as np
from pathlib import Path
import os

"""
Script para generar las dimensiones y tabla de hechos del Modelo Estrella PTE
a partir del parquet consolidado generado por limpieza_pte.py.

Genera:
- dimensiones/dim_entidad.parquet
- dimensiones/dim_rubro.parquet
- dimensiones/dim_periodo.parquet
- hechos/fact_presupuesto.parquet
"""

# Rutas
BASE_DIR = Path(__file__).parent.parent.parent
PROCESSED_PTE = BASE_DIR / "datos" / "processed" / "pte"
CONSOLIDADO_PATH = PROCESSED_PTE / "pte_limpio_consolidado.parquet"

def generar_dimensiones_hechos():
    print("=" * 80)
    print("GENERANDO DIMENSIONES Y HECHOS PARA MODELO ESTRELLA PTE")
    print("=" * 80)
    
    # Verificar que existe el consolidado
    if not CONSOLIDADO_PATH.exists():
        print(f"ERROR: No se encontro el archivo consolidado en {CONSOLIDADO_PATH}")
        print("Ejecuta primero: python src/ingesta/limpieza_pte.py")
        return
    
    print(f"\nLeyendo consolidado desde: {CONSOLIDADO_PATH}")
    df = pd.read_parquet(CONSOLIDADO_PATH)
    print(f"  Registros totales: {len(df):,}")
    print(f"  Columnas: {len(df.columns)}")
    
    # Crear directorios de salida
    dim_dir = PROCESSED_PTE / "dimensiones"
    hechos_dir = PROCESSED_PTE / "hechos"
    dim_dir.mkdir(parents=True, exist_ok=True)
    hechos_dir.mkdir(parents=True, exist_ok=True)
    
    # ==========================================
    # DIMENSION: ENTIDAD
    # ==========================================
    print("\n" + "="*60)
    print("GENERANDO DIMENSION ENTIDAD...")
    print("="*60)
    
    # Seleccionar columnas unicas de entidad
    cols_entidad = ['nombreentidad']
    # Agregar codigoentidad si existe
    if 'codigoentidad' in df.columns:
        cols_entidad.append('codigoentidad')
    
    dim_entidad = df.drop_duplicates(subset=cols_entidad)[cols_entidad].copy()
    dim_entidad = dim_entidad.dropna(subset=['nombreentidad'])
    dim_entidad = dim_entidad.reset_index(drop=True)
    dim_entidad['id_entidad'] = dim_entidad.index + 1  # ID secuencial
    
    # Reordenar columnas
    cols_order = ['id_entidad'] + [c for c in cols_entidad if c != 'id_entidad']
    dim_entidad = dim_entidad[cols_order]
    
    print(f"  Registros unicos de entidad: {len(dim_entidad):,}")
    print(f"  Columnas: {list(dim_entidad.columns)}")
    
    # Guardar
    dim_entidad_path = dim_dir / "dim_entidad.parquet"
    dim_entidad.to_parquet(dim_entidad_path, index=False)
    print(f"  Guardado en: {dim_entidad_path}")
    
    # ==========================================
    # DIMENSION: RUBRO
    # ==========================================
    print("\n" + "="*60)
    print("GENERANDO DIMENSION RUBRO...")
    print("="*60)
    
    # Columnas que describen el rubro
    cols_rubro = ['rubro']
    if 'descripcion' in df.columns:
        cols_rubro.append('descripcion')
    
    # Agregar columnas de codigos individuales si existen
    cols_codigo = ['codigotipogasto', 'codigonivelrubrogasto', 'codigodetallegasto', 
                   'codigoquintonivel', 'codigocuartonivel']
    cols_nombre = ['nombretipogasto', 'nombrenivelrubrogasto', 'nombredetallegasto',
                   'nombrequintonivel', 'nombrecuartonivel']
    
    for col in cols_codigo + cols_nombre:
        if col in df.columns:
            cols_rubro.append(col)
    
    dim_rubro = df.drop_duplicates(subset=cols_rubro)[cols_rubro].copy()
    dim_rubro = dim_rubro.dropna(subset=['rubro'])
    # Eliminar filas donde rubro sea solo 'SIN_DATOS' o vacio
    dim_rubro = dim_rubro[dim_rubro['rubro'].astype(str).str.strip() != 'SIN_DATOS']
    dim_rubro = dim_rubro[dim_rubro['rubro'].astype(str).str.strip() != '']
    dim_rubro = dim_rubro.reset_index(drop=True)
    dim_rubro['id_rubro'] = dim_rubro.index + 1  # ID secuencial
    
    # Reordenar columnas
    cols_order = ['id_rubro'] + [c for c in cols_rubro if c != 'id_rubro']
    dim_rubro = dim_rubro[cols_order]
    
    print(f"  Registros unicos de rubro: {len(dim_rubro):,}")
    print(f"  Columnas: {list(dim_rubro.columns)}")
    
    # Guardar
    dim_rubro_path = dim_dir / "dim_rubro.parquet"
    dim_rubro.to_parquet(dim_rubro_path, index=False)
    print(f"  Guardado en: {dim_rubro_path}")
    
    # ==========================================
    # DIMENSION: PERIODO
    # ==========================================
    print("\n" + "="*60)
    print("GENERANDO DIMENSION PERIODO...")
    print("="*60)
    
    # Extraer anos unicos
    dim_periodo = df[['anio_proceso']].drop_duplicates().copy()
    dim_periodo = dim_periodo.sort_values('anio_proceso').reset_index(drop=True)
    dim_periodo['id_periodo'] = dim_periodo.index + 1  # ID secuencial
    
    # Reordenar
    dim_periodo = dim_periodo[['id_periodo', 'anio_proceso']]
    
    print(f"  Registros unicos de periodo: {len(dim_periodo)}")
    print(f"  Anos: {list(dim_periodo['anio_proceso'])}")
    
    # Guardar
    dim_periodo_path = dim_dir / "dim_periodo.parquet"
    dim_periodo.to_parquet(dim_periodo_path, index=False)
    print(f"  Guardado en: {dim_periodo_path}")
    
    # ==========================================
    # TABLA DE HECHOS: PRESUPUESTO
    # ==========================================
    print("\n" + "="*60)
    print("GENERANDO TABLA DE HECHOS PRESUPUESTO...")
    print("="*60)
    
    # Columnas de presupuesto
    columnas_presupuesto = ['apropiacioninicial', 'apropiacionvigente', 'compromisos', 
                           'obligaciones', 'pagos']
    
    # Seleccionar columnas para el join - solo las que existen en el consolidado
    cols_join = ['nombreentidad', 'rubro', 'anio_proceso']
    
    # Agregar codigoentidad si existe
    if 'codigoentidad' in df.columns:
        cols_join.append('codigoentidad')
    
    # Crear tabla de hechos
    fact_cols = cols_join + columnas_presupuesto
    fact_presupuesto = df[fact_cols].copy()
    
    # Hacer join con las dimensiones para obtener los IDs
    # Join con entidad - usar solo columnas que existen en ambos
    cols_entidad_join = [c for c in cols_entidad if c in fact_presupuesto.columns]
    fact_presupuesto = fact_presupuesto.merge(
        dim_entidad[['id_entidad'] + cols_entidad_join],
        on=cols_entidad_join,
        how='left',
        suffixes=('', '_entidad')
    )
    
    # Join con rubro - usar solo columnas que existen en ambos
    cols_rubro_join = [c for c in cols_rubro if c in fact_presupuesto.columns]
    fact_presupuesto = fact_presupuesto.merge(
        dim_rubro[['id_rubro'] + cols_rubro_join],
        on=cols_rubro_join,
        how='left',
        suffixes=('', '_rubro')
    )
    
    # Join con periodo
    fact_presupuesto = fact_presupuesto.merge(
        dim_periodo,
        on='anio_proceso',
        how='left'
    )
    
    # Seleccionar solo columnas finales
    fact_final = fact_presupuesto[['id_entidad', 'id_rubro', 'id_periodo'] + columnas_presupuesto].copy()
    
    # Asegurar que las columnas numericas sean numericass
    for col in columnas_presupuesto:
        fact_final[col] = pd.to_numeric(fact_final[col], errors='coerce').fillna(0)
    
    print(f"  Registros en tabla de hechos: {len(fact_final):,}")
    print(f"  Columnas: {list(fact_final.columns)}")
    
    # Verificar nulos en IDs
    nulos_ids = fact_final[['id_entidad', 'id_rubro', 'id_periodo']].isnull().sum()
    print(f"  IDs nulos:\n{nulos_ids}")
    
    # Guardar
    fact_presupuesto_path = hechos_dir / "fact_presupuesto.parquet"
    fact_final.to_parquet(fact_presupuesto_path, index=False)
    print(f"  Guardado en: {fact_presupuesto_path}")
    
    # ==========================================
    # RESUMEN FINAL
    # ==========================================
    print("\n" + "="*60)
    print("RESUMEN DE GENERACION COMPLETADA")
    print("="*60)
    print(f"\nArchivos generados:")
    print(f"  1. {dim_entidad_path} ({len(dim_entidad):,} registros)")
    print(f"  2. {dim_rubro_path} ({len(dim_rubro):,} registros)")
    print(f"  3. {dim_periodo_path} ({len(dim_periodo)} registros)")
    print(f"  4. {fact_presupuesto_path} ({len(fact_final):,} registros)")
    
    # Tamanos de archivo
    for path in [dim_entidad_path, dim_rubro_path, dim_periodo_path, fact_presupuesto_path]:
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"     Tamanio: {size_mb:.2f} MB")
    
    print("\n" + "="*60)
    print("¡DIMENSIONES Y HECHOS GENERADOS EXITOSAMENTE!")
    print("="*60)

if __name__ == "__main__":
    generar_dimensiones_hechos()