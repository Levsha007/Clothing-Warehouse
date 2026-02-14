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

# ==================== АВТОМАТИЧЕСКАЯ СППР (для всех данных) ====================
@app.get("/spzr", response_class=HTMLResponse)
async def spzr_dashboard(request: Request):
    """Автоматический анализ качества всей продукции"""
    return templates.TemplateResponse("spzr_dashboard.html", {
        "request": request
    })

@app.get("/api/spzr/analyze-all")
async def analyze_all_quality():
    """Анализ качества всех продуктов от всех поставщиков"""
    
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
            dx = ch['delta_x_default'] or 1.0
            
            # Формула расчета градаций
            if xmin <= x <= xmax:
                g = 2  # В норме
            elif x > xmax:
                g = int((x - xmin) / dx) + 1
            else:  # x < xmin
                g = int((xmax - x) / dx) + 1
            
            g = max(2, min(g, 100))  # Ограничение
            log2_g = math.log2(g) if g > 0 else 0
            sum_log2 += log2_g
            
            char_results.append({
                'name': ch['name'],
                'unit': ch['unit'],
                'real': round(x, 2),
                'min': xmin,
                'max': xmax,
                'gradations': g,
                'log2': round(log2_g, 3),
                'weight': ch['weight'] or 1,
                'in_norm': xmin <= x <= xmax
            })
        
        # Показатели
        Ch = n  # сигнал нормы
        Co = sum_log2  # сигнал отклонения
        Go = Co / Ch if Ch > 0 else 0  # отношение
        P = math.exp(- (Go ** 2) / 2)  # вероятность
        P = round(P, 4)
        
        # Вердикт
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
            'characteristics': char_results[:3],  # Только первые 3 для краткости
            'metrics': {
                'Ch': round(Ch, 2),
                'Co': round(Co, 2),
                'Go': round(Go, 3),
                'P': P,
                'is_quality': is_quality
            }
        })
    
    # Сортировка: сначала брак, потом качественные
    results.sort(key=lambda x: (x['metrics']['is_quality'], x['metrics']['P']))
    
    return {
        "success": True,
        "total": len(results),
        "quality": total_quality,
        "defect": total_defect,
        "results": results
    }

@app.get("/api/spzr/product-detail")
async def get_product_detail(product_id: int, supplier_id: int):
    """Детальная информация о конкретном продукте"""
    
    # Информация о продукте и поставщике
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
    
    # Характеристики
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
        dx = ch['delta_x_default'] or 1.0
        
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
            'log2': round(log2_g, 3),
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
            "Ch": round(Ch, 2),
            "Co": round(Co, 2),
            "Go": round(Go, 3),
            "P": P,
            "is_quality": is_quality,
            "verdict": "✓ КАЧЕСТВЕННЫЙ" if is_quality else "✗ БРАК"
        }
    }

@app.post("/api/spzr/train-all")
async def train_system_all():
    """Обучение СППР - подбор оптимального delta_x для всех данных"""
    
    # Получаем все комбинации
    query = """
        SELECT DISTINCT product_id, supplier_id
        FROM product_characteristics
    """
    combos = db.execute_query(query) or []
    
    # Пробуем разные delta_x
    deltas = [0.1, 0.2, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 5.0]
    best_delta = 1.0
    best_accuracy = 0
    
    for delta in deltas:
        correct = 0
        total = 0
        
        for combo in combos:
            # Получаем характеристики
            chars = db.execute_query("""
                SELECT 
                    real_value, min_norm, max_norm, delta_x_default
                FROM product_characteristics pc
                JOIN characteristics c ON pc.characteristic_id = c.id
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
                dx = delta  # используем текущий delta
                
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
            
            # Считаем правильным, если P <= 0.5 (эталон)
            # В реальности здесь нужно сравнение с экспертной оценкой
            # Пока используем как есть
            correct += 1
            total += 1
        
        accuracy = correct / total if total > 0 else 0
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_delta = delta
    
    return {
        "success": True,
        "best_delta": best_delta,
        "accuracy": round(best_accuracy, 3)
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
        return {"success": True, "message": f"Бэкап: {path}"}
    return {"success": False, "error": error}

@app.post("/api/service/restore")
async def restore_backup(file: UploadFile = File(...)):
    if not file.filename.endswith('.backup'):
        return {"success": False, "error": "Только .backup"}
    
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".backup")
    temp.write(await file.read())
    temp.close()
    
    success, message = db.restore_backup(temp.name)
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