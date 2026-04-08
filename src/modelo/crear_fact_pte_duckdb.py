#!/usr/bin/env python3
"""
Script para crear fact_ejecucion_presupuestal en DuckDB
Implementa la tabla de hechos de PTE segun requerimientos
"""

import duckdb
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
DATOS_DIR = BASE_DIR / "datos" / "processed"
DUCKDB_PATH = BASE_DIR / "datos" / "observatorio_educacion.duckdb"

def crear_fact_pte():
    """Crea tabla de hechos PTE en DuckDB"""
    print("Creando fact_ejecucion_presupuestal en DuckDB...")
    
    conn = duckdb.connect(str(DUCKDB_PATH))
    
    # Leer fact_presupuesto existente
    fact_pte = pd.read_parquet(DATOS_DIR / "pte" / "hechos" / "fact_presupuesto.parquet")
    
    # Crear tabla en DuckDB
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fact_ejecucion_presupuestal (
            id_entidad INTEGER,
            id_rubro INTEGER,
            id_periodo INTEGER,
            apropiacioninicial DOUBLE,
            apropiacionvigente DOUBLE,
            compromisos DOUBLE,
            obligaciones DOUBLE,
            pagos DOUBLE
        )
    """)
    
    # Insertar datos
    conn.execute("INSERT INTO fact_ejecucion_presupuestal SELECT * FROM fact_pte")
    
    # Guardar como parquet tambien
    output_path = DATOS_DIR / "fact_pte.parquet"
    fact_pte.to_parquet(output_path, index=False)
    
    print(f"  fact_ejecucion_presupuestal creada con {len(fact_pte)} registros")
    print(f"  Guardado en: {output_path}")
    
    conn.close()

if __name__ == "__main__":
    crear_fact_pte()