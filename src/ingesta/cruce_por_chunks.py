"""
Script de Cruce ICFES por Chunks 
--------------------------------------------------------
Usa el mapeo como diccionario y columnas basicas.
"""

import pandas as pd
from pathlib import Path
import logging
import gc
from datetime import datetime

# Configuracion de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rutas base
BASE_DIR = Path(__file__).parent.parent.parent
RAW_ICFES_11 = BASE_DIR / "datos" / "raw" / "icfes" / "saber_11"
RAW_ICFES_PRO = BASE_DIR / "datos" / "raw" / "icfes" / "saber_pro"
CRUCE_FILE = BASE_DIR / "cruce" / "Cruce_Examen_Saber_11_Examen_Saber_Pro.txt"
PROCESSED_DIR = BASE_DIR / "datos" / "processed" / "icfes"

def procesar_cruce_por_chunks():
    """Procesa el cruce ano por ano para no saturar memoria."""
    logger.info("="*60)
    logger.info("INICIANDO CRUCE POR CHUNKS - VERSION SIMPLIFICADA")
    logger.info("="*60)
    
    # Crear directorio de salida
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    # Paso 1: Cargar archivo de mapeo completo
    logger.info("Cargando archivo de mapeo completo...")
    df_mapeo = pd.read_csv(CRUCE_FILE, sep=';', encoding='utf-8', low_memory=False)
    logger.info(f"Mapeo cargado: {len(df_mapeo):,} registros")
    
    # Paso 2: Procesar por periodos exactos (semestre)
    logger.info("\n--- PROCESANDO POR PERIODOS EXACTOS ---")
    
    # Obtener periodos unicos del mapeo
    df_mapeo['anio_sb11'] = df_mapeo['periodo_sb11'].astype(str).str[:4]
    df_mapeo['anio_sbpro'] = df_mapeo['periodo_sbpro'].astype(str).str[:4]
    
    periodos_unicos_11 = sorted(df_mapeo['periodo_sb11'].unique())
    periodos_unicos_pro = sorted(df_mapeo['periodo_sbpro'].unique())
    
    logger.info(f"Periodos SB11 en mapeo: {len(periodos_unicos_11)}")
    logger.info(f"Periodos SBPRO en mapeo: {len(periodos_unicos_pro)}")
    
    resultados_parciales = []
    
    # Procesar cada periodo de Saber 11
    for periodo_11 in periodos_unicos_11:
        anio_11 = str(periodo_11)[:4]
        logger.info(f"\n--- Procesando periodo SB11: {periodo_11} (ano {anio_11}) ---")
        
        # Obtener mapeo para este periodo especifico
        mapeo_periodo = df_mapeo[df_mapeo['periodo_sb11'] == periodo_11]
        
        # Cargar datos de Saber 11 de este ano
        archivo_11 = RAW_ICFES_11 / anio_11 / f"saber11_{anio_11}_consolidado.parquet"
        if not archivo_11.exists():
            logger.warning(f"  Archivo Saber 11 {anio_11} no encontrado")
            continue
        
        # Columnas basicas de Saber 11 (algunas pueden no existir, usamos alternativas)
        columnas_basicas_11 = ['estu_consecutivo', 'periodo', 'estu_genero',
                               'cole_cod_dane_establecimiento', 'cole_nombre_establecimiento',
                               'punt_lenguaje', 'punt_matematicas', 'punt_ingles']
        
        # Columnas opcionales (pueden no existir)
        columnas_opcionales_11 = ['estu_edad', 'estu_fechanacimiento']
        
        # Columnas de ubicacion (pueden tener nombres diferentes por ano)
        columnas_ubicacion = ['estu_depto_presentacion', 'estu_mcpio_presentacion',
                              'cole_cod_depto_ubicacion', 'cole_cod_mcpio_ubicacion']
        
        # Leer primero columnas basicas
        try:
            df_11 = pd.read_parquet(archivo_11, columns=columnas_basicas_11)
        except Exception as e:
            logger.error(f"  Error cargando Saber 11: {e}")
            continue
        
        # Agregar columnas opcionales que existan
        for col in columnas_opcionales_11:
            try:
                df_col = pd.read_parquet(archivo_11, columns=[col])
                df_11[col] = df_col[col]
            except:
                pass  # Columna no existe
        
        # Agregar columnas de ubicacion que existan
        for col in columnas_ubicacion:
            try:
                df_col = pd.read_parquet(archivo_11, columns=[col])
                df_11[col] = df_col[col]
            except:
                pass  # Columna no existe
        
        # Estandarizar nombres de columnas de ubicacion
        if 'estu_depto_presentacion' not in df_11.columns and 'cole_cod_depto_ubicacion' in df_11.columns:
            df_11['estu_depto_presentacion'] = df_11['cole_cod_depto_ubicacion']
        if 'estu_mcpio_presentacion' not in df_11.columns and 'cole_cod_mcpio_ubicacion' in df_11.columns:
            df_11['estu_mcpio_presentacion'] = df_11['cole_cod_mcpio_ubicacion']
        
        # Calcular edad si no existe pero existe fecha de nacimiento
        if 'estu_edad' not in df_11.columns and 'estu_fechanacimiento' in df_11.columns:
            from datetime import datetime
            try:
                df_11['estu_fechanacimiento'] = pd.to_datetime(df_11['estu_fechanacimiento'], errors='coerce', dayfirst=True)
                hoy = datetime.now()
                df_11['estu_edad'] = ((hoy - df_11['estu_fechanacimiento']).dt.days // 365).astype(str)
                logger.info(f"    estu_edad calculada desde estu_fechanacimiento")
            except:
                df_11['estu_edad'] = ''  # Edad desconocida
        
        # Asegurar que estu_edad exista y sea string (aunque sea vacio)
        if 'estu_edad' not in df_11.columns:
            df_11['estu_edad'] = ''
        else:
            df_11['estu_edad'] = df_11['estu_edad'].astype(str).fillna('')
        
        # Convertir estu_fechanacimiento a string para evitar errores de pyarrow
        if 'estu_fechanacimiento' in df_11.columns:
            df_11['estu_fechanacimiento'] = df_11['estu_fechanacimiento'].astype(str).fillna('')
        
        logger.info(f"  Saber 11 cargado: {len(df_11):,} registros")
        
        # Procesar cada periodo de Saber Pro relacionado con este periodo de Saber 11
        periodos_pro_relacionados = mapeo_periodo['periodo_sbpro'].unique()
        
        for periodo_pro in periodos_pro_relacionados:
            anio_pro = str(periodo_pro)[:4]
            logger.info(f"    Cruzando con SBPRO periodo: {periodo_pro} (ano {anio_pro})")
            
            # Obtener mapeo especifico para esta combinacion exacta de periodos
            mapeo_especifico = mapeo_periodo[mapeo_periodo['periodo_sbpro'] == periodo_pro]
            
            # Cargar datos de Saber Pro
            archivo_pro = RAW_ICFES_PRO / anio_pro / f"saber_pro_{anio_pro}_consolidado.parquet"
            if not archivo_pro.exists():
                logger.warning(f"    Archivo Saber Pro {anio_pro} no encontrado")
                continue
            
            # Columnas basicas de Saber Pro (algunas pueden no existir)
            columnas_basicas_pro = ['estu_consecutivo', 'periodo', 'estu_genero',
                                    'estu_depto_presentacion', 'estu_mcpio_presentacion']
            
            # Columnas de puntajes (pueden variar por ano)
            columnas_puntajes_pro = ['mod_comuni_escrita_punt', 'mod_razona_cuantitat_punt',
                                     'mod_ingles_punt', 'mod_competen_ciudada_punt',
                                     'punt_global', 'percentil_global']
            
            # Leer primero columnas basicas
            try:
                df_pro = pd.read_parquet(archivo_pro, columns=columnas_basicas_pro)
            except Exception as e:
                logger.error(f"    Error cargando Saber Pro: {e}")
                continue
            
            # Agregar columnas de puntajes que existan
            for col in columnas_puntajes_pro:
                try:
                    df_col = pd.read_parquet(archivo_pro, columns=[col])
                    df_pro[col] = df_col[col]
                except:
                    # Columna no existe, la creamos como NaN
                    df_pro[col] = float('nan')
            
            # Calcular punt_global si no existe (promedio de areas)
            if 'punt_global' in df_pro.columns and df_pro['punt_global'].isna().all():
                areas = ['mod_comuni_escrita_punt', 'mod_razona_cuantitat_punt',
                         'mod_ingles_punt', 'mod_competen_ciudada_punt']
                areas_existentes = [a for a in areas if a in df_pro.columns]
                if areas_existentes:
                    df_pro['punt_global'] = df_pro[areas_existentes].mean(axis=1)
                    logger.info(f"    punt_global calculado como promedio de {len(areas_existentes)} areas")
            
            logger.info(f"    Saber Pro cargado: {len(df_pro):,} registros")
            
            # Convertir periodos a string para evitar errores de tipo
            mapeo_especifico['periodo_sb11'] = mapeo_especifico['periodo_sb11'].astype(str)
            mapeo_especifico['periodo_sbpro'] = mapeo_especifico['periodo_sbpro'].astype(str)
            
            # FILTRAR datos por los consecutivos del mapeo
            consecutivos_11_mapeo = mapeo_especifico['estu_consecutivo_sb11'].unique()
            consecutivos_pro_mapeo = mapeo_especifico['estu_consecutivo_sbpro'].unique()
            
            # Filtrar datos por los consecutivos del mapeo
            df_11_filtrado = df_11[df_11['estu_consecutivo'].isin(consecutivos_11_mapeo)].copy()
            df_pro_filtrado = df_pro[df_pro['estu_consecutivo'].isin(consecutivos_pro_mapeo)].copy()
            
            # Convertir periodos a string para evitar errores de tipo
            if df_11_filtrado['periodo'].dtype == 'int64':
                df_11_filtrado['periodo'] = df_11_filtrado['periodo'].astype(str)
            if df_pro_filtrado['periodo'].dtype == 'int64':
                df_pro_filtrado['periodo'] = df_pro_filtrado['periodo'].astype(str)
            
            logger.info(f"    SB11 filtrados: {len(df_11_filtrado):,}")
            logger.info(f"    SBPRO filtrados: {len(df_pro_filtrado):,}")
            
            if len(df_11_filtrado) == 0 or len(df_pro_filtrado) == 0:
                logger.warning(f"    No hay coincidencias")
                continue
            
            # HACER EL CRUCE USANDO EL MAPEO
            df_cruce_11 = mapeo_especifico.merge(
                df_11_filtrado,
                left_on=['periodo_sb11', 'estu_consecutivo_sb11'],
                right_on=['periodo', 'estu_consecutivo'],
                how='inner',
                suffixes=('_mapeo', '_11')
            )
            logger.info(f"    Cruce SB11: {len(df_cruce_11):,}")
            
            df_cruce_final = df_cruce_11.merge(
                df_pro_filtrado,
                left_on=['periodo_sbpro', 'estu_consecutivo_sbpro'],
                right_on=['periodo', 'estu_consecutivo'],
                how='inner',
                suffixes=('_11', '_pro')
            )
            logger.info(f"    Cruce final: {len(df_cruce_final):,}")
            
            if len(df_cruce_final) > 0:
                resultados_parciales.append(df_cruce_final)
                logger.info(f"    ✅ Guardado")
            
            # Liberar memoria
            del df_11_filtrado, df_pro_filtrado, df_cruce_11, df_cruce_final
            gc.collect()
        
        # Liberar memoria
        del df_11
        gc.collect()
    
    # Paso 3: Unir todos los resultados
    logger.info("\n--- UNIENDO RESULTADOS ---")
    
    if resultados_parciales:
        df_final = pd.concat(resultados_parciales, ignore_index=True)
        logger.info(f"Total registros cruzados: {len(df_final):,}")
        
        # Guardar resultado
        archivo_final = PROCESSED_DIR / "cruce_saber_11_pro_completo.parquet"
        df_final.to_parquet(archivo_final, index=False)
        logger.info(f"✅ Cruce guardado en: {archivo_final}")
        
        # Resumen
        logger.info(f"\n--- RESUMEN ---")
        logger.info(f"  Total registros cruzados: {len(df_final):,}")
        logger.info(f"  Columnas: {len(df_final.columns)}")
        
        return df_final
    else:
        logger.error("No se encontraron registros para cruzar")
        return None

if __name__ == "__main__":
    df_resultado = procesar_cruce_por_chunks()