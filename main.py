from fastapi import FastAPI, Request, Form, Depends, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
import json
import math
from datetime import datetime
import tempfile
from pathlib import Path

from database import Database

app = FastAPI(title="Склад одежды - Информационная система", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статика и шаблоны
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Глобальный экземпляр БД
db = Database()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def calculate_gradations(x, xmin, xmax, dx):
    """
    Правильный расчет градаций по методичке (стр. 35)
    
    n = 2, если значение в норме
    n = (x - xmax)/Δx + 1, если x > xmax
    n = (xmin - x)/Δx + 1, если x < xmin
    
    Важно: используем math.ceil для округления вверх
    """
    if xmin <= x <= xmax:
        return 2
    elif x > xmax:
        # Отклонение вверх
        diff = x - xmax
        n = math.ceil(diff / dx) + 1
        return max(2, min(n, 100))
    else:  # x < xmin
        # Отклонение вниз
        diff = xmin - x
        n = math.ceil(diff / dx) + 1
        return max(2, min(n, 100))

# ==================== ГЛАВНАЯ ====================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    tables = db.get_tables()
    table_counts = {t: db.get_table_count(t) for t in tables}
    return templates.TemplateResponse("index.html", {
        "request": request,
        "tables": tables,
        "table_counts": table_counts
    })

# ==================== ДОКУМЕНТАЦИЯ ====================
@app.get("/spzr/docs", response_class=HTMLResponse)
async def spzr_docs(request: Request):
    return templates.TemplateResponse("spzr_docs.html", {
        "request": request
    })

# ==================== СХЕМА ДАННЫХ ====================
@app.get("/schema", response_class=HTMLResponse)
async def schema_view(request: Request):
    """Страница со схемой данных"""
    return templates.TemplateResponse("schema.html", {
        "request": request
    })

@app.get("/api/schema/tables")
async def get_schema_tables():
    """Получить информацию о таблицах для схемы"""
    tables = db.get_tables()
    result = []
    
    for table in tables:
        # Получаем колонки
        columns = db.get_table_columns(table) or []
        
        # Получаем первичные ключи
        pk_query = """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_name = %s
        """
        pk_columns = db.execute_query(pk_query, (table,)) or []
        pk_set = {r['column_name'] for r in pk_columns}
        
        # Получаем внешние ключи
        fk_query = """
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = %s
        """
        fk_columns = db.execute_query(fk_query, (table,)) or []
        fk_set = {r['column_name'] for r in fk_columns}
        
        # Формируем список колонок с дополнительной информацией
        columns_info = []
        for col in columns:
            columns_info.append({
                'column_name': col['column_name'],
                'data_type': col['data_type'],
                'is_primary_key': col['column_name'] in pk_set,
                'is_foreign_key': col['column_name'] in fk_set,
                'is_nullable': col['is_nullable'],
                'foreign_key_info': next(
                    (r for r in fk_columns if r['column_name'] == col['column_name']),
                    None
                )
            })
        
        result.append({
            'name': table,
            'columns': columns_info
        })
    
    return JSONResponse(content=result)

@app.get("/api/schema/relationships")
async def get_relationships():
    """Получить все связи между таблицами"""
    query = """
        SELECT
            tc.table_name AS from_table,
            kcu.column_name AS from_column,
            ccu.table_name AS to_table,
            ccu.column_name AS to_column,
            rc.update_rule,
            rc.delete_rule
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
        LEFT JOIN information_schema.referential_constraints rc
            ON rc.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_name, kcu.ordinal_position
    """
    relationships = db.execute_query(query) or []
    
    result = []
    for rel in relationships:
        result.append({
            'from_table': rel['from_table'],
            'from_column': rel['from_column'],
            'to_table': rel['to_table'],
            'to_column': rel['to_column'],
            'update_rule': rel['update_rule'],
            'delete_rule': rel['delete_rule']
        })
    
    return JSONResponse(content=result)

@app.get("/api/schema/ddl")
async def get_schema_ddl():
    """Получить SQL DDL для всех таблиц"""
    tables = db.get_tables()
    ddl_parts = []
    
    for table in tables:
        # Получаем колонки
        columns = db.execute_query(f"""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
        """) or []
        
        col_defs = []
        for col in columns:
            null_str = "NOT NULL" if col['is_nullable'] == 'NO' else ""
            default_str = f"DEFAULT {col['column_default']}" if col['column_default'] else ""
            col_defs.append(f"    {col['column_name']} {col['data_type']} {null_str} {default_str}".strip())
        
        # Получаем первичный ключ
        pk = db.execute_query(f"""
            SELECT 
                kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_name = '{table}'
        """) or []
        
        if pk:
            pk_cols = [p['column_name'] for p in pk]
            col_defs.append(f"    PRIMARY KEY ({', '.join(pk_cols)})")
        
        # Получаем внешние ключи
        fk = db.execute_query(f"""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = '{table}'
        """) or []
        
        for f in fk:
            col_defs.append(
                f"    FOREIGN KEY ({f['column_name']}) REFERENCES {f['foreign_table']}({f['foreign_column']})"
            )
        
        ddl_parts.append(f"CREATE TABLE {table} (\n" + ",\n".join(col_defs) + "\n);\n")
    
    return JSONResponse(content={
        'ddl': '\n'.join(ddl_parts)
    })

# ==================== РАБОТА С ДАННЫМИ ====================
@app.get("/data", response_class=HTMLResponse)
async def data_forms(request: Request, table: str = "", page: int = 1):
    tables = db.get_tables()
    columns, data, total_count = [], [], 0
    per_page = 100
    
    if table and table in tables:
        columns = db.get_table_columns(table) or []
        total_count = db.get_table_count(table)
        offset = (page - 1) * per_page
        data = db.get_table_data(table, limit=per_page, offset=offset) or []
    
    total_pages = (total_count + per_page - 1) // per_page if total_count else 1
    
    return templates.TemplateResponse("data_forms.html", {
        "request": request,
        "tables": tables,
        "current_table": table,
        "columns": columns,
        "data": data,
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages
    })

@app.post("/api/data/insert")
async def insert_data(table: str = Form(...), data: str = Form(...)):
    try:
        data_dict = json.loads(data)
        result = db.insert_data(table, data_dict)
        if result:
            return {"success": True, "message": f"Добавлена запись с ID: {result}"}
        return {"success": False, "error": "Ошибка вставки"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/data/update")
async def update_data(table: str = Form(...), data: str = Form(...), condition: str = Form(...)):
    try:
        data_dict = json.loads(data)
        filtered = {k: v for k, v in data_dict.items() if v}
        if not filtered:
            return {"success": False, "error": "Нет данных"}
        result = db.update_data(table, filtered, condition)
        if result:
            return {"success": True, "message": "Обновлено"}
        return {"success": False, "error": "Не найдено"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/data/delete")
async def delete_data(table: str = Form(...), condition: str = Form(...), cascade: bool = Form(False)):
    try:
        if not condition:
            return {"success": False, "error": "Условие пусто"}
        if cascade:
            result = db.delete_data(table, condition)
            if result:
                return {"success": True, "message": "Удалено с каскадом"}
        else:
            result = db.delete_data_safe(table, condition)
            if isinstance(result, dict):
                if result.get('success'):
                    return {"success": True, "message": f"Удалено: {result.get('affected_rows', 0)}"}
                if result.get('error') == 'Есть зависимые записи':
                    return {
                        "success": False,
                        "error": "Есть зависимости",
                        "has_dependencies": True,
                        "dependencies": result.get('dependencies', [])
                    }
        return {"success": False, "error": "Ошибка удаления"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== КОНСТРУКТОР ЗАПРОСОВ ====================
@app.get("/query", response_class=HTMLResponse)
async def query_builder(request: Request):
    return templates.TemplateResponse("query_builder.html", {
        "request": request,
        "tables": db.get_tables()
    })

@app.post("/api/query/execute")
async def execute_query(sql: str = Form(...), params: str = Form("{}")):
    try:
        params_dict = json.loads(params) if params else {}
        result = db.execute_query(sql, params_dict, fetch=True)
        return {
            "success": True,
            "data": result,
            "count": len(result) if result else 0
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== АВТОМАТИЧЕСКАЯ СППР ====================
@app.get("/spzr", response_class=HTMLResponse)
async def spzr_dashboard(request: Request):
    return templates.TemplateResponse("spzr_dashboard.html", {
        "request": request
    })

@app.get("/api/spzr/characteristic-weights")
async def get_characteristic_weights():
    """Получить веса характеристик для круговой диаграммы"""
    query = """
        SELECT name, weight, description
        FROM characteristics
        ORDER BY weight DESC
    """
    chars = db.execute_query(query) or []
    return {
        "success": True,
        "characteristics": chars
    }

@app.get("/api/spzr/characteristic-stats")
async def get_characteristic_stats(delta_x: float = 1.0):
    """Получить статистику по характеристикам для заданного Δx"""
    
    chars_query = "SELECT id, name, delta_x_default FROM characteristics"
    chars = db.execute_query(chars_query) or []
    
    values_query = """
        SELECT 
            characteristic_id,
            real_value,
            min_norm,
            max_norm
        FROM product_characteristics
    """
    values = db.execute_query(values_query) or []
    
    stats = []
    for ch in chars:
        ch_values = [v for v in values if v['characteristic_id'] == ch['id']]
        if not ch_values:
            continue
        
        gradations = []
        for v in ch_values:
            g = calculate_gradations(
                v['real_value'],
                v['min_norm'],
                v['max_norm'],
                delta_x
            )
            gradations.append(g)
        
        avg_g = sum(gradations) / len(gradations) if gradations else 0
        
        stats.append({
            'id': ch['id'],
            'name': ch['name'],
            'avg_gradations': round(avg_g, 2),
            'count': len(gradations)
        })
    
    return {
        "success": True,
        "stats": stats,
        "delta_x": delta_x
    }

@app.get("/api/spzr/analyze-all")
async def analyze_all_quality(delta_x: float = 1.0):
    """Анализ качества всех продуктов от всех поставщиков с заданным Δx"""
    
    query = """
        SELECT DISTINCT 
            p.id as product_id,
            p.name as product_name,
            s.id as supplier_id,
            s.name as supplier_name,
            COUNT(pc.id) as characteristics_count
        FROM product_characteristics pc
        JOIN products p ON pc.product_id = p.id
        JOIN suppliers s ON pc.supplier_id = s.id
        GROUP BY p.id, p.name, s.id, s.name
        ORDER BY s.name, p.name
    """
    combinations = db.execute_query(query) or []
    
    results = []
    total_quality = 0
    total_defect = 0
    
    char_stats = {}
    
    for combo in combinations:
        chars_query = """
            SELECT 
                c.id,
                c.name,
                c.unit,
                c.delta_x_default,
                c.weight,
                pc.min_norm,
                pc.max_norm,
                pc.real_value
            FROM product_characteristics pc
            JOIN characteristics c ON pc.characteristic_id = c.id
            WHERE pc.product_id = %s AND pc.supplier_id = %s
        """
        chars = db.execute_query(chars_query, (combo['product_id'], combo['supplier_id'])) or []
        
        if not chars:
            continue
        
        # --- Базовый вердикт (Δx = 1.0) ---
        base_sum_log2 = 0
        n = len(chars)
        
        for ch in chars:
            g = calculate_gradations(
                ch['real_value'], 
                ch['min_norm'], 
                ch['max_norm'], 
                1.0  # базовый Δx
            )
            base_sum_log2 += math.log2(g)
        
        base_Go = base_sum_log2 / n if n > 0 else 0
        if base_Go > 0:
            base_P = math.exp(-math.log(2) / (base_Go * base_Go))
        else:
            base_P = math.exp(-math.log(2) / 0.0001)
        
        base_is_quality = base_P <= 0.5
        
        # --- Текущий расчет с заданным Δx ---
        char_results = []
        current_sum_log2 = 0
        
        for ch in chars:
            g = calculate_gradations(
                ch['real_value'], 
                ch['min_norm'], 
                ch['max_norm'], 
                delta_x
            )
            log2_g = math.log2(g)
            current_sum_log2 += log2_g
            
            if ch['id'] not in char_stats:
                char_stats[ch['id']] = {
                    'name': ch['name'],
                    'gradations': []
                }
            char_stats[ch['id']]['gradations'].append(g)
            
            char_results.append({
                'name': ch['name'],
                'unit': ch['unit'],
                'real': round(ch['real_value'], 2),
                'min': ch['min_norm'],
                'max': ch['max_norm'],
                'gradations': g,
                'log2': round(log2_g, 3),
                'weight': ch['weight'] or 1,
                'in_norm': ch['min_norm'] <= ch['real_value'] <= ch['max_norm']
            })
        
        current_Go = current_sum_log2 / n if n > 0 else 0
        if current_Go > 0:
            current_P = math.exp(-math.log(2) / (current_Go * current_Go))
        else:
            current_P = math.exp(-math.log(2) / 0.0001)
        
        if base_is_quality:
            total_quality += 1
        else:
            total_defect += 1
        
        results.append({
            'product_id': combo['product_id'],
            'product_name': combo['product_name'],
            'supplier_id': combo['supplier_id'],
            'supplier_name': combo['supplier_name'],
            'characteristics_count': combo['characteristics_count'],
            'characteristics': char_results[:3],
            'metrics': {
                'Ch': n,
                'Co': round(current_sum_log2, 3),
                'Go': round(current_Go, 3),
                'P': round(current_P, 4),
                'is_quality': base_is_quality,
                'base_P': round(base_P, 4)
            }
        })
    
    characteristic_stats = []
    for ch_id, stats in char_stats.items():
        avg_g = sum(stats['gradations']) / len(stats['gradations']) if stats['gradations'] else 0
        characteristic_stats.append({
            'id': ch_id,
            'name': stats['name'],
            'avg_gradations': round(avg_g, 2),
            'count': len(stats['gradations'])
        })
    
    return {
        "success": True,
        "total": len(results),
        "quality": total_quality,
        "defect": total_defect,
        "results": results,
        "characteristic_stats": characteristic_stats,
        "delta_x": delta_x
    }

@app.get("/api/spzr/product-detail")
async def get_product_detail(product_id: int, supplier_id: int, delta_x: float = 1.0):
    """Детальная информация о конкретном продукте"""
    
    info_query = """
        SELECT 
            p.name as product_name,
            p.category,
            p.description,
            s.name as supplier_name,
            s.address,
            s.phone
        FROM products p
        CROSS JOIN suppliers s
        WHERE p.id = %s AND s.id = %s
    """
    info = db.execute_query(info_query, (product_id, supplier_id))
    
    if not info:
        return {"success": False, "error": "Продукт не найден"}
    
    chars_query = """
        SELECT 
            c.id,
            c.name,
            c.unit,
            c.delta_x_default,
            c.weight,
            pc.min_norm,
            pc.max_norm,
            pc.real_value,
            pc.measurement_date
        FROM product_characteristics pc
        JOIN characteristics c ON pc.characteristic_id = c.id
        WHERE pc.product_id = %s AND pc.supplier_id = %s
        ORDER BY c.name
    """
    chars = db.execute_query(chars_query, (product_id, supplier_id)) or []
    
    char_results = []
    current_sum_log2 = 0
    base_sum_log2 = 0
    n = len(chars)
    
    for ch in chars:
        x = ch['real_value']
        xmin = ch['min_norm']
        xmax = ch['max_norm']
        
        # Базовые градации (для определения качества)
        base_g = calculate_gradations(x, xmin, xmax, 1.0)
        base_sum_log2 += math.log2(base_g)
        
        # Текущие градации (для отображения)
        current_g = calculate_gradations(x, xmin, xmax, delta_x)
        current_log2 = math.log2(current_g)
        current_sum_log2 += current_log2
        
        char_results.append({
            'name': ch['name'],
            'unit': ch['unit'],
            'real': round(x, 2),
            'min': xmin,
            'max': xmax,
            'gradations': current_g,
            'log2': round(current_log2, 3),
            'weight': ch['weight'] or 1,
            'in_norm': xmin <= x <= xmax
        })
    
    # Базовый вердикт
    base_Go = base_sum_log2 / n if n > 0 else 0
    if base_Go > 0:
        base_P = math.exp(-math.log(2) / (base_Go * base_Go))
    else:
        base_P = math.exp(-math.log(2) / 0.0001)
    
    is_quality = base_P <= 0.5
    
    # Текущие метрики
    current_Go = current_sum_log2 / n if n > 0 else 0
    if current_Go > 0:
        current_P = math.exp(-math.log(2) / (current_Go * current_Go))
    else:
        current_P = math.exp(-math.log(2) / 0.0001)
    
    # Подсчет отклонений для пояснения
    deviations = sum(1 for c in char_results if not c['in_norm'])
    
    return {
        "success": True,
        "product": info[0],
        "characteristics": char_results,
        "metrics": {
            "Ch": n,
            "Co": round(current_sum_log2, 3),
            "Go": round(current_Go, 3),
            "P": round(current_P, 4),
            "base_P": round(base_P, 4),
            "is_quality": is_quality,
            "verdict": "✓ КАЧЕСТВЕННЫЙ" if is_quality else "✗ БРАК"
        },
        "summary": {
            "total_chars": n,
            "deviations": deviations,
            "in_norm": n - deviations
        }
    }

@app.post("/api/spzr/train-all")
async def train_system_all():
    """Обучение СППР - подбор оптимального delta_x"""
    
    query = """
        SELECT DISTINCT product_id, supplier_id
        FROM product_characteristics
    """
    combos = db.execute_query(query) or []
    
    deltas = [0.1, 0.2, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 5.0]
    results = {}
    
    for delta in deltas:
        quality_count = 0
        total = 0
        
        for combo in combos:
            chars = db.execute_query("""
                SELECT 
                    real_value, min_norm, max_norm
                FROM product_characteristics
                WHERE product_id = %s AND supplier_id = %s
            """, (combo['product_id'], combo['supplier_id'])) or []
            
            if not chars:
                continue
            
            sum_log2 = 0
            n = len(chars)
            
            for ch in chars:
                g = calculate_gradations(
                    ch['real_value'],
                    ch['min_norm'],
                    ch['max_norm'],
                    delta
                )
                sum_log2 += math.log2(g)
            
            Ch = n
            Co = sum_log2
            Go = Co / Ch if Ch > 0 else 0
            
            if Go > 0:
                P = math.exp(-math.log(2) / (Go * Go))
            else:
                P = math.exp(-math.log(2) / 0.0001)
            
            if P <= 0.5:
                quality_count += 1
            total += 1
        
        quality_percent = (quality_count / total * 100) if total > 0 else 0
        results[delta] = {
            'quality': quality_count,
            'total': total,
            'percent': round(quality_percent, 1)
        }
    
    # Находим Δx, при котором доля качественных ближе всего к 50%
    best_delta = min(deltas, key=lambda d: abs(results[d]['percent'] - 50))
    
    return {
        "success": True,
        "best_delta": best_delta,
        "results": results
    }

@app.get("/api/spzr/export")
async def export_spzr_analysis(delta_x: float = 1.0, format: str = "json"):
    """Экспорт результатов СППР анализа в JSON или Excel"""
    
    analysis = await analyze_all_quality(delta_x)
    
    if not analysis.get("success"):
        return {"success": False, "error": "Ошибка анализа"}
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"spzr_analysis_delta{delta_x}_{timestamp}"
    
    if format == "json":
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "delta_x": delta_x,
            "summary": {
                "total": analysis["total"],
                "quality": analysis["quality"],
                "defect": analysis["defect"],
                "quality_percent": round(analysis["quality"] / analysis["total"] * 100, 2) if analysis["total"] > 0 else 0,
                "defect_percent": round(analysis["defect"] / analysis["total"] * 100, 2) if analysis["total"] > 0 else 0
            },
            "characteristic_stats": analysis.get("characteristic_stats", []),
            "results": analysis["results"]
        }
        
        export_dir = Path("exports") / datetime.now().strftime("%Y%m%d")
        export_dir.mkdir(parents=True, exist_ok=True)
        filepath = export_dir / f"{filename}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        
        return FileResponse(
            path=filepath,
            filename=f"{filename}.json",
            media_type="application/json"
        )
    
    elif format == "excel":
        import pandas as pd
        from io import BytesIO
        
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Результаты
            results_data = []
            for r in analysis["results"]:
                results_data.append({
                    "Поставщик": r["supplier_name"],
                    "Продукция": r["product_name"],
                    "Характеристик": r["characteristics_count"],
                    "Ch": r["metrics"]["Ch"],
                    "Co": r["metrics"]["Co"],
                    "Go": r["metrics"]["Go"],
                    "P": r["metrics"]["P"],
                    "Вердикт": "КАЧЕСТВЕННЫЙ" if r["metrics"]["is_quality"] else "БРАК"
                })
            
            if results_data:
                pd.DataFrame(results_data).to_excel(writer, sheet_name="Результаты", index=False)
            
            # Статистика по характеристикам
            chars_data = []
            for c in analysis.get("characteristic_stats", []):
                chars_data.append({
                    "Характеристика": c["name"],
                    "Средние градации": c["avg_gradations"],
                    "Количество измерений": c["count"]
                })
            
            if chars_data:
                pd.DataFrame(chars_data).to_excel(writer, sheet_name="Характеристики", index=False)
            
            # Сводка
            summary_data = {
                "Параметр": [
                    "Дата анализа",
                    "Δx",
                    "Всего позиций",
                    "Качественные",
                    "Брак",
                    "% качественных",
                    "% брака"
                ],
                "Значение": [
                    datetime.now().strftime("%d.%m.%Y %H:%M"),
                    delta_x,
                    analysis["total"],
                    analysis["quality"],
                    analysis["defect"],
                    round(analysis["quality"] / analysis["total"] * 100, 2) if analysis["total"] > 0 else 0,
                    round(analysis["defect"] / analysis["total"] * 100, 2) if analysis["total"] > 0 else 0
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name="Сводка", index=False)
        
        output.seek(0)
        
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
        )
    
    else:
        return {"success": False, "error": "Неверный формат"}

@app.get("/api/spzr/product-export")
async def export_product_detail(
    product_id: int, 
    supplier_id: int, 
    delta_x: float = 1.0,
    format: str = "json"
):
    """Экспорт детальной информации о продукте"""
    
    detail = await get_product_detail(product_id, supplier_id, delta_x)
    
    if not detail["success"]:
        return {"success": False, "error": detail.get("error", "Ошибка")}
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"product_{product_id}_{supplier_id}_delta{delta_x}_{timestamp}"
    
    if format == "json":
        # Подготовка данных для JSON с полной структурой как в интерфейсе
        is_quality = detail["metrics"]["is_quality"]
        
        # Формируем пояснение как в модальном окне
        if is_quality:
            explanation = {
                "title": "✅ Почему товар КАЧЕСТВЕННЫЙ, хотя есть отклонения?",
                "points": [
                    f"Несмотря на {detail['summary']['deviations']} отклонений из {detail['summary']['total_chars']}, система считает товар качественным, потому что:",
                    "Отклонения незначительны (малые градации n при базовом Δx=1.0)",
                    f"Вероятность P = {detail['metrics']['base_P']:.4f} ≤ 0.5 (по методичке стр. 38)",
                    f"Сигнал отклонения Co = {detail['metrics']['Co']} не превышает порог",
                    "Пороговое правило: P ≤ 0.5 → качественный"
                ]
            }
        else:
            explanation = {
                "title": "❌ Почему товар БРАК, если большинство характеристик в норме?",
                "points": [
                    f"Хотя только {detail['summary']['deviations']} из {detail['summary']['total_chars']} характеристик имеют отклонения, система считает товар браком, потому что:",
                    "Отклонения СИЛЬНЫЕ (большие градации n при базовом Δx=1.0)",
                    f"Вероятность P = {detail['metrics']['base_P']:.4f} > 0.5 (по методичке стр. 38)",
                    f"Сигнал отклонения Co = {detail['metrics']['Co']} превышает порог",
                    "Пороговое правило: P > 0.5 → брак"
                ]
            }
        
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "delta_x": delta_x,
            "product": {
                "name": detail["product"]["product_name"],
                "supplier": detail["product"]["supplier_name"],
                "category": detail["product"]["category"] or "—",
                "description": detail["product"]["description"] or "—",
                "address": detail["product"]["address"],
                "phone": detail["product"]["phone"]
            },
            "verdict": {
                "text": detail["metrics"]["verdict"],
                "is_quality": is_quality,
                "color": "success" if is_quality else "danger"
            },
            "explanation": explanation,
            "metrics": {
                "Ch": detail["metrics"]["Ch"],
                "Co": detail["metrics"]["Co"],
                "Go": round(detail["metrics"]["Go"], 3),
                "P_current": detail["metrics"]["P"],
                "P_base": detail["metrics"]["base_P"],
                "calculation": {
                    "ch_formula": f"Ch = N = {detail['metrics']['Ch']}",
                    "co_formula": f"Co = Σ log₂(nᵢ) = {detail['metrics']['Co']}",
                    "go_formula": f"Go = Co / Ch = {detail['metrics']['Co']} / {detail['metrics']['Ch']} = {round(detail['metrics']['Go'], 3)}",
                    "p_formula": f"P = e^(-ln2/Go²) = e^(-0.6931/{round(detail['metrics']['Go']**2, 3)}) = {detail['metrics']['P']:.4f}",
                    "note": "Базовое P (при Δx=1.0): {:.4f} — именно это значение определяет вердикт".format(detail['metrics']['base_P'])
                }
            },
            "summary": {
                "total_chars": detail["summary"]["total_chars"],
                "in_norm": detail["summary"]["in_norm"],
                "deviations": detail["summary"]["deviations"],
                "sum_log2": detail["metrics"]["Co"],
                "avg_go": round(detail["metrics"]["Go"], 3)
            },
            "characteristics": [],
            "analysis": {
                "title": "📊 Анализ градаций:",
                "points": [
                    f"Сумма log₂(n) = {detail['metrics']['Co']}",
                    f"Количество характеристик N = {detail['metrics']['Ch']}",
                    f"Отношение Go = {round(detail['metrics']['Go'], 3)}",
                    f"Вероятность P (текущая) = {detail['metrics']['P']:.4f}",
                    f"Базовое P (при Δx=1.0) = {detail['metrics']['base_P']:.4f}",
                    f"Правило: P {'≤ 0.5 → КАЧЕСТВЕННЫЙ' if is_quality else '> 0.5 → БРАК'}"
                ],
                "warning": "⚠️ Вердикт НЕ МЕНЯЕТСЯ при изменении Δx. Δx влияет только на отображение градаций."
            }
        }
        
        # Добавляем характеристики
        for c in detail["characteristics"]:
            export_data["characteristics"].append({
                "name": c["name"],
                "unit": c["unit"] or "-",
                "norm": f"{c['min']} — {c['max']}",
                "real": c["real"],
                "gradations": c["gradations"],
                "log2": c["log2"],
                "weight": c["weight"],
                "status": {
                    "text": "✓ в норме" if c["in_norm"] else "✗ отклонение",
                    "in_norm": c["in_norm"],
                    "color": "success" if c["in_norm"] else "danger"
                }
            })
        
        export_dir = Path("exports") / datetime.now().strftime("%Y%m%d")
        export_dir.mkdir(parents=True, exist_ok=True)
        filepath = export_dir / f"{filename}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        
        return FileResponse(
            path=filepath,
            filename=f"{filename}.json",
            media_type="application/json"
        )
    
    elif format == "excel":
        import pandas as pd
        from io import BytesIO
        
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # ========== ЛИСТ 1: Информация о продукте ==========
            product_info = [
                ["Параметр", "Значение"],
                ["Продукт", detail["product"]["product_name"]],
                ["Поставщик", detail["product"]["supplier_name"]],
                ["Категория", detail["product"]["category"] or "—"],
                ["Описание", detail["product"]["description"] or "—"],
                ["Адрес", detail["product"]["address"]],
                ["Телефон", detail["product"]["phone"]],
                ["Дата экспорта", datetime.now().strftime("%d.%m.%Y %H:%M:%S")],
                ["Δx (текущий)", delta_x],
                ["Вердикт", detail["metrics"]["verdict"]]
            ]
            pd.DataFrame(product_info).to_excel(writer, sheet_name="Информация", index=False, header=False)
            
            # ========== ЛИСТ 2: Пояснение ==========
            is_quality = detail["metrics"]["is_quality"]
            if is_quality:
                explanation_title = "✅ Почему товар КАЧЕСТВЕННЫЙ, хотя есть отклонения?"
                explanation_points = [
                    f"Несмотря на {detail['summary']['deviations']} отклонений из {detail['summary']['total_chars']}, система считает товар качественным, потому что:",
                    "Отклонения незначительны (малые градации n при базовом Δx=1.0)",
                    f"Вероятность P = {detail['metrics']['base_P']:.4f} ≤ 0.5 (по методичке стр. 38)",
                    f"Сигнал отклонения Co = {detail['metrics']['Co']} не превышает порог",
                    "Пороговое правило: P ≤ 0.5 → качественный"
                ]
            else:
                explanation_title = "❌ Почему товар БРАК, если большинство характеристик в норме?"
                explanation_points = [
                    f"Хотя только {detail['summary']['deviations']} из {detail['summary']['total_chars']} характеристик имеют отклонения, система считает товар браком, потому что:",
                    "Отклонения СИЛЬНЫЕ (большие градации n при базовом Δx=1.0)",
                    f"Вероятность P = {detail['metrics']['base_P']:.4f} > 0.5 (по методичке стр. 38)",
                    f"Сигнал отклонения Co = {detail['metrics']['Co']} превышает порог",
                    "Пороговое правило: P > 0.5 → брак"
                ]
            
            explanation_rows = [[explanation_title], [""]]
            for point in explanation_points:
                explanation_rows.append([point])
            
            pd.DataFrame(explanation_rows).to_excel(writer, sheet_name="Пояснение", index=False, header=False)
            
            # ========== ЛИСТ 3: Метрики и расчеты ==========
            metrics_data = [
                ["Показатель", "Значение", "Формула"],
                ["Ch (количество характеристик)", detail["metrics"]["Ch"], "Ch = N"],
                ["Co (сумма log₂(n))", detail["metrics"]["Co"], "Co = Σ log₂(nᵢ)"],
                ["Go (Co/Ch)", round(detail["metrics"]["Go"], 3), f"Go = {detail['metrics']['Co']} / {detail['metrics']['Ch']} = {round(detail['metrics']['Go'], 3)}"],
                ["P (текущая вероятность)", f"{detail['metrics']['P']:.4f}", f"P = e^(-ln2/Go²) = e^(-0.6931/{round(detail['metrics']['Go']**2, 3)})"],
                ["P (базовое, Δx=1.0)", f"{detail['metrics']['base_P']:.4f}", "Базовое значение для определения вердикта"],
                ["Правило", "P ≤ 0.5 → КАЧЕСТВЕННЫЙ" if is_quality else "P > 0.5 → БРАК", "по методичке стр. 38"]
            ]
            pd.DataFrame(metrics_data).to_excel(writer, sheet_name="Метрики", index=False, header=True)
            
            # ========== ЛИСТ 4: Характеристики ==========
            chars_data = []
            for c in detail["characteristics"]:
                chars_data.append({
                    "Характеристика": c["name"],
                    "Ед. изм.": c["unit"] or "-",
                    "Норма (min)": c["min"],
                    "Норма (max)": c["max"],
                    "Реальное значение": c["real"],
                    "Градации (n)": c["gradations"],
                    "log₂(n)": c["log2"],
                    "Вес": c["weight"],
                    "Статус": "✓ в норме" if c["in_norm"] else "✗ отклонение",
                    "Отклонение": "Нет" if c["in_norm"] else f"{'выше' if c['real'] > c['max'] else 'ниже'} нормы"
                })
            
            if chars_data:
                pd.DataFrame(chars_data).to_excel(writer, sheet_name="Характеристики", index=False)
            
            # ========== ЛИСТ 5: Анализ градаций ==========
            analysis_data = [
                ["Параметр", "Значение"],
                ["Сумма log₂(n)", detail["metrics"]["Co"]],
                ["Количество характеристик N", detail["metrics"]["Ch"]],
                ["Отношение Go", round(detail["metrics"]["Go"], 3)],
                ["Вероятность P (текущая)", f"{detail['metrics']['P']:.4f}"],
                ["Вероятность P (базовая)", f"{detail['metrics']['base_P']:.4f}"],
                ["Всего характеристик", detail["summary"]["total_chars"]],
                ["В норме", detail["summary"]["in_norm"]],
                ["Отклонений", detail["summary"]["deviations"]],
                ["Процент отклонений", f"{round(detail['summary']['deviations'] / detail['summary']['total_chars'] * 100, 1)}%"],
                [""],
                ["Правило определения:"],
                [f"P {'≤' if is_quality else '>'} 0.5 → {'КАЧЕСТВЕННЫЙ' if is_quality else 'БРАК'}"]
            ]
            pd.DataFrame(analysis_data).to_excel(writer, sheet_name="Анализ", index=False, header=False)
            
            # ========== ЛИСТ 6: Сводка ==========
            summary_data = [
                ["Показатель", "Значение"],
                ["Статус", detail["metrics"]["verdict"]],
                ["Всего характеристик", detail["summary"]["total_chars"]],
                ["В норме", detail["summary"]["in_norm"]],
                ["С отклонениями", detail["summary"]["deviations"]],
                ["Средний Go", round(detail["metrics"]["Go"], 3)],
                ["Вероятность P", f"{detail['metrics']['P']:.4f}"],
                ["Базовое P", f"{detail['metrics']['base_P']:.4f}"],
                ["Δx текущий", delta_x],
                [""],
                ["⚠️ Важно:"],
                ["Вердикт НЕ МЕНЯЕТСЯ при изменении Δx"],
                ["Δx влияет только на отображение градаций"]
            ]
            pd.DataFrame(summary_data).to_excel(writer, sheet_name="Сводка", index=False, header=False)
        
        output.seek(0)
        
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
        )
    
    else:
        return {"success": False, "error": "Неверный формат"}

# ==================== СЕРВИСНЫЕ ФУНКЦИИ ====================
@app.get("/service", response_class=HTMLResponse)
async def service_page(request: Request):
    return templates.TemplateResponse("service.html", {
        "request": request,
        "tables": db.get_tables()
    })

@app.post("/api/service/backup")
async def create_backup():
    success, path, error = db.create_backup()
    if success:
        return {"success": True, "message": f"Бэкап создан: {path}"}
    return {"success": False, "error": error}

@app.post("/api/service/restore")
async def restore_backup(file: UploadFile = File(...)):
    if not file.filename.endswith('.backup'):
        return {"success": False, "error": "Файл должен иметь расширение .backup"}
    
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".backup")
    temp.write(await file.read())
    temp.close()
    
    success, message = db.restore_backup(temp.name)
    os.unlink(temp.name)
    
    if success:
        return {"success": True, "message": message}
    return {"success": False, "error": message}

@app.post("/api/service/restore-sql")
async def restore_sql(file: UploadFile = File(...)):
    if not file.filename.endswith('.sql'):
        return {"success": False, "error": "Файл должен иметь расширение .sql"}
    
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".sql", mode='wb')
    temp.write(await file.read())
    temp.close()
    
    success, message = db.restore_from_sql(temp.name)
    os.unlink(temp.name)
    
    if success:
        return {"success": True, "message": message}
    return {"success": False, "error": message}

@app.post("/api/table/delete")
async def drop_table(table: str = Form(...)):
    if db.drop_table(table):
        return {"success": True, "message": f"Таблица '{table}' удалена"}
    return {"success": False, "error": "Ошибка удаления"}

@app.post("/api/service/archive")
async def archive_tables(tables: str = Form("[]"), archive_all: bool = Form(False)):
    tables_list = json.loads(tables) if not archive_all else db.get_tables()
    if not tables_list:
        return {"success": False, "error": "Нет таблиц"}
    success, result = db.archive_tables(tables_list)
    if success:
        return {
            "success": True,
            "message": result["message"],
            "archive_dir": result["archive_dir"],
            "tables_archived": result["tables_archived"],
            "details": result.get("details", [])
        }
    return {"success": False, "error": result}

# ==================== ЭКСПОРТ ====================
@app.get("/api/export/table/{table_name}/{format}")
async def export_table(table_name: str, format: str):
    if format == "excel":
        path, name = db.export_table_to_excel(table_name)
    elif format == "json":
        path, name = db.export_table_to_json(table_name)
    else:
        return {"success": False, "error": "Неверный формат"}
    
    if path:
        return FileResponse(path, filename=name)
    return {"success": False, "error": name}

@app.post("/api/export/tables")
async def export_tables(tables: List[str] = Form(...), format: str = Form("excel")):
    if format == "excel":
        path, name = db.export_tables_to_excel(tables)
    else:
        path, name = db.export_tables_to_json(tables)
    if path:
        return FileResponse(path, filename=name)
    return {"success": False, "error": name}

@app.get("/api/export/all/{format}")
async def export_all_tables(format: str):
    tables = db.get_tables()
    if format == "excel":
        path, name = db.export_tables_to_excel(tables)
    else:
        path, name = db.export_tables_to_json(tables)
    if path:
        return FileResponse(path, filename=name)
    return {"success": False, "error": name}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("APP_PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)