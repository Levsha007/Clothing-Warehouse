-- Полная инициализация базы данных склада одежды (Вариант 19)
-- 6+ поставщиков, у каждого 5+ товаров с характеристиками

-- Очистка существующих таблиц
DROP TABLE IF EXISTS product_characteristics CASCADE;
DROP TABLE IF EXISTS characteristics CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;

-- ============ 1. ПОСТАВЩИКИ (7 штук) ============
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    address TEXT NOT NULL,
    phone VARCHAR(20) NOT NULL,
    contact_person VARCHAR(100) NOT NULL,
    inn VARCHAR(12) NOT NULL,
    rating INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO suppliers (name, address, phone, contact_person, inn, rating) VALUES
    ('ООО "Текстиль-Импорт"', 'г. Москва, ул. Ткацкая, 15', '+7 (495) 123-45-67', 'Иванов Петр Сергеевич', '7712345678', 5),
    ('АО "Мода-Стиль"', 'г. Санкт-Петербург, пр. Невский, 45', '+7 (812) 234-56-78', 'Петрова Елена Владимировна', '7812345678', 4),
    ('ИП "Силуэт"', 'г. Новосибирск, ул. Советская, 12', '+7 (383) 345-67-89', 'Сидоров Александр Николаевич', '5412345678', 3),
    ('Швейная фабрика "Элегант"', 'г. Екатеринбург, ул. Машиностроителей, 8', '+7 (343) 456-78-90', 'Козлова Ольга Ивановна', '6612345678', 5),
    ('Торговый дом "Кашемир"', 'г. Казань, ул. Баумана, 23', '+7 (843) 567-89-01', 'Смирнов Дмитрий Константинович', '1612345678', 4),
    ('ООО "Джинс-Маркет"', 'г. Воронеж, ул. Ленина, 30', '+7 (473) 678-90-12', 'Васильева Наталья Алексеевна', '3612345678', 4),
    ('Фабрика "Классика"', 'г. Самара, ул. Промышленная, 5', '+7 (846) 789-01-23', 'Федоров Игорь Павлович', '6312345678', 5);

-- ============ 2. ХАРАКТЕРИСТИКИ КАЧЕСТВА ============
CREATE TABLE characteristics (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    unit VARCHAR(20),
    delta_x_default FLOAT DEFAULT 0.5,
    weight INTEGER DEFAULT 20,
    description TEXT,
    is_critical BOOLEAN DEFAULT FALSE
);

INSERT INTO characteristics (name, unit, delta_x_default, weight, description, is_critical) VALUES
    ('Состав ткани', '%', 1.0, 25, 'Процентное содержание основного волокна', TRUE),
    ('Плотность ткани', 'г/м²', 5.0, 20, 'Вес квадратного метра', FALSE),
    ('Устойчивость окраски', 'баллы', 0.5, 20, 'По 5-балльной шкале', TRUE),
    ('Усадка после стирки', '%', 0.5, 15, 'Процент усадки', TRUE),
    ('Прочность швов', 'Н/см', 2.0, 20, 'Ньютон на сантиметр', FALSE),
    ('Соответствие размеру', 'мм', 1.0, 25, 'Отклонение от заявленного', TRUE),
    ('Воздухопроницаемость', 'дм³/м²с', 5.0, 15, 'Пропускание воздуха', FALSE),
    ('Гигроскопичность', '%', 1.0, 15, 'Влагопоглощение', FALSE),
    ('Электризуемость', 'кВ/м', 0.2, 10, 'Статическое электричество', FALSE),
    ('Качество упаковки', 'баллы', 0.5, 15, 'Внешний вид упаковки', FALSE);

-- ============ 3. ПРОДУКЦИЯ (35+ товаров) ============
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(50),
    base_price DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO products (name, description, category, base_price) VALUES
    -- Джинсы (5 моделей)
    ('Джинсы мужские классические', 'Прямые джинсы, синий деним, 100% хлопок', 'Брюки', 2999.00),
    ('Джинсы женские скинни', 'Узкие джинсы, черный цвет, эластан', 'Брюки', 3299.00),
    ('Джинсы мужские свободные', 'Широкие джинсы, голубой деним', 'Брюки', 2799.00),
    ('Джинсы женские клеш', 'Клеш от колена, белый деним', 'Брюки', 3499.00),
    ('Джинсы подростковые', 'Молодежный стиль, потертости', 'Брюки', 2599.00),
    
    -- Рубашки (5 моделей)
    ('Рубашка женская офисная', 'Белая, хлопок 100%, классический крой', 'Блузы', 1899.00),
    ('Рубашка мужская классическая', 'Голубая, хлопок, длинный рукав', 'Сорочки', 1999.00),
    ('Блуза шелковая', 'Искусственный шелк, приталенная', 'Блузы', 2499.00),
    ('Рубашка ковбойка', 'Клетка, хлопок, короткий рукав', 'Сорочки', 1799.00),
    ('Рубашка оверсайз', 'Свободный крой, льняная', 'Блузы', 2199.00),
    
    -- Верхняя одежда (5 моделей)
    ('Куртка демисезонная', 'Плащевка, утеплитель, капюшон', 'Верхняя одежда', 4599.00),
    ('Пальто шерстяное', '70% шерсть, двубортное', 'Верхняя одежда', 6899.00),
    ('Пуховик зимний', 'Натуральный пух, длина миди', 'Верхняя одежда', 7999.00),
    ('Тренч женский', 'Непромокаемая ткань, пояс', 'Верхняя одежда', 5299.00),
    ('Бомбер', 'Спортивный стиль, флис', 'Верхняя одежда', 3899.00),
    
    -- Трикотаж (5 моделей)
    ('Футболка хлопковая', 'Оверсайз, принт', 'Трикотаж', 899.00),
    ('Водолазка', 'Трикотаж, облегающая', 'Трикотаж', 1299.00),
    ('Свитер крупной вязки', 'Шерсть, высокий ворот', 'Трикотаж', 2799.00),
    ('Худи на молнии', 'Флис, капюшон', 'Трикотаж', 2399.00),
    ('Лонгслив', 'Хлопок, длинный рукав', 'Трикотаж', 1199.00),
    
    -- Платья (5 моделей)
    ('Платье-футляр', 'Черное, эластан, миди', 'Платья', 3299.00),
    ('Платье летнее', 'Вискоза, цветочный принт', 'Платья', 2199.00),
    ('Платье вечернее', 'Кружево, декольте', 'Платья', 5499.00),
    ('Сарафан', 'Лен, бретели', 'Платья', 1999.00),
    ('Платье-свитер', 'Трикотаж, свободное', 'Платья', 2799.00),
    
    -- Костюмы (5 моделей)
    ('Костюм спортивный', 'Флис, трикотаж, двойка', 'Спорт', 3499.00),
    ('Костюм офисный', 'Классика, пиджак+брюки', 'Костюмы', 6899.00),
    ('Пижама', 'Хлопок, набор', 'Дом', 2199.00),
    ('Костюм для йоги', 'Эластан, дышащий', 'Спорт', 2899.00),
    ('Тройка мужская', 'Шерсть, пиджак+жилет+брюки', 'Костюмы', 8999.00),
    
    -- Аксессуары (5 моделей)
    ('Шарф кашемировый', '120x30 см, бордовый', 'Аксессуары', 1599.00),
    ('Шапка вязаная', 'Шерсть, объемная', 'Аксессуары', 899.00),
    ('Перчатки кожаные', 'Натуральная кожа, утеплитель', 'Аксессуары', 1499.00),
    ('Ремень кожаный', 'Ширина 3 см, классика', 'Аксессуары', 1299.00),
    ('Галстук шелковый', 'Синий, принт', 'Аксессуары', 999.00);

-- ============ 4. ХАРАКТЕРИСТИКИ ДЛЯ КАЖДОГО ТОВАРА У КАЖДОГО ПОСТАВЩИКА ============
CREATE TABLE product_characteristics (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE CASCADE,
    characteristic_id INTEGER REFERENCES characteristics(id) ON DELETE CASCADE,
    min_norm FLOAT NOT NULL,
    max_norm FLOAT NOT NULL,
    real_value FLOAT NOT NULL,
    measurement_date TIMESTAMP DEFAULT NOW(),
    batch_number VARCHAR(50),
    UNIQUE(product_id, supplier_id, characteristic_id)
);

-- Функция для генерации реалистичных значений с отклонениями
CREATE OR REPLACE FUNCTION generate_real_value(
    min_norm FLOAT, 
    max_norm FLOAT, 
    defect_prob FLOAT DEFAULT 0.3
) RETURNS FLOAT AS $$
DECLARE
    r FLOAT;
    result FLOAT;
BEGIN
    r := random();
    
    -- 30% шанс брака (по умолчанию)
    IF r < defect_prob THEN
        -- Брак: отклонение от нормы
        IF random() < 0.5 THEN
            -- Ниже нормы (на 5-30%)
            result := min_norm * (0.7 + random() * 0.25);
        ELSE
            -- Выше нормы (на 5-30%)
            result := max_norm * (1.0 + random() * 0.3);
        END IF;
    ELSE
        -- В норме (случайное значение в пределах нормы)
        result := min_norm + random() * (max_norm - min_norm);
    END IF;
    
    RETURN ROUND(result::NUMERIC, 1)::FLOAT;
END;
$$ LANGUAGE plpgsql;

-- Заполняем характеристики для всех товаров у всех поставщиков
DO $$
DECLARE
    s RECORD;
    p RECORD;
    c RECORD;
    min_val FLOAT;
    max_val FLOAT;
    real_val FLOAT;
    defect_rate FLOAT;
BEGIN
    FOR s IN SELECT id, name FROM suppliers LOOP
        -- У каждого поставщика своя склонность к браку
        defect_rate := CASE 
            WHEN s.name LIKE '%Текстиль-Импорт%' OR s.name LIKE '%Элегант%' OR s.name LIKE '%Классика%' THEN 0.15  -- качественные
            WHEN s.name LIKE '%Мода-Стиль%' OR s.name LIKE '%Кашемир%' OR s.name LIKE '%Джинс-Маркет%' THEN 0.25  -- средние
            ELSE 0.4  -- проблемные
        END;
        
        FOR p IN SELECT id, name, category FROM products WHERE category IN ('Брюки', 'Сорочки', 'Верхняя одежда', 'Трикотаж', 'Платья', 'Спорт', 'Костюмы') LOOP
            -- Характеристика 1: Состав ткани
            c := (SELECT * FROM characteristics WHERE name = 'Состав ткани');
            IF p.category IN ('Брюки', 'Сорочки', 'Платья') THEN
                min_val := 95; max_val := 100;
            ELSIF p.category = 'Верхняя одежда' THEN
                min_val := 50; max_val := 100;
            ELSE
                min_val := 80; max_val := 100;
            END IF;
            real_val := generate_real_value(min_val, max_val, defect_rate);
            INSERT INTO product_characteristics (product_id, supplier_id, characteristic_id, min_norm, max_norm, real_value, batch_number)
            VALUES (p.id, s.id, c.id, min_val, max_val, real_val, 'BATCH-' || to_char(NOW(), 'YYYYMMDD') || '-' || s.id || '-' || p.id)
            ON CONFLICT DO NOTHING;
            
            -- Характеристика 2: Плотность ткани
            c := (SELECT * FROM characteristics WHERE name = 'Плотность ткани');
            IF p.category = 'Верхняя одежда' THEN
                min_val := 150; max_val := 300;
            ELSIF p.category = 'Брюки' THEN
                min_val := 200; max_val := 350;
            ELSE
                min_val := 120; max_val := 200;
            END IF;
            real_val := generate_real_value(min_val, max_val, defect_rate);
            INSERT INTO product_characteristics (product_id, supplier_id, characteristic_id, min_norm, max_norm, real_value, batch_number)
            VALUES (p.id, s.id, c.id, min_val, max_val, real_val, 'BATCH-' || to_char(NOW(), 'YYYYMMDD') || '-' || s.id || '-' || p.id)
            ON CONFLICT DO NOTHING;
            
            -- Характеристика 3: Устойчивость окраски (критическая)
            c := (SELECT * FROM characteristics WHERE name = 'Устойчивость окраски');
            min_val := 4; max_val := 5;
            real_val := generate_real_value(min_val, max_val, defect_rate * 1.5);  -- выше шанс брака
            INSERT INTO product_characteristics (product_id, supplier_id, characteristic_id, min_norm, max_norm, real_value, batch_number)
            VALUES (p.id, s.id, c.id, min_val, max_val, real_val, 'BATCH-' || to_char(NOW(), 'YYYYMMDD') || '-' || s.id || '-' || p.id)
            ON CONFLICT DO NOTHING;
            
            -- Характеристика 4: Усадка после стирки (критическая)
            c := (SELECT * FROM characteristics WHERE name = 'Усадка после стирки');
            IF p.category = 'Верхняя одежда' THEN
                min_val := 0; max_val := 5;
            ELSE
                min_val := 0; max_val := 3;
            END IF;
            real_val := generate_real_value(min_val, max_val, defect_rate);
            INSERT INTO product_characteristics (product_id, supplier_id, characteristic_id, min_norm, max_norm, real_value, batch_number)
            VALUES (p.id, s.id, c.id, min_val, max_val, real_val, 'BATCH-' || to_char(NOW(), 'YYYYMMDD') || '-' || s.id || '-' || p.id)
            ON CONFLICT DO NOTHING;
            
            -- Характеристика 5: Прочность швов
            c := (SELECT * FROM characteristics WHERE name = 'Прочность швов');
            IF p.category = 'Верхняя одежда' THEN
                min_val := 25; max_val := 50;
            ELSIF p.category = 'Брюки' THEN
                min_val := 20; max_val := 40;
            ELSE
                min_val := 15; max_val := 30;
            END IF;
            real_val := generate_real_value(min_val, max_val, defect_rate);
            INSERT INTO product_characteristics (product_id, supplier_id, characteristic_id, min_norm, max_norm, real_value, batch_number)
            VALUES (p.id, s.id, c.id, min_val, max_val, real_val, 'BATCH-' || to_char(NOW(), 'YYYYMMDD') || '-' || s.id || '-' || p.id)
            ON CONFLICT DO NOTHING;
            
            -- Характеристика 6: Соответствие размеру (критическая)
            c := (SELECT * FROM characteristics WHERE name = 'Соответствие размеру');
            min_val := -10; max_val := 10;
            real_val := generate_real_value(min_val, max_val, defect_rate * 1.2);
            INSERT INTO product_characteristics (product_id, supplier_id, characteristic_id, min_norm, max_norm, real_value, batch_number)
            VALUES (p.id, s.id, c.id, min_val, max_val, real_val, 'BATCH-' || to_char(NOW(), 'YYYYMMDD') || '-' || s.id || '-' || p.id)
            ON CONFLICT DO NOTHING;
            
            -- Характеристика 7: Воздухопроницаемость
            c := (SELECT * FROM characteristics WHERE name = 'Воздухопроницаемость');
            IF p.category = 'Сорочки' OR p.category = 'Блузы' OR p.category = 'Трикотаж' THEN
                min_val := 100; max_val := 300;
            ELSE
                min_val := 30; max_val := 100;
            END IF;
            real_val := generate_real_value(min_val, max_val, defect_rate * 0.8);
            INSERT INTO product_characteristics (product_id, supplier_id, characteristic_id, min_norm, max_norm, real_value, batch_number)
            VALUES (p.id, s.id, c.id, min_val, max_val, real_val, 'BATCH-' || to_char(NOW(), 'YYYYMMDD') || '-' || s.id || '-' || p.id)
            ON CONFLICT DO NOTHING;
        END LOOP;
    END LOOP;
END $$;

-- Создаем индексы для быстрого поиска
CREATE INDEX idx_product_characteristics_product ON product_characteristics(product_id);
CREATE INDEX idx_product_characteristics_supplier ON product_characteristics(supplier_id);
CREATE INDEX idx_product_characteristics_quality ON product_characteristics(characteristic_id, real_value);

-- Создаем представление для анализа качества
CREATE VIEW quality_analysis AS
SELECT 
    s.name AS supplier_name,
    s.rating AS supplier_rating,
    p.name AS product_name,
    p.category,
    COUNT(DISTINCT pc.id) AS total_characteristics,
    COUNT(DISTINCT CASE WHEN pc.real_value < pc.min_norm OR pc.real_value > pc.max_norm THEN pc.id END) AS defect_count,
    ROUND(
        (COUNT(DISTINCT CASE WHEN pc.real_value < pc.min_norm OR pc.real_value > pc.max_norm THEN pc.id END)::FLOAT / 
         COUNT(DISTINCT pc.id)::FLOAT * 100)::NUMERIC, 1
    ) AS defect_percent,
    ROUND(AVG(pc.real_value)::NUMERIC, 1) AS avg_real_value,
    ROUND(AVG(pc.min_norm)::NUMERIC, 1) AS avg_min_norm,
    ROUND(AVG(pc.max_norm)::NUMERIC, 1) AS avg_max_norm
FROM product_characteristics pc
JOIN suppliers s ON pc.supplier_id = s.id
JOIN products p ON pc.product_id = p.id
GROUP BY s.id, s.name, s.rating, p.id, p.name, p.category
ORDER BY s.name, defect_percent DESC;

-- Создаем представление для СППР
CREATE VIEW spzr_data AS
SELECT 
    pc.id,
    s.id AS supplier_id,
    s.name AS supplier_name,
    p.id AS product_id,
    p.name AS product_name,
    c.id AS characteristic_id,
    c.name AS characteristic_name,
    c.unit,
    c.weight,
    c.delta_x_default,
    pc.min_norm,
    pc.max_norm,
    pc.real_value,
    pc.batch_number,
    CASE 
        WHEN pc.real_value BETWEEN pc.min_norm AND pc.max_norm THEN 'Норма'
        WHEN pc.real_value < pc.min_norm THEN 'Ниже нормы'
        ELSE 'Выше нормы'
    END AS status
FROM product_characteristics pc
JOIN suppliers s ON pc.supplier_id = s.id
JOIN products p ON pc.product_id = p.id
JOIN characteristics c ON pc.characteristic_id = c.id;

-- Проверка результатов
SELECT COUNT(*) AS total_suppliers FROM suppliers;
SELECT COUNT(*) AS total_products FROM products;
SELECT COUNT(*) AS total_characteristics_defs FROM characteristics;
SELECT COUNT(*) AS total_product_characteristics FROM product_characteristics;

-- Статистика по качеству
SELECT 
    s.name AS supplier,
    COUNT(DISTINCT pc.product_id) AS products,
    COUNT(pc.id) AS total_checks,
    COUNT(CASE WHEN pc.real_value < pc.min_norm OR pc.real_value > pc.max_norm THEN 1 END) AS defects,
    ROUND(
        COUNT(CASE WHEN pc.real_value < pc.min_norm OR pc.real_value > pc.max_norm THEN 1 END)::NUMERIC / 
        COUNT(pc.id)::NUMERIC * 100, 1
    ) AS defect_rate_percent
FROM product_characteristics pc
JOIN suppliers s ON pc.supplier_id = s.id
GROUP BY s.id, s.name
ORDER BY defect_rate_percent;