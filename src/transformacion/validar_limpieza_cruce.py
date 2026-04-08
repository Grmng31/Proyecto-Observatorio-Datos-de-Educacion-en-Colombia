"""
Script de Validacion y Limpieza del Cruce ICFES (Saber 11 - Saber Pro)
======================================================================
Basado en validacion_datos.py original pero mejorado con:
- Eliminacion de duplicados
- Deteccion de outliers en puntajes
- Tratamiento de faltantes
- Generacion de reporte JSON en tests/
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

# Rutas
BASE_DIR = Path(__file__).parent.parent.parent
CRUCE_PATH = BASE_DIR / 'datos' / 'processed' / 'icfes' / 'cruce_saber_11_pro_completo.parquet'
TESTS_DIR = BASE_DIR / 'tests'
TESTS_DIR.mkdir(parents=True, exist_ok=True)

def validar_limpieza_cruce():
    print("=" * 80)
    print("VALIDACION Y LIMPIEZA DEL CRUCE ICFES")
    print("=" * 80)
    
    # Cargar datos
    print(f"\nCargando datos desde: {CRUCE_PATH}")
    df = pd.read_parquet(CRUCE_PATH)
    print(f"  Registros iniciales: {len(df):,}")
    print(f"  Columnas: {len(df.columns)}")
    
    reporte = {
        'fecha': datetime.now().isoformat(),
        'archivo': str(CRUCE_PATH),
        'registros_iniciales': len(df),
        'columnas': list(df.columns),
        'validaciones': {}
    }
    
    # 1. Resumen por ano
    print("\n" + "=" * 60)
    print("1. REGISTROS POR ANO")
    print("=" * 60)
    
    registros_por_ano = df['anio_sb11'].value_counts().sort_index().to_dict()
    print(f"\nRegistros por ano de Saber 11:")
    for ano, count in registros_por_ano.items():
        print(f"  {ano}: {count:,}")
    
    reporte['validaciones']['registros_por_ano'] = {str(k): v for k, v in registros_por_ano.items()}
    
    # 2. Verificacion de Nulos
    print("\n" + "=" * 60)
    print("2. VERIFICACION DE NULOS")
    print("=" * 60)
    
    nulos = df.isnull().sum()
    nulos_pct = (nulos / len(df) * 100).round(2)
    nulos_df = pd.DataFrame({'nulos': nulos, 'porcentaje': nulos_pct})
    nulos_df = nulos_df[nulos_df['nulos'] > 0]
    
    print(f"\nColumnas con valores nulos:")
    if len(nulos_df) > 0:
        for col, row in nulos_df.iterrows():
            print(f"  {col}: {row['nulos']:,} ({row['porcentaje']}%)")
    else:
        print("  No hay valores nulos")
    
    reporte['validaciones']['nulos'] = {
        col: {'count': int(row['nulos']), 'percentage': float(row['porcentaje'])}
        for col, row in nulos_df.iterrows()
    }
    
    # 3. Duplicados
    print("\n" + "=" * 60)
    print("3. DUPLICADOS")
    print("=" * 60)
    
    duplicados_antes = df.duplicated().sum()
    print(f"\nRegistros duplicados: {duplicados_antes:,}")
    
    if duplicados_antes > 0:
        df = df.drop_duplicates()
        print(f"  Se eliminaron {duplicados_antes:,} duplicados")
        print(f"  Registros despues de eliminar duplicados: {len(df):,}")
    
    reporte['validaciones']['duplicados'] = {
        'antes': int(duplicados_antes),
        'despues': 0
    }
    
    # 4. Outliers en puntajes
    print("\n" + "=" * 60)
    print("4. OUTLIERS EN PUNTAJES")
    print("=" * 60)
    
    # Convertir columnas de puntaje a numericas
    punt_cols = ['punt_global', 'punt_lenguaje', 'punt_matematicas', 'punt_ingles',
                 'mod_comuni_escrita_punt', 'mod_razona_cuantitat_punt', 'mod_ingles_punt', 'mod_competen_ciudada_punt']
    
    outliers_report = {}
    for col in punt_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
            outliers_pct = (outliers / len(df) * 100).round(2)
            
            print(f"\n  {col}:")
            print(f"    Rango normal: [{lower_bound:.2f}, {upper_bound:.2f}]")
            print(f"    Outliers: {outliers:,} ({outliers_pct}%)")
            
            outliers_report[col] = {
                'rango_normal': [round(float(lower_bound), 2), round(float(upper_bound), 2)],
                'outliers': int(outliers),
                'porcentaje': float(outliers_pct)
            }
    
    reporte['validaciones']['outliers_puntajes'] = outliers_report
    
    # 5. Top Instituciones
    print("\n" + "=" * 60)
    print("5. TOP INSTITUCIONES")
    print("=" * 60)
    
    if 'cole_nombre_establecimiento' in df.columns:
        top_inst = df['cole_nombre_establecimiento'].value_counts().head(10)
        print("\nTop 10 instituciones con mas registros:")
        for inst, count in top_inst.items():
            print(f"  {inst}: {count:,}")
        
        reporte['validaciones']['top_instituciones'] = {
            str(inst): int(count) for inst, count in top_inst.items()
        }
    
    # 6. Estadisticas descriptivas de puntajes
    print("\n" + "=" * 60)
    print("6. ESTADISTICAS DE PUNTAJES")
    print("=" * 60)
    
    stats_puntajes = {}
    for col in punt_cols:
        if col in df.columns and df[col].notna().sum() > 0:
            stats = df[col].describe()
            print(f"\n  {col}:")
            print(f"    Media: {stats['mean']:.2f}")
            print(f"    Mediana: {stats['50%']:.2f}")
            print(f"    Desviacion: {stats['std']:.2f}")
            print(f"    Min: {stats['min']:.2f}")
            print(f"    Max: {stats['max']:.2f}")
            
            stats_puntajes[col] = {
                'media': round(float(stats['mean']), 2),
                'mediana': round(float(stats['50%']), 2),
                'desviacion': round(float(stats['std']), 2),
                'min': round(float(stats['min']), 2),
                'max': round(float(stats['max']), 2)
            }
    
    reporte['validaciones']['estadisticas_puntajes'] = stats_puntajes
    
    # 7. Guardar datos limpios
    print("\n" + "=" * 60)
    print("7. GUARDANDO DATOS LIMPIOS")
    print("=" * 60)
    
    cruce_limpio_path = CRUCE_PATH.parent / 'cruce_saber_11_pro_limpio.parquet'
    df.to_parquet(cruce_limpio_path, index=False)
    print(f"\nDatos limpios guardados en: {cruce_limpio_path}")
    print(f"  Registros finales: {len(df):,}")
    
    reporte['registros_finales'] = len(df)
    reporte['archivo_limpio'] = str(cruce_limpio_path)
    
    # 8. Generar JSON de validacion
    validate_json_path = TESTS_DIR / 'validate_cruce.json'
    with open(validate_json_path, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)
    
    print(f"\nReporte de validacion guardado en: {validate_json_path}")
    
    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN DE VALIDACION")
    print("=" * 80)
    print(f"  Registros iniciales: {reporte['registros_iniciales']:,}")
    print(f"  Registros finales: {reporte['registros_finales']:,}")
    print(f"  Duplicados eliminados: {reporte['validaciones']['duplicados']['antes']}")
    print(f"  Columnas con nulos: {len(reporte['validaciones']['nulos'])}")
    print(f"  Archivo limpio: {cruce_limpio_path.name}")
    print(f"  Reporte JSON: {validate_json_path.name}")
    print("=" * 80)
    
    return reporte

if __name__ == "__main__":
    validar_limpieza_cruce()