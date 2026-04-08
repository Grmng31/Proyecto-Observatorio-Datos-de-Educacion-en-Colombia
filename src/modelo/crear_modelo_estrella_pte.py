import duckdb
from pathlib import Path
import os

print("=" * 80)
print("CREANDO MODELO ESTRELLA PTE - DUCKDB")
print("=" * 80)

# Rutas
BASE_DIR = Path(__file__).parent.parent.parent
PROCESSED_PTE = BASE_DIR / "datos" / "processed" / "pte"
MODELOS_DIR = BASE_DIR / "datos" / "processed" / "modelos" / "pte"

# Crear directorio
MODELOS_DIR.mkdir(parents=True, exist_ok=True)

# Ruta del DuckDB
db_path = MODELOS_DIR / "modelo_estrella_pte.duckdb"

# Eliminar si existe
if db_path.exists():
    os.remove(db_path)

# Conectar a DuckDB
conn = duckdb.connect(str(db_path))

print(f"\nBase de datos: {db_path}")

# ==========================================
# LEER PARQUETS EXISTENTES
# ==========================================
print("\n" + "="*60)
print("LEYENDO PARQUETS EXISTENTES...")
print("="*60)

# Leer dimensiones
dim_entidad = PROCESSED_PTE / "dimensiones" / "dim_entidad.parquet"
dim_rubro = PROCESSED_PTE / "dimensiones" / "dim_rubro.parquet"
dim_periodo = PROCESSED_PTE / "dimensiones" / "dim_periodo.parquet"
fact_presupuesto = PROCESSED_PTE / "hechos" / "fact_presupuesto.parquet"

print(f"\n  dim_entidad: {dim_entidad.exists()}")
print(f"  dim_rubro: {dim_rubro.exists()}")
print(f"  dim_periodo: {dim_periodo.exists()}")
print(f"  fact_presupuesto: {fact_presupuesto.exists()}")

# Crear tablas en DuckDB desde parquet
conn.execute(f"CREATE TABLE dim_entidad AS SELECT * FROM read_parquet('{dim_entidad}')")
conn.execute(f"CREATE TABLE dim_rubro AS SELECT * FROM read_parquet('{dim_rubro}')")
conn.execute(f"CREATE TABLE dim_periodo AS SELECT * FROM read_parquet('{dim_periodo}')")
conn.execute(f"CREATE TABLE fact_presupuesto AS SELECT * FROM read_parquet('{fact_presupuesto}')")

# ==========================================
# VERIFICAR RESULTADOS
# ==========================================
print("\n" + "="*60)
print("VERIFICANDO MODELO ESTRELLA PTE...")
print("="*60)

print("\nDimensiones:")
for tabla in ['dim_entidad', 'dim_rubro', 'dim_periodo']:
    count = conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    print(f"  {tabla}: {count:,} registros")

print(f"\nTabla de hechos:")
hechos = conn.execute("SELECT COUNT(*) FROM fact_presupuesto").fetchone()[0]
print(f"  fact_presupuesto: {hechos:,} registros")

# Estadisticas
print("\nEstadisticas de presupuesto:")
stats = conn.execute("""
SELECT 
    SUM(apropiacionvigente) as total_av,
    SUM(compromisos) as total_c,
    SUM(pagos) as total_p
FROM fact_presupuesto
""").fetchone()
print(f"  Total apropiacion vigente: ${stats[0]:,.0f}")
print(f"  Total compromisos: ${stats[1]:,.0f}")
print(f"  Total pagos: ${stats[2]:,.0f}")

# Tamaño del archivo
db_size = os.path.getsize(db_path) / (1024*1024)
print(f"\nTamano del archivo DuckDB: {db_size:.1f} MB")

conn.close()

print("\n" + "="*60)
print("MODELO ESTRELLA PTE CREADO EXITOSAMENTE")
print(f"Archivo: {db_path}")
print("="*60)