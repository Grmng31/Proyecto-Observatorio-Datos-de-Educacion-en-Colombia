import pandas as pd
import numpy as np
import time
import gc
from pathlib import Path
import os

print("=" * 80)
print("LIMPIEZA MATRICULADOS SNIES - preparacion para CINE")
print("=" * 80)

# Rutas
BASE_DIR = Path(__file__).parent.parent.parent
RAW_MATRICULADOS = BASE_DIR / "datos" / "raw" / "snies" / "matriculados"
PROCESSED_SNIES = BASE_DIR / "datos" / "processed" / "snies"

# Crear directorio de salida
PROCESSED_SNIES.mkdir(parents=True, exist_ok=True)

# Columnas estandar que queremos mantener (incluye columnas CINE)
COLUMNAS_ESTANDAR = [
    'codigo_institucion', 'nombre_institucion', 'ies_padre', 'tipo_ies',
    'id_sector', 'sector', 'id_caracter', 'caracter',
    'codigo_depto_ies', 'depto_ies', 'codigo_mcpio_ies', 'mcpio_ies',
    'ies_acreditada',
    'codigo_snies_programa', 'nombre_programa', 'programa_acreditado',
    'id_nivel', 'nivel', 'id_nivel_formacion', 'nivel_formacion',
    'id_metodologia', 'metodologia',
    'id_area', 'area_conocimiento', 'id_nucleo', 'nucleo_conocimiento',
    # Columnas CINE
    'id_cine_campo_amplio', 'desc_cine_campo_amplio',
    'id_cine_campo_especifico', 'desc_cine_campo_especifico',
    'id_cine_campo_detallado', 'desc_cine_campo_detallado',
    'codigo_depto_programa', 'depto_programa', 'codigo_mcpio_programa', 'mcpio_programa',
    'id_genero', 'genero',
    'anio', 'semestre', 'matriculados'
]

def normalizar_columna(col):
    """Normaliza nombre de columna"""
    if pd.isna(col):
        return ''
    return str(col).lower().strip().replace('\n', ' ').replace('\r', ' ')

def mapear_columnas(df):
    """Mapea columnas del DataFrame a nombres estandar"""
    mapeo = {}
    for col in df.columns:
        col_norm = normalizar_columna(col)
        
        # Buscar coincidencias
        if 'código de' in col_norm and 'instituci' in col_norm:
            mapeo[col] = 'codigo_institucion'
        elif 'institución de educación superior' in col_norm or 'institucion de educacion superior' in col_norm:
            mapeo[col] = 'nombre_institucion'
        elif 'ies padre' in col_norm:
            mapeo[col] = 'ies_padre'
        elif 'principal' in col_norm or 'tipo ies' in col_norm:
            mapeo[col] = 'tipo_ies'
        elif 'id sector' in col_norm:
            mapeo[col] = 'id_sector'
        elif col_norm == 'sector ies' or col_norm == 'sector':
            mapeo[col] = 'sector'
        elif 'id caracter' in col_norm or 'id caráct' in col_norm or 'id caracter' in col_norm:
            mapeo[col] = 'id_caracter'
        elif col_norm == 'caracter ies' or col_norm == 'caracter' or 'caráct' in col_norm:
            mapeo[col] = 'caracter'
        elif 'código del departamento' in col_norm and 'ies' in col_norm:
            mapeo[col] = 'codigo_depto_ies'
        elif 'departamento de domicilio' in col_norm:
            mapeo[col] = 'depto_ies'
        elif 'código del municipio' in col_norm and 'ies' in col_norm:
            mapeo[col] = 'codigo_mcpio_ies'
        elif 'municipio de domicilio' in col_norm:
            mapeo[col] = 'mcpio_ies'
        elif 'código snies del programa' in col_norm or 'codigo snies del programa' in col_norm:
            mapeo[col] = 'codigo_snies_programa'
        elif 'programa académico' in col_norm or 'programa academico' in col_norm:
            mapeo[col] = 'nombre_programa'
        elif 'id nivel' in col_norm and 'académ' in col_norm:
            mapeo[col] = 'id_nivel'
        elif col_norm == 'nivel académico' or col_norm == 'nivel academico':
            mapeo[col] = 'nivel'
        elif 'id nivel de formación' in col_norm or 'id nivel de formacion' in col_norm:
            mapeo[col] = 'id_nivel_formacion'
        elif 'nivel de formación' in col_norm or 'nivel de formacion' in col_norm:
            mapeo[col] = 'nivel_formacion'
        elif 'id metodolog' in col_norm or 'id modalidad' in col_norm:
            mapeo[col] = 'id_metodologia'
        elif 'metodolog' in col_norm or 'modalidad' in col_norm:
            mapeo[col] = 'metodologia'
        elif 'id área' in col_norm or 'id area' in col_norm:
            mapeo[col] = 'id_area'
        elif 'área de conocimiento' in col_norm or 'area de conocimiento' in col_norm:
            mapeo[col] = 'area_conocimiento'
        elif 'id núcleo' in col_norm or 'id nucleo' in col_norm:
            mapeo[col] = 'id_nucleo'
        elif 'núcleo básico' in col_norm or 'nucleo basico' in col_norm:
            mapeo[col] = 'nucleo_conocimiento'
        # Columnas CINE
        elif 'id cine campo amplio' in col_norm:
            mapeo[col] = 'id_cine_campo_amplio'
        elif 'desc cine campo amplio' in col_norm:
            mapeo[col] = 'desc_cine_campo_amplio'
        elif 'id cine campo especifico' in col_norm:
            mapeo[col] = 'id_cine_campo_especifico'
        elif 'desc cine campo especifico' in col_norm:
            mapeo[col] = 'desc_cine_campo_especifico'
        elif 'id cine codigo detallado' in col_norm or 'id cine campo detallado' in col_norm:
            mapeo[col] = 'id_cine_campo_detallado'
        elif 'desc cine codigo detallado' in col_norm or 'desc cine campo detallado' in col_norm:
            mapeo[col] = 'desc_cine_campo_detallado'
        # Columnas adicionales
        elif 'ies acreditada' in col_norm:
            mapeo[col] = 'ies_acreditada'
        elif 'programa acreditado' in col_norm:
            mapeo[col] = 'programa_acreditado'
        # Columnas de programa
        elif 'código del departamento' in col_norm and 'programa' in col_norm:
            mapeo[col] = 'codigo_depto_programa'
        elif 'departamento de oferta' in col_norm:
            mapeo[col] = 'depto_programa'
        elif 'código del municipio' in col_norm and 'programa' in col_norm:
            mapeo[col] = 'codigo_mcpio_programa'
        elif 'municipio de oferta' in col_norm:
            mapeo[col] = 'mcpio_programa'
        elif 'id género' in col_norm or 'id genero' in col_norm or 'id sexo' in col_norm:
            mapeo[col] = 'id_genero'
        elif col_norm == 'género' or col_norm == 'genero' or col_norm == 'sexo':
            mapeo[col] = 'genero'
        elif col_norm == 'año' or col_norm == 'ano':
            mapeo[col] = 'anio'
        elif col_norm == 'semestre':
            mapeo[col] = 'semestre'
        elif 'matriculados' in col_norm:
            mapeo[col] = 'matriculados'
    
    return mapeo

def estandarizar_genero(df):
    """Estandariza columna genero"""
    if 'genero' in df.columns:
        df['genero'] = df['genero'].astype(str).str.upper().str.strip()
        df['genero'] = df['genero'].replace(['M', 'MASCULINO', 'HOMBRE'], 'MASCULINO')
        df['genero'] = df['genero'].replace(['F', 'FEMENINO', 'MUJER'], 'FEMENINO')
    return df

def procesar_archivo(archivo, anio):
    """Procesa un archivo individual"""
    try:
        df = pd.read_parquet(archivo)
        print(f"  Procesando: {archivo.name} ({df.shape})")
        
        # Mapear columnas
        mapeo = mapear_columnas(df)
        df = df.rename(columns=mapeo)
        
        # Eliminar columnas duplicadas (mantener la primera ocurrencia)
        df = df.loc[:, ~df.columns.duplicated()]
        
        # Seleccionar solo columnas que pudimos mapear
        columnas_mapeadas = [c for c in df.columns if c in COLUMNAS_ESTANDAR]
        df = df[columnas_mapeadas]
        
        # Agregar anio si no existe
        if 'anio' not in df.columns:
            df['anio'] = anio
        
        # Estandarizar genero
        df = estandarizar_genero(df)
        
        # Asegurar que matriculados existe
        if 'matriculados' not in df.columns:
            # Buscar columna con el ano
            for col in df.columns:
                if 'matriculados' in col.lower():
                    df['matriculados'] = df[col]
                    break
        
        print(f"  Columnas despues de limpieza: {len(df.columns)}")
        return df
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

# ==========================================
# PROCESAMIENTO PRINCIPAL
# ==========================================
print("\nIniciando procesamiento de matriculados SNIES...")

# Procesar cada ano y guardar por separado
for anio in range(2015, 2025):
    print(f"\n{'='*50}")
    print(f"Procesando ano {anio}...")
    print(f"{'='*50}")
    
    anio_dir = RAW_MATRICULADOS / str(anio)
    if not anio_dir.exists():
        print(f"  Directorio no encontrado: {anio_dir}")
        continue
    
    archivos = list(anio_dir.glob("*.parquet"))
    print(f"  Archivos encontrados: {len(archivos)}")
    
    chunks = []
    for archivo in archivos:
        df = procesar_archivo(archivo, anio)
        if df is not None:
            chunks.append(df)
        del df
        gc.collect()
        time.sleep(1)
    
    if chunks:
        df_anio = pd.concat(chunks, ignore_index=True)
        print(f"  Total registros ano {anio}: {len(df_anio):,}")
        
        # Guardar por ano
        ruta_salida = PROCESSED_SNIES / f"matriculados_{anio}_limpio.parquet"
        df_anio.to_parquet(ruta_salida, index=False, compression='snappy')
        print(f"  Guardado: {ruta_salida.name}")
        
        del df_anio, chunks
        gc.collect()
        time.sleep(2)

# ==========================================
# CONCATENAR TODOS LOS ANOS
# ==========================================
print("\n" + "="*60)
print("Concatenando todos los anos...")
print("="*60)

# Leer todos los archivos guardados
archivos_limpiados = list(PROCESSED_SNIES.glob("matriculados_*_limpio.parquet"))
print(f"Archivos encontrados: {len(archivos_limpiados)}")

# Leer y concatenar
todos_los_datos = []
for archivo in sorted(archivos_limpiados):
    print(f"  Leyendo: {archivo.name}")
    df = pd.read_parquet(archivo)
    todos_los_datos.append(df)
    del df
    gc.collect()

if todos_los_datos:
    # Encontrar columnas comunes a todos
    columnas_comunes = set(todos_los_datos[0].columns)
    for df in todos_los_datos[1:]:
        columnas_comunes &= set(df.columns)
    
    print(f"\nColumnas comunes a todos los anos: {len(columnas_comunes)}")
    print(f"Columnas: {sorted(columnas_comunes)}")
    
    # Seleccionar solo columnas comunes
    todos_los_datos = [df[list(columnas_comunes)] for df in todos_los_datos]
    
    # Concatenar
    df_final = pd.concat(todos_los_datos, ignore_index=True)
    print(f"\nTotal registros consolidados: {len(df_final):,}")
    
    # Eliminar duplicados
    antes = len(df_final)
    df_final = df_final.drop_duplicates()
    print(f"Registros despues de eliminar duplicados: {len(df_final):,}")
    print(f"Duplicados eliminados: {antes - len(df_final):,}")
    
    # Guardar archivo final
    ruta_final = PROCESSED_SNIES / "matriculados_limpio_consolidado.parquet"
    df_final.to_parquet(ruta_final, index=False, compression='snappy')
    print(f"\nArchivo final guardado: {ruta_final.name}")
    
    # Estadisticas
    print(f"\n{'='*60}")
    print("ESTADISTICAS FINALES")
    print(f"{'='*60}")
    print(f"Total registros: {len(df_final):,}")
    print(f"Columnas: {len(df_final.columns)}")
    print(f"Anos cubiertos: {sorted(df_final['anio'].unique())}")
    print(f"Total matriculados: {df_final['matriculados'].sum():,}")
    if 'codigo_institucion' in df_final.columns:
        print(f"Instituciones unicas: {df_final['codigo_institucion'].nunique():,}")
    if 'codigo_snies_programa' in df_final.columns:
        print(f"Programas unicos: {df_final['codigo_snies_programa'].nunique():,}")
    if 'genero' in df_final.columns:
        print(f"Distribucion por genero:")
        print(df_final['genero'].value_counts().to_string())

print("\nProceso completado!")