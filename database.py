import os
import psycopg2
import subprocess
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime
import json
import pandas as pd
import shutil
from pathlib import Path
import math

load_dotenv()

class Database:
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('DB_HOST', 'postgres'),
            'database': os.getenv('DB_NAME', 'clothing_warehouse'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres'),
            'port': os.getenv('DB_PORT', '5432')
        }
        self.pg_dump = "pg_dump"
        self.pg_restore = "pg_restore"
        self.psql = "psql"  # Добавляем psql для SQL файлов
        self._init_dirs()
    
    def _init_dirs(self):
        self.dirs = {
            'backups': Path("backups"),
            'exports': Path("exports"),
            'archives': Path("archives")
        }
        for d in self.dirs.values():
            d.mkdir(exist_ok=True)
    
    def _timestamp_dir(self, base):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        p = base / ts
        p.mkdir(parents=True, exist_ok=True)
        return p
    
    def get_connection(self, dict_cursor=True):
        try:
            return psycopg2.connect(
                **self.connection_params,
                cursor_factory=RealDictCursor if dict_cursor else None
            )
        except Exception as e:
            print(f"DB conn error: {e}")
            return None
    
    def execute_query(self, query, params=None, fetch=True):
        conn = self.get_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                if fetch and cur.description:
                    res = cur.fetchall()
                else:
                    res = None
                conn.commit()
                return res
        except Exception as e:
            conn.rollback()
            print(f"Query error: {e}\n{query}")
            return None
        finally:
            conn.close()
    
    def execute_sql_file(self, filepath):
        """Выполнить SQL файл через psql"""
        try:
            db = os.getenv('DB_NAME', 'clothing_warehouse')
            user = os.getenv('DB_USER', 'postgres')
            host = os.getenv('DB_HOST', 'postgres')
            port = os.getenv('DB_PORT', '5432')
            
            cmd = [
                self.psql,
                '-h', host,
                '-U', user,
                '-p', port,
                '-d', db,
                '-f', filepath,
                '-v', 'ON_ERROR_STOP=1'
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = os.getenv('DB_PASSWORD', 'postgres')
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return True, "SQL файл успешно выполнен"
            else:
                return False, result.stderr
                
        except Exception as e:
            return False, str(e)
    
    def get_tables(self):
        q = "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"
        res = self.execute_query(q)
        return [r['table_name'] for r in res] if res else []
    
    def get_table_columns(self, table):
        q = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = %s ORDER BY ordinal_position
        """
        return self.execute_query(q, (table,))
    
    def get_table_count(self, table):
        q = f"SELECT COUNT(*) as c FROM {table}"
        res = self.execute_query(q)
        return res[0]['c'] if res else 0
    
    def get_table_data(self, table, limit=None, offset=0):
        if limit:
            q = f"SELECT * FROM {table} LIMIT %s OFFSET %s"
            return self.execute_query(q, (limit, offset))
        return self.execute_query(f"SELECT * FROM {table}")
    
    def insert_data(self, table, data):
        cols = ', '.join(data.keys())
        ph = ', '.join(['%s'] * len(data))
        q = f"INSERT INTO {table} ({cols}) VALUES ({ph}) RETURNING id"
        res = self.execute_query(q, tuple(data.values()))
        return res[0]['id'] if res else None
    
    def update_data(self, table, data, condition):
        set_clause = ', '.join([f"{k}=%s" for k in data.keys()])
        q = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        conn = self.get_connection(dict_cursor=False)
        if not conn: return None
        try:
            with conn.cursor() as cur:
                cur.execute(q, tuple(data.values()))
                conn.commit()
                return cur.rowcount > 0
        except:
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def delete_data(self, table, condition):
        conn = self.get_connection(dict_cursor=False)
        if not conn: return None
        try:
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM {table} WHERE {condition}")
                conn.commit()
                return cur.rowcount > 0
        except:
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def delete_data_safe(self, table, condition):
        """Проверка зависимостей перед удалением"""
        conn = self.get_connection(dict_cursor=False)
        if not conn:
            return {'success': False, 'error': 'No connection'}
        
        try:
            with conn.cursor() as cur:
                # Получаем внешние ключи
                fk_query = """
                    SELECT
                        tc.table_name,
                        kcu.column_name,
                        ccu.table_name AS parent_table,
                        ccu.column_name AS parent_column
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND ccu.table_name = %s
                """
                cur.execute(fk_query, (table,))
                refs = cur.fetchall()
                
                dependencies = []
                for ref in refs:
                    child = ref[0]
                    child_col = ref[1]
                    check = f"""
                        SELECT COUNT(*) FROM {child}
                        WHERE {child_col} IN (
                            SELECT id FROM {table} WHERE {condition}
                        )
                    """
                    cur.execute(check)
                    cnt = cur.fetchone()[0]
                    if cnt > 0:
                        dependencies.append({'table': child, 'count': cnt})
                
                if dependencies:
                    return {
                        'success': False,
                        'error': 'Есть зависимые записи',
                        'dependencies': dependencies
                    }
                
                cur.execute(f"DELETE FROM {table} WHERE {condition}")
                conn.commit()
                return {'success': True, 'affected_rows': cur.rowcount}
                
        except Exception as e:
            conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def drop_table(self, table):
        conn = self.get_connection(dict_cursor=False)
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                conn.commit()
                return True
        except:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ---------- Экспорт ----------
    def export_table_to_excel(self, table):
        try:
            data = self.get_table_data(table)
            if not data:
                return None, "Нет данных"
            d = self._timestamp_dir(self.dirs['exports'])
            f = d / f"{table}_{datetime.now().strftime('%H%M%S')}.xlsx"
            pd.DataFrame(data).to_excel(str(f), index=False)
            return str(f), f.name
        except Exception as e:
            return None, str(e)
    
    def export_table_to_json(self, table):
        try:
            data = self.get_table_data(table)
            if not data:
                return None, "Нет данных"
            d = self._timestamp_dir(self.dirs['exports'])
            f = d / f"{table}_{datetime.now().strftime('%H%M%S')}.json"
            with open(f, 'w', encoding='utf-8') as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2, default=str)
            return str(f), f.name
        except Exception as e:
            return None, str(e)
    
    def export_tables_to_excel(self, tables):
        try:
            d = self._timestamp_dir(self.dirs['exports'])
            f = d / f"export_{datetime.now().strftime('%H%M%S')}.xlsx"
            with pd.ExcelWriter(str(f), engine='openpyxl') as writer:
                for t in tables:
                    data = self.get_table_data(t)
                    if data:
                        pd.DataFrame(data).to_excel(writer, sheet_name=t[:31], index=False)
            return str(f), f.name
        except Exception as e:
            return None, str(e)
    
    def export_tables_to_json(self, tables):
        try:
            d = self._timestamp_dir(self.dirs['exports'])
            f = d / f"export_{datetime.now().strftime('%H%M%S')}.json"
            out = {}
            for t in tables:
                data = self.get_table_data(t)
                if data:
                    out[t] = data
            with open(f, 'w', encoding='utf-8') as fp:
                json.dump(out, fp, ensure_ascii=False, indent=2, default=str)
            return str(f), f.name
        except Exception as e:
            return None, str(e)
    
    # ---------- Backup / Restore ----------
    def create_backup(self):
        try:
            db = os.getenv('DB_NAME', 'clothing_warehouse')
            user = os.getenv('DB_USER', 'postgres')
            host = os.getenv('DB_HOST', 'postgres')
            port = os.getenv('DB_PORT', '5432')
            d = self._timestamp_dir(self.dirs['backups'])
            f = d / f"backup_{db}_{datetime.now().strftime('%H%M%S')}.backup"
            
            cmd = [
                self.pg_dump, '-h', host, '-U', user, '-p', port,
                '-d', db, '-F', 'c', '-f', str(f)
            ]
            env = os.environ.copy()
            env['PGPASSWORD'] = os.getenv('DB_PASSWORD', 'postgres')
            
            res = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if res.returncode == 0:
                return True, str(f), None
            return False, None, res.stderr
        except Exception as e:
            return False, None, str(e)
    
    def restore_backup(self, backup_file):
        """Восстановление из .backup файла"""
        try:
            db = os.getenv('DB_NAME', 'clothing_warehouse')
            user = os.getenv('DB_USER', 'postgres')
            host = os.getenv('DB_HOST', 'postgres')
            port = os.getenv('DB_PORT', '5432')
            
            cmd = [
                self.pg_restore, '-h', host, '-U', user, '-p', port,
                '-d', db, '--clean', '--if-exists', backup_file
            ]
            env = os.environ.copy()
            env['PGPASSWORD'] = os.getenv('DB_PASSWORD', 'postgres')
            
            res = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if res.returncode == 0:
                return True, "Восстановление из .backup выполнено"
            # Игнорируем ошибку transaction_timeout
            if "transaction_timeout" in res.stderr:
                return True, "Восстановление с предупреждениями"
            return False, res.stderr
        except Exception as e:
            return False, str(e)
    
    def restore_from_sql(self, sql_file):
        """Восстановление из SQL файла (например init.sql)"""
        try:
            return self.execute_sql_file(sql_file)
        except Exception as e:
            return False, str(e)
    
    def create_table_backup(self, table, backup_dir):
        try:
            db = os.getenv('DB_NAME', 'clothing_warehouse')
            user = os.getenv('DB_USER', 'postgres')
            host = os.getenv('DB_HOST', 'postgres')
            port = os.getenv('DB_PORT', '5432')
            
            f = backup_dir / f"backup_{table}_{datetime.now().strftime('%H%M%S')}.backup"
            cmd = [
                self.pg_dump, '-h', host, '-U', user, '-p', port,
                '-d', db, '-t', table, '-F', 'c', '-f', str(f)
            ]
            env = os.environ.copy()
            env['PGPASSWORD'] = os.getenv('DB_PASSWORD', 'postgres')
            
            res = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if res.returncode == 0:
                return True, str(f), None
            return False, None, res.stderr
        except Exception as e:
            return False, None, str(e)
    
    def archive_tables(self, tables):
        try:
            arch_dir = self._timestamp_dir(self.dirs['archives'])
            results = []
            success_count = 0
            
            for t in tables:
                try:
                    # 1. Backup
                    ok, bf, err = self.create_table_backup(t, arch_dir)
                    if not ok:
                        results.append(f"Таблица {t}: ошибка backup - {err}")
                        continue
                    
                    # 2. Excel
                    ef = arch_dir / f"{t}_{datetime.now().strftime('%H%M%S')}.xlsx"
                    data = self.get_table_data(t)
                    rows = len(data) if data else 0
                    if data:
                        pd.DataFrame(data).to_excel(str(ef), index=False)
                    
                    # 3. JSON
                    jf = arch_dir / f"{t}_{datetime.now().strftime('%H%M%S')}.json"
                    with open(jf, 'w', encoding='utf-8') as fp:
                        json.dump(data, fp, ensure_ascii=False, indent=2, default=str)
                    
                    # 4. Drop
                    if self.drop_table(t):
                        success_count += 1
                        results.append({
                            'table': t,
                            'rows_archived': rows,
                            'backup_file': os.path.basename(bf),
                            'excel_file': ef.name,
                            'json_file': jf.name,
                            'status': 'success'
                        })
                    else:
                        results.append(f"Таблица {t}: не удалось удалить")
                        
                except Exception as e:
                    results.append(f"Таблица {t}: {str(e)}")
            
            return True, {
                'message': f"Архивация: {success_count}/{len(tables)}",
                'archive_dir': str(arch_dir),
                'tables_archived': success_count,
                'total_tables': len(tables),
                'details': results
            }
        except Exception as e:
            return False, str(e)
    
    def archive_all_tables(self):
        return self.archive_tables(self.get_tables())

def get_db():
    return Database()