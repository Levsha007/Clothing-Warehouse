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

app = FastAPI(title="Склад одежды - СППР (Вариант 19)", version="3.0.0")

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
    tables = db.get_tables() or []
    table_counts = {t: db.get_table_count(t) for t in tables}
    return templates.TemplateResponse("index.html", {
        "request": request,
        "tables": tables,
        "table_counts": table_counts
    })

# ==================== РАБОТА С ДАННЫМИ ====================
@app.get("/data", response_class=HTMLResponse)
async def data_forms(request: Request, table: str = "", page: int = 1):
    tables = db.get_tables() or []
    columns, data, total_count = [], [], 0
    per_page = 50
    
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
        "tables": db.get_tables() or []
    })

@app.post("/api/query/execute")
async def execute_query(sql: str = Form(...), params: str = Form("{}")):
    try:
        params_dict = json.loads(params) if params else {}
        result = db.execute_query(sql, params_dict, fetch=True)
        return {
            "success": True,
            "data": result or [],
            "count": len(result) if result else 0
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/query/export")
async def export_query(sql: str = Form(...), params: str = Form("{}"), format: str = Form("csv")):
    try:
        params_dict = json.loads(params) if params else {}
        result = db.execute_query(sql, params_dict, fetch=True)
        
        if not result:
            return {"success": False, "error": "Нет данных"}
        
        if format == "csv":
            filepath, error = db.export_query_to_excel(result)
            if filepath:
                return FileResponse(filepath, filename=f"query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
            return {"success": False, "error": error}
        
        elif format == "json":
            return JSONResponse({
                "success": True,
                "data": result,
                "count": len(result)
            })
        
        return {"success": False, "error": "Неизвестный формат"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== СИСТЕМА ПОДДЕРЖКИ ПРИНЯТИЯ РЕШЕНИЙ ====================
@app.get("/spzr", response_class=HTMLResponse)
async def spzr_form(request: Request):
    """Форма СППР со всеми поставщиками и продукцией"""
    suppliers = db.execute_query("SELECT id, name FROM suppliers ORDER BY name")
    products = db.execute_query("SELECT id, name FROM products ORDER BY name")
    
    # Получаем список всех поставщиков и товаров для выпадающих списков
    all_suppliers = db.execute_query("""
        SELECT s.id, s.name, COUNT(DISTINCT pc.product_id) as product_count
        FROM suppliers s
        LEFT JOIN product_characteristics pc ON s.id = pc.supplier_id
        GROUP BY s.id, s.name
        ORDER BY s.name
    """)
    
    all_products = db.execute_query("""
        SELECT p.id, p.name, p.category, COUNT(DISTINCT pc.supplier_id) as supplier_count
        FROM products p
        LEFT JOIN product_characteristics pc ON p.id = pc.product_id
        GROUP BY p.id, p.name, p.category
        ORDER BY p.name
    """)
    
    return templates.TemplateResponse("spzr_form.html", {
        "request": request,
        "suppliers": suppliers or [],
        "products": products or [],
        "all_suppliers": all_suppliers or [],
        "all_products": all_products or []
    })

@app.post("/api/spzr/analyze")
async def analyze_quality(
    supplier_id: int = Form(...),
    product_id: int = Form(...),
    delta_x: Optional[float] = Form(None)
):
    """Универсальный анализ качества - автоматический расчет для любых данных"""
    
    # Получаем все характеристики для данного поставщика и продукта
    chars = db.execute_query("""
        SELECT 
            pc.id,
            c.id as characteristic_id,
            c.name AS char_name,
            c.unit,
            c.weight,
            c.delta_x_default,
            c.is_critical,
            pc.min_norm,
            pc.max_norm,
            pc.real_value
        FROM product_characteristics pc
        JOIN characteristics c ON pc.characteristic_id = c.id
        WHERE pc.product_id = %s AND pc.supplier_id = %s
        ORDER BY c.weight DESC, c.name
    """, (product_id, supplier_id))
    
    if not chars:
        return {"success": False, "error": "Нет данных по выбранной продукции"}
    
    # Информация о поставщике и продукте
    supplier = db.execute_query("SELECT name FROM suppliers WHERE id = %s", (supplier_id,))
    product = db.execute_query("SELECT name FROM products WHERE id = %s", (product_id,))
    
    # Расчет градаций для всех характеристик
    results = []
    total_gradations = 0
    sum_log2 = 0
    total_weight = 0
    weighted_sum = 0
    critical_defects = 0
    
    for ch in chars:
        x = float(ch['real_value'])
        xmin = float(ch['min_norm'])
        xmax = float(ch['max_norm'])
        dx = delta_x if delta_x is not None else float(ch['delta_x_default'] or 1.0)
        
        # Формула расчета градаций
        if xmin <= x <= xmax:
            g = 2  # в норме
            status = "Норма"
        elif x > xmax:
            g = int((x - xmin) / dx) + 1
            status = "Выше нормы"
        else:  # x < xmin
            g = int((xmax - x) / dx) + 1
            status = "Ниже нормы"
        
        # Ограничиваем разумные значения
        g = max(1, min(g, 100))
        
        # Проверка критических характеристик
        if ch['is_critical'] and (x < xmin or x > xmax):
            critical_defects += 1
        
        # Логарифм для сигнала отклонения
        log2_g = math.log2(g) if g > 0 else 0
        
        sum_log2 += log2_g
        total_gradations += g
        total_weight += ch['weight']
        weighted_sum += log2_g * ch['weight']
        
        results.append({
            'name': ch['char_name'],
            'unit': ch['unit'] or '-',
            'min': round(xmin, 1),
            'max': round(xmax, 1),
            'real': round(x, 1),
            'gradations': g,
            'log2': round(log2_g, 3),
            'weight': ch['weight'],
            'is_critical': ch['is_critical'],
            'status': status,
            'in_norm': xmin <= x <= xmax
        })
    
    n = len(chars)  # количество характеристик
    
    # Сигнал нормы (Ch)
    Ch = n
    
    # Сигнал отклонения (Co) - средневзвешенный
    if total_weight > 0:
        Co = weighted_sum / total_weight * n
    else:
        Co = sum_log2
    
    # Отношение отклонение/норма
    Go = Co / Ch if Ch > 0 else 0
    
    # Вероятность правильной классификации
    P = math.exp(- (Go ** 2) / 2)
    P = round(P, 4)
    
    # Интегральная оценка качества
    defect_percent = sum(1 for r in results if not r['in_norm']) / n * 100 if n > 0 else 0
    
    # Финальный вердикт:
    # - Критические дефекты -> брак
    # - Вероятность > 0.5 -> брак
    # - Более 30% характеристик вне нормы -> брак
    is_quality = (critical_defects == 0) and (P <= 0.5) and (defect_percent <= 30)
    
    verdict = "✓ ГОДЕН" if is_quality else "✗ БРАК"
    
    # Дополнительная информация
    quality_level = "Отличное" if P <= 0.3 else "Хорошее" if P <= 0.5 else "Сомнительное" if P <= 0.7 else "Плохое"
    
    return {
        "success": True,
        "supplier": supplier[0] if supplier else {"name": "Неизвестно"},
        "product": product[0] if product else {"name": "Неизвестно"},
        "characteristics": results,
        "metrics": {
            "n": n,
            "Ch": round(Ch, 3),
            "Co": round(Co, 3),
            "Go": round(Go, 3),
            "P": P,
            "is_quality": is_quality,
            "verdict": verdict,
            "quality_level": quality_level,
            "defect_percent": round(defect_percent, 1),
            "critical_defects": critical_defects,
            "delta_x": delta_x if delta_x else "auto"
        }
    }

@app.get("/api/spzr/all")
async def get_all_products_quality():
    """Анализ качества для всех продуктов всех поставщиков"""
    
    # Получаем все уникальные пары поставщик-продукт
    pairs = db.execute_query("""
        SELECT DISTINCT supplier_id, product_id
        FROM product_characteristics
        ORDER BY supplier_id, product_id
    """)
    
    results = []
    
    for pair in pairs or []:
        # Для каждой пары запускаем анализ
        analysis = await analyze_quality(pair['supplier_id'], pair['product_id'])
        if analysis.get('success'):
            results.append({
                'supplier_id': pair['supplier_id'],
                'product_id': pair['product_id'],
                'supplier_name': analysis['supplier']['name'],
                'product_name': analysis['product']['name'],
                'verdict': analysis['metrics']['verdict'],
                'is_quality': analysis['metrics']['is_quality'],
                'P': analysis['metrics']['P'],
                'defect_percent': analysis['metrics']['defect_percent']
            })
    
    return {
        "success": True,
        "total": len(results),
        "quality_count": sum(1 for r in results if r['is_quality']),
        "defect_count": sum(1 for r in results if not r['is_quality']),
        "results": results
    }

@app.get("/spzr/report", response_class=HTMLResponse)
async def spzr_report(
    request: Request,
    supplier_id: int,
    product_id: int,
    delta_x: Optional[float] = None
):
    """Отчет по качеству"""
    
    # Получаем анализ
    analysis = await analyze_quality(supplier_id, product_id, delta_x)
    
    if not analysis.get("success"):
        return HTMLResponse("Ошибка: " + analysis.get("error", ""))
    
    return templates.TemplateResponse("report.html", {
        "request": request,
        "supplier": analysis["supplier"],
        "product": analysis["product"],
        "characteristics": analysis["characteristics"],
        "metrics": analysis["metrics"],
        "delta_x": delta_x if delta_x else "авто",
        "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    })

@app.post("/api/spzr/train")
async def train_system(
    supplier_id: int = Form(...),
    product_id: int = Form(...),
    target_quality: bool = Form(...)
):
    """Обучение СППР - автоподбор delta_x"""
    
    best_delta = 1.0
    best_p = 0.5
    found = False
    
    # Поиск оптимального delta_x
    deltas_to_try = [0.1, 0.2, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
    
    for delta in deltas_to_try:
        analysis = await analyze_quality(supplier_id, product_id, delta)
        if analysis.get("success"):
            p = analysis["metrics"]["P"]
            is_quality = p <= 0.5
            
            if is_quality == target_quality:
                best_delta = delta
                best_p = p
                found = True
                break
    
    # Если не нашли, пробуем более тонкие значения
    if not found:
        fine_deltas = [0.01, 0.03, 0.05, 0.07, 0.09, 0.15, 0.25, 0.35, 0.45]
        for delta in fine_deltas:
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
async def export_all(format: str):
    tables = db.get_tables()
    if format == "excel":
        path, name = db.export_tables_to_excel(tables)
    else:
        path, name = db.export_tables_to_json(tables)
    
    if path:
        return FileResponse(path, filename=name)
    return {"success": False, "error": name}

# ==================== СЕРВИС ====================
@app.get("/service", response_class=HTMLResponse)
async def service_page(request: Request):
    return templates.TemplateResponse("service.html", {
        "request": request,
        "tables": db.get_tables() or []
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("APP_PORT", 3000))
    print(f"🚀 Сервер запущен на http://localhost:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)