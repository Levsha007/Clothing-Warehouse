from database import get_db

def init_db():
    """Инициализация базы данных для склада одежды (Вариант 19)"""
    db = get_db()
    
    # 1. Поставщики (не менее 6)
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            address TEXT,
            phone VARCHAR(20),
            contact_person VARCHAR(100),
            inn VARCHAR(12),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """, fetch=False)
    
    # 2. Продукция (не менее 4 наименований)
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            category VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """, fetch=False)
    
    # 3. Характеристики (не менее 5 для одежды)
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS characteristics (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            unit VARCHAR(20),
            delta_x_default FLOAT DEFAULT 0.5,
            weight INTEGER DEFAULT 20,
            description TEXT
        )
    """, fetch=False)
    
    # 4. Связь: продукт-поставщик-характеристики с нормами и реальными значениями
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS product_characteristics (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
            supplier_id INTEGER REFERENCES suppliers(id) ON DELETE CASCADE,
            characteristic_id INTEGER REFERENCES characteristics(id) ON DELETE CASCADE,
            min_norm FLOAT NOT NULL,
            max_norm FLOAT NOT NULL,
            real_value FLOAT NOT NULL,
            measurement_date TIMESTAMP DEFAULT NOW(),
            UNIQUE(product_id, supplier_id, characteristic_id)
        )
    """, fetch=False)
    
    # ============ ЗАПОЛНЕНИЕ ДАННЫМИ ============
    
    # Поставщики (6+)
    suppliers = [
        ("ООО 'Текстиль-Импорт'", "г. Москва, ул. Ткацкая, 15", "+7 (495) 123-45-67", "Иванов П.С.", "7712345678"),
        ("АО 'Мода-Стиль'", "г. Санкт-Петербург, пр. Невский, 45", "+7 (812) 234-56-78", "Петрова Е.В.", "7812345678"),
        ("ИП 'Силуэт'", "г. Новосибирск, ул. Советская, 12", "+7 (383) 345-67-89", "Сидоров А.Н.", "5412345678"),
        ("Швейная фабрика 'Элегант'", "г. Екатеринбург, ул. Машиностроителей, 8", "+7 (343) 456-78-90", "Козлова О.И.", "6612345678"),
        ("Торговый дом 'Кашемир'", "г. Казань, ул. Баумана, 23", "+7 (843) 567-89-01", "Смирнов Д.К.", "1612345678"),
        ("ООО 'Джинс-Маркет'", "г. Воронеж, ул. Ленина, 30", "+7 (473) 678-90-12", "Васильева Н.А.", "3612345678"),
        ("Фабрика 'Классика'", "г. Самара, ул. Промышленная, 5", "+7 (846) 789-01-23", "Федоров И.П.", "6312345678"),
    ]
    for sup in suppliers:
        db.execute_query("""
            INSERT INTO suppliers (name, address, phone, contact_person, inn)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING
        """, sup, fetch=False)
    
    # Продукция (4+ наименований одежды)
    products = [
        ("Джинсы мужские классические", "Прямые джинсы, синий деним", "Брюки"),
        ("Рубашка женская офисная", "Белая, хлопок 100%", "Блузы"),
        ("Куртка демисезонная", "Плащевка, утеплитель", "Верхняя одежда"),
        ("Футболка хлопковая", "Оверсайз, принт", "Трикотаж"),
        ("Платье-футляр", "Черное, эластан", "Платья"),
        ("Костюм спортивный", "Флис, трикотаж", "Спорт"),
    ]
    for prod in products:
        db.execute_query("""
            INSERT INTO products (name, description, category)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO NOTHING
        """, prod, fetch=False)
    
    # Характеристики качества для одежды (5+)
    chars = [
        ("Состав ткани", "%", 1.0, 25, "Процентное содержание основного волокна"),
        ("Плотность ткани", "г/м²", 10.0, 20, "Вес квадратного метра"),
        ("Устойчивость окраски", "баллы", 0.5, 20, "По 5-балльной шкале"),
        ("Усадка после стирки", "%", 0.5, 15, "Процент усадки"),
        ("Прочность швов", "Н/см", 5.0, 20, "Ньютон на сантиметр"),
        ("Соответствие размеру", "мм", 2.0, 25, "Отклонение от заявленного"),
        ("Качество упаковки", "баллы", 0.5, 15, "Внешний вид упаковки"),
    ]
    for ch in chars:
        db.execute_query("""
            INSERT INTO characteristics (name, unit, delta_x_default, weight, description)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING
        """, ch, fetch=False)
    
    # Получаем ID для связей
    sup_ids = {r['name']: r['id'] for r in db.execute_query("SELECT id, name FROM suppliers")}
    prod_ids = {r['name']: r['id'] for r in db.execute_query("SELECT id, name FROM products")}
    char_ids = {r['name']: r['id'] for r in db.execute_query("SELECT id, name FROM characteristics")}
    
    # Заполняем характеристики для продукции разных поставщиков
    # (нормы и реальные значения - часть брак, часть качественные)
    
    # Джинсы от Текстиль-Импорт
    if sup_ids.get("ООО 'Текстиль-Импорт'") and prod_ids.get("Джинсы мужские классические"):
        sid = sup_ids["ООО 'Текстиль-Импорт'"]
        pid = prod_ids["Джинсы мужские классические"]
        db.execute_query("""
            INSERT INTO product_characteristics 
                (product_id, supplier_id, characteristic_id, min_norm, max_norm, real_value)
            VALUES
                (%s, %s, %s, 95, 100, 98),   -- Состав ткани: 98% хлопок (норма)
                (%s, %s, %s, 250, 350, 280), -- Плотность: 280 г/м² (норма)
                (%s, %s, %s, 4, 5, 5),       -- Устойчивость окраски: 5 (норма)
                (%s, %s, %s, 0, 3, 2.5),     -- Усадка: 2.5% (норма)
                (%s, %s, %s, 20, 40, 35),    -- Прочность швов: 35 Н/см (норма)
                (%s, %s, %s, -5, 5, 3),      -- Соответствие размеру: +3 мм (норма)
                (%s, %s, %s, 4, 5, 5)        -- Упаковка: 5 баллов (норма)
            ON CONFLICT DO NOTHING
        """, (pid, sid, char_ids["Состав ткани"],
              pid, sid, char_ids["Плотность ткани"],
              pid, sid, char_ids["Устойчивость окраски"],
              pid, sid, char_ids["Усадка после стирки"],
              pid, sid, char_ids["Прочность швов"],
              pid, sid, char_ids["Соответствие размеру"],
              pid, sid, char_ids["Качество упаковки"]), fetch=False)
    
    # Рубашка от Мода-Стиль (качественная)
    if sup_ids.get("АО 'Мода-Стиль'") and prod_ids.get("Рубашка женская офисная"):
        sid = sup_ids["АО 'Мода-Стиль'"]
        pid = prod_ids["Рубашка женская офисная"]
        db.execute_query("""
            INSERT INTO product_characteristics 
                (product_id, supplier_id, characteristic_id, min_norm, max_norm, real_value)
            VALUES
                (%s, %s, %s, 95, 100, 100),  -- Состав: 100% хлопок
                (%s, %s, %s, 120, 150, 135), -- Плотность: 135
                (%s, %s, %s, 4, 5, 5),       -- Окраска: 5
                (%s, %s, %s, 0, 2, 1.2),     -- Усадка: 1.2%
                (%s, %s, %s, 15, 30, 25),    -- Прочность: 25
                (%s, %s, %s, -3, 3, 1),      -- Размер: +1 мм
                (%s, %s, %s, 4, 5, 5)        -- Упаковка: 5
            ON CONFLICT DO NOTHING
        """, (pid, sid, char_ids["Состав ткани"],
              pid, sid, char_ids["Плотность ткани"],
              pid, sid, char_ids["Устойчивость окраски"],
              pid, sid, char_ids["Усадка после стирки"],
              pid, sid, char_ids["Прочность швов"],
              pid, sid, char_ids["Соответствие размеру"],
              pid, sid, char_ids["Качество упаковки"]), fetch=False)
    
    # Куртка от Силуэт (БРАК - плохая устойчивость окраски)
    if sup_ids.get("ИП 'Силуэт'") and prod_ids.get("Куртка демисезонная"):
        sid = sup_ids["ИП 'Силуэт'"]
        pid = prod_ids["Куртка демисезонная"]
        db.execute_query("""
            INSERT INTO product_characteristics 
                (product_id, supplier_id, characteristic_id, min_norm, max_norm, real_value)
            VALUES
                (%s, %s, %s, 50, 100, 65),   -- Состав: 65% (норма)
                (%s, %s, %s, 150, 250, 180), -- Плотность: 180
                (%s, %s, %s, 4, 5, 2),       -- Окраска: 2 - БРАК (ниже нормы)
                (%s, %s, %s, 0, 4, 3),       -- Усадка: 3%
                (%s, %s, %s, 25, 50, 40),    -- Прочность: 40
                (%s, %s, %s, -10, 10, 8),    -- Размер: +8 мм
                (%s, %s, %s, 4, 5, 4)        -- Упаковка: 4
            ON CONFLICT DO NOTHING
        """, (pid, sid, char_ids["Состав ткани"],
              pid, sid, char_ids["Плотность ткани"],
              pid, sid, char_ids["Устойчивость окраски"],
              pid, sid, char_ids["Усадка после стирки"],
              pid, sid, char_ids["Прочность швов"],
              pid, sid, char_ids["Соответствие размеру"],
              pid, sid, char_ids["Качество упаковки"]), fetch=False)
    
    # Футболка от Элегант (БРАК - размер сильно занижен)
    if sup_ids.get("Швейная фабрика 'Элегант'") and prod_ids.get("Футболка хлопковая"):
        sid = sup_ids["Швейная фабрика 'Элегант'"]
        pid = prod_ids["Футболка хлопковая"]
        db.execute_query("""
            INSERT INTO product_characteristics 
                (product_id, supplier_id, characteristic_id, min_norm, max_norm, real_value)
            VALUES
                (%s, %s, %s, 90, 100, 95),   -- Состав: 95%
                (%s, %s, %s, 140, 180, 160), -- Плотность: 160
                (%s, %s, %s, 4, 5, 5),       -- Окраска: 5
                (%s, %s, %s, 0, 3, 2),       -- Усадка: 2%
                (%s, %s, %s, 15, 30, 22),    -- Прочность: 22
                (%s, %s, %s, -5, 5, -12),    -- Размер: -12 мм - БРАК (сильно маломерит)
                (%s, %s, %s, 4, 5, 4)        -- Упаковка: 4
            ON CONFLICT DO NOTHING
        """, (pid, sid, char_ids["Состав ткани"],
              pid, sid, char_ids["Плотность ткани"],
              pid, sid, char_ids["Устойчивость окраски"],
              pid, sid, char_ids["Усадка после стирки"],
              pid, sid, char_ids["Прочность швов"],
              pid, sid, char_ids["Соответствие размеру"],
              pid, sid, char_ids["Качество упаковки"]), fetch=False)
    
    print("✅ База данных склада одежды инициализирована (Вариант 19)")