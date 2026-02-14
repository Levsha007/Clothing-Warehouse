from fastapi import FastAPI, Request, Form, Depends, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
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
    
    # Получаем все характеристики
    chars_query = "SELECT id, name, delta_x_default FROM characteristics"
    chars = db.execute_query(chars_query) or []
    
    # Получаем все значения product_characteristics
    values_query = """
        SELECT 
            characteristic_id,
            real_value,
            min_norm,
            max_norm
        FROM product_characteristics
    """
    values = db.execute_query(values_query) or []
    
    # Группируем по характеристикам
    stats = []
    for ch in chars:
        ch_values = [v for v in values if v['characteristic_id'] == ch['id']]
        if not ch_values:
            continue
        
        gradations = []
        for v in ch_values:
            x = v['real_value']
            xmin = v['min_norm']
            xmax = v['max_norm']
            dx = delta_x
            
            if xmin <= x <= xmax:
                g = 2
            elif x > xmax:
                g = int((x - xmin) / dx) + 1
            else:
                g = int((xmax - x) / dx) + 1
            
            g = max(2, min(g, 100))
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
    
    # 1. Получаем все уникальные комбинации продукт-поставщик
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
    
    # Для статистики по характеристикам
    char_stats = {}
    
    for combo in combinations:
        # Получаем характеристики для этой комбинации
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
        
        # Расчет градаций и показателей
        char_results = []
        sum_log2 = 0
        n = len(chars)
        
        for ch in chars:
            x = ch['real_value']
            xmin = ch['min_norm']
            xmax = ch['max_norm']
            dx = delta_x  # используем переданный delta_x
            
            if xmin <= x <= xmax:
                g = 2
            elif x > xmax:
                g = int((x - xmin) / dx) + 1
            else:
                g = int((xmax - x) / dx) + 1
            
            g = max(2, min(g, 100))
            log2_g = math.log2(g) if g > 0 else 0
            sum_log2 += log2_g
            
            # Собираем статистику
            if ch['id'] not in char_stats:
                char_stats[ch['id']] = {
                    'name': ch['name'],
                    'gradations': []
                }
            char_stats[ch['id']]['gradations'].append(g)
            
            char_results.append({
                'name': ch['name'],
                'unit': ch['unit'],
                'real': round(x, 2),
                'min': xmin,
                'max': xmax,
                'gradations': g,
                'log2': log2_g,
                'weight': ch['weight'] or 1,
                'in_norm': xmin <= x <= xmax
            })
        
        Ch = n
        Co = sum_log2
        Go = Co / Ch if Ch > 0 else 0
        P = math.exp(- (Go ** 2) / 2)
        P = round(P, 4)
        
        is_quality = P <= 0.5
        
        if is_quality:
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
                'Ch': Ch,
                'Co': round(Co, 3),
                'Go': round(Go, 3),
                'P': P,
                'is_quality': is_quality
            }
        })
    
    # Подготавливаем статистику по характеристикам для диаграммы
    characteristic_stats = []
    for ch_id, stats in char_stats.items():
        avg_g = sum(stats['gradations']) / len(stats['gradations']) if stats['gradations'] else 0
        characteristic_stats.append({
            'id': ch_id,
            'name': stats['name'],
            'avg_gradations': round(avg_g, 2),
            'count': len(stats['gradations'])
        })
    
    results.sort(key=lambda x: (x['metrics']['is_quality'], x['metrics']['P']))
    
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
    sum_log2 = 0
    n = len(chars)
    
    for ch in chars:
        x = ch['real_value']
        xmin = ch['min_norm']
        xmax = ch['max_norm']
        dx = delta_x
        
        if xmin <= x <= xmax:
            g = 2
        elif x > xmax:
            g = int((x - xmin) / dx) + 1
        else:
            g = int((xmax - x) / dx) + 1
        
        g = max(2, min(g, 100))
        log2_g = math.log2(g) if g > 0 else 0
        sum_log2 += log2_g
        
        char_results.append({
            'name': ch['name'],
            'unit': ch['unit'],
            'real': round(x, 2),
            'min': xmin,
            'max': xmax,
            'gradations': g,
            'log2': log2_g,
            'weight': ch['weight'] or 1,
            'in_norm': xmin <= x <= xmax
        })
    
    Ch = n
    Co = sum_log2
    Go = Co / Ch if Ch > 0 else 0
    P = round(math.exp(- (Go ** 2) / 2), 4)
    is_quality = P <= 0.5
    
    return {
        "success": True,
        "product": info[0],
        "characteristics": char_results,
        "metrics": {
            "Ch": Ch,
            "Co": round(Co, 3),
            "Go": round(Go, 3),
            "P": P,
            "is_quality": is_quality,
            "verdict": "✓ КАЧЕСТВЕННЫЙ" if is_quality else "✗ БРАК"
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
                x = ch['real_value']
                xmin = ch['min_norm']
                xmax = ch['max_norm']
                dx = delta
                
                if xmin <= x <= xmax:
                    g = 2
                elif x > xmax:
                    g = int((x - xmin) / dx) + 1
                else:
                    g = int((xmax - x) / dx) + 1
                
                g = max(2, min(g, 100))
                sum_log2 += math.log2(g)
            
            Ch = n
            Co = sum_log2
            Go = Co / Ch if Ch > 0 else 0
            P = math.exp(- (Go ** 2) / 2)
            
            if P <= 0.5:
                quality_count += 1
            total += 1
        
        quality_percent = (quality_count / total * 100) if total > 0 else 0
        results[delta] = {
            'quality': quality_count,
            'total': total,
            'percent': round(quality_percent, 1)
        }
    
    best_delta = min(deltas, key=lambda d: abs(results[d]['percent'] - 50))
    
    return {
        "success": True,
        "best_delta": best_delta,
        "results": results
    }

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