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
from models import init_db, get_db

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

# Инициализация БД при старте
@app.on_event("startup")
async def startup():
    init_db()

# ==================== ГЛАВНАЯ ====================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    db = get_db()
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
    db = get_db()
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
    db = get_db()
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
    db = get_db()
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
    db = get_db()
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
    db = get_db()
    return templates.TemplateResponse("query_builder.html", {
        "request": request,
        "tables": db.get_tables()
    })

@app.post("/api/query/execute")
async def execute_query(sql: str = Form(...), params: str = Form("{}")):
    db = get_db()
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

# ==================== СИСТЕМА ПОДДЕРЖКИ ПРИНЯТИЯ РЕШЕНИЙ ====================
@app.get("/spzr", response_class=HTMLResponse)
async def spzr_form(request: Request):
    db = get_db()
    suppliers = db.execute_query("SELECT id, name FROM suppliers ORDER BY name")
    products = db.execute_query("SELECT id, name FROM products ORDER BY name")
    return templates.TemplateResponse("spzr_form.html", {
        "request": request,
        "suppliers": suppliers or [],
        "products": products or []
    })

@app.post("/api/spzr/analyze")
async def analyze_quality(
    supplier_id: int = Form(...),
    product_id: int = Form(...),
    delta_x: float = Form(1.0)
):
    """Пороговый метод диагностики"""
    db = get_db()
    
    # 1. Получаем характеристики для конкретного продукта и поставщика
    query = """
        SELECT 
            pc.id,
            c.name as char_name,
            c.unit,
            pc.min_norm,
            pc.max_norm,
            pc.real_value,
            c.delta_x_default,
            c.weight
        FROM product_characteristics pc
        JOIN characteristics c ON pc.characteristic_id = c.id
        WHERE pc.product_id = %s AND pc.supplier_id = %s
    """
    chars = db.execute_query(query, (product_id, supplier_id))
    
    if not chars:
        return {"success": False, "error": "Нет данных по выбранной продукции"}
    
    # 2. Расчет градаций
    results = []
    total_gradations = 0
    sum_log2 = 0
    n = len(chars)
    
    for ch in chars:
        x = ch['real_value']
        xmin = ch['min_norm']
        xmax = ch['max_norm']
        dx = delta_x if delta_x else ch['delta_x_default'] or 1.0
        
        # Формула расчета градаций
        if xmin <= x <= xmax:
            g = 2
        elif x > xmax:
            g = int((x - xmin) / dx) + 1
        else:  # x < xmin
            g = int((xmax - x) / dx) + 1
        
        g = max(2, min(g, 100))  # Ограничим
        
        log2_g = math.log2(g) if g > 0 else 0
        sum_log2 += log2_g
        total_gradations += g
        
        results.append({
            'name': ch['char_name'],
            'unit': ch['unit'],
            'real': x,
            'min': xmin,
            'max': xmax,
            'gradations': g,
            'log2': round(log2_g, 3),
            'weight': ch['weight'] or 1
        })
    
    # 3. Показатели
    Ch = n  # сигнал нормы
    Co = sum_log2  # сигнал отклонения
    Go = Co / Ch if Ch > 0 else 0  # отношение
    
    # 4. Вероятность правильной классификации
    P = math.exp(- (Go ** 2) / 2)
    P = round(P, 4)
    
    # 5. Вывод о качестве
    is_quality = P <= 0.5
    
    return {
        "success": True,
        "characteristics": results,
        "metrics": {
            "n": n,
            "Ch": round(Ch, 3),
            "Co": round(Co, 3),
            "Go": round(Go, 3),
            "P": P,
            "is_quality": is_quality,
            "verdict": "✓ ГОДЕН" if is_quality else "✗ БРАК",
            "delta_x": delta_x
        }
    }

@app.get("/spzr/report", response_class=HTMLResponse)
async def spzr_report(
    request: Request,
    supplier_id: int,
    product_id: int,
    delta_x: float = 1.0
):
    """Отчет по качеству"""
    db = get_db()
    
    # Информация о поставщике и продукте
    supplier = db.execute_query("SELECT name FROM suppliers WHERE id = %s", (supplier_id,))
    product = db.execute_query("SELECT name FROM products WHERE id = %s", (product_id,))
    
    # Анализ
    from fastapi import Request
    analysis = await analyze_quality(supplier_id, product_id, delta_x)
    
    if not analysis.get("success"):
        return HTMLResponse("Ошибка: " + analysis.get("error", ""))
    
    return templates.TemplateResponse("report.html", {
        "request": request,
        "supplier": supplier[0] if supplier else {"name": "Неизвестно"},
        "product": product[0] if product else {"name": "Неизвестно"},
        "characteristics": analysis["characteristics"],
        "metrics": analysis["metrics"],
        "delta_x": delta_x,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    })

@app.post("/api/spzr/train")
async def train_system(
    supplier_id: int = Form(...),
    product_id: int = Form(...),
    target_quality: bool = Form(...),
    current_delta: float = Form(1.0)
):
    """Обучение СППР - подбор delta_x"""
    db = get_db()
    
    best_delta = current_delta
    best_p = 0.5
    found = False
    
    # Поиск подходящего delta_x
    for delta in [0.1, 0.2, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 5.0]:
        analysis = await analyze_quality(supplier_id, product_id, delta)
        if analysis.get("success"):
            p = analysis["metrics"]["P"]
            is_quality = p <= 0.5
            
            if is_quality == target_quality:
                best_delta = delta
                best_p = p
                found = True
                break
    
    if not found:
        # Жестче требования
        for delta in [0.01, 0.05, 0.1, 0.2, 0.5]:
            analysis = await analyze_quality(supplier_id, product_id, delta)
            if analysis.get("success"):
                p = analysis["metrics"]["P"]
                is_quality = p <= 0.5
                if is_quality == target_quality:
                    best_delta = delta
                    best_p = p
                    found = True
                    break
    
    return {
        "success": True,
        "found": found,
        "delta": best_delta,
        "probability": best_p
    }

# ==================== СЕРВИСНЫЕ ФУНКЦИИ ====================
@app.get("/service", response_class=HTMLResponse)
async def service_page(request: Request):
    db = get_db()
    return templates.TemplateResponse("service.html", {
        "request": request,
        "tables": db.get_tables()
    })

@app.post("/api/service/backup")
async def create_backup():
    db = get_db()
    success, path, error = db.create_backup()
    if success:
        return {"success": True, "message": f"Бэкап: {path}"}
    return {"success": False, "error": error}

@app.post("/api/service/restore")
async def restore_backup(file: UploadFile = File(...)):
    db = get_db()
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
    db = get_db()
    if db.drop_table(table):
        return {"success": True, "message": f"Таблица '{table}' удалена"}
    return {"success": False, "error": "Ошибка удаления"}

@app.post("/api/service/archive")
async def archive_tables(tables: str = Form("[]"), archive_all: bool = Form(False)):
    db = get_db()
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
    db = get_db()
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
    db = get_db()
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