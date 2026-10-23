import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

sys.path.insert(0, os.getcwd())
from backend.app.core.config import settings
from backend.app.db.base import Base
import backend.app.models  # imports all models

async def verify_schema():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        print("=== VERIFYING DATABASE TABLES & COLUMNS AGAINST SQLALCHEMY MODELS ===")
        all_ok = True
        for table_name, table in Base.metadata.tables.items():
            res = await conn.execute(text(f"""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = '{table_name}';
            """))
            db_cols = {r[0]: (r[1], r[2]) for r in res.fetchall()}
            
            if not db_cols:
                print(f"[FAIL] Missing table: {table_name}")
                all_ok = False
                continue
                
            model_cols = set(table.columns.keys())
            missing_in_db = model_cols - set(db_cols.keys())
            if missing_in_db:
                print(f"[FAIL] Table '{table_name}' is missing columns in DB: {missing_in_db}")
                all_ok = False
            else:
                print(f"[OK] Table '{table_name}': all {len(model_cols)} columns present.")
                
        if all_ok:
            print("\n[SUCCESS] ALL MODEL TABLES AND COLUMNS FULLY EXIST AND MATCH IN SUPABASE!")
        else:
            print("\n[WARNING] Some tables or columns were missing!")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify_schema())
