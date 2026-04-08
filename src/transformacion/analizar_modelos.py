import duckdb

print("=" * 60)
print("ANALISIS DE MODELOS ESTRELLA")
print("=" * 60)

# PTE
print("\n=== PTE ===")
con = duckdb.connect('datos/processed/modelos/pte/modelo_estrella_pte.duckdb', read_only=True)
for table in ['dim_periodo', 'dim_entidad', 'fact_presupuesto']:
    print(f"\n{table}:")
    cols = con.execute(f'DESCRIBE {table}').fetchall()
    print(f"  Columnas: {[c[0] for c in cols]}")
    sample = con.execute(f'SELECT * FROM {table} LIMIT 3').fetchall()
    print(f"  Ejemplo: {sample}")

# SABER
print("\n=== SABER ===")
con = duckdb.connect('datos/processed/modelos/saber/modelo_estrella_saber.duckdb', read_only=True)
for table in ['dim_periodo', 'dim_institucion', 'fact_resultados_saber']:
    print(f"\n{table}:")
    cols = con.execute(f'DESCRIBE {table}').fetchall()
    print(f"  Columnas: {[c[0] for c in cols]}")
    sample = con.execute(f'SELECT * FROM {table} LIMIT 3').fetchall()
    print(f"  Ejemplo: {sample}")

# SNIES
print("\n=== SNIES ===")
con = duckdb.connect('datos/processed/modelos/snies/modelo_estrella_snies.duckdb', read_only=True)
for table in ['fact_matriculas']:
    print(f"\n{table}:")
    cols = con.execute(f'DESCRIBE {table}').fetchall()
    print(f"  Columnas: {[c[0] for c in cols]}")
    sample = con.execute(f'SELECT * FROM {table} LIMIT 3').fetchall()
    print(f"  Ejemplo: {sample}")