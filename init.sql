-- =====================================================
-- ПОЛНАЯ ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
-- Склад готовой продукции - ОДЕЖДА (Вариант 19)
-- 6+ производителей, 5+ товаров для каждого
-- =====================================================

-- Очистка старых таблиц (если есть)
DROP TABLE IF EXISTS product_characteristics CASCADE;
DROP TABLE IF EXISTS characteristics CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;

-- ============ 1. ПОСТАВЩИКИ (6+) ============
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    address TEXT,
    phone VARCHAR(20),
    contact_person VARCHAR(100),
    inn VARCHAR(12),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO suppliers (name, address, phone, contact_person, inn, email) VALUES
-- Поставщик 1
('ООО "Текстиль-Импорт"', 
 'г. Москва, ул. Ткацкая, д. 15, офис 304', 
 '+7 (495) 123-45-67', 
 'Иванов Петр Сергеевич', 
 '7712345678', 
 'info@textil-import.ru'),

-- Поставщик 2
('АО "Мода-Стиль"', 
 'г. Санкт-Петербург, Невский пр., д. 45, лит. А', 
 '+7 (812) 234-56-78', 
 'Петрова Елена Владимировна', 
 '7812345678', 
 'sale@moda-style.ru'),

-- Поставщик 3
('ИП "Силуэт"', 
 'г. Новосибирск, ул. Советская, д. 12', 
 '+7 (383) 345-67-89', 
 'Сидоров Александр Николаевич', 
 '5412345678', 
 'sidorov@siluet.ru'),

-- Поставщик 4
('Швейная фабрика "Элегант"', 
 'г. Екатеринбург, ул. Машиностроителей, д. 8', 
 '+7 (343) 456-78-90', 
 'Козлова Ольга Ивановна', 
 '6612345678', 
 'factory@elegant.ru'),

-- Поставщик 5
('Торговый дом "Кашемир"', 
 'г. Казань, ул. Баумана, д. 23', 
 '+7 (843) 567-89-01', 
 'Смирнов Дмитрий Константинович', 
 '1612345678', 
 'info@cashmere.ru'),

-- Поставщик 6
('ООО "Джинс-Маркет"', 
 'г. Воронеж, ул. Ленина, д. 30', 
 '+7 (473) 678-90-12', 
 'Васильева Наталья Андреевна', 
 '3612345678', 
 'jeans@market.ru'),

-- Поставщик 7 (дополнительный)
('Фабрика "Классика"', 
 'г. Самара, ул. Промышленная, д. 5', 
 '+7 (846) 789-01-23', 
 'Федоров Игорь Петрович', 
 '6312345678', 
 'info@classica.ru'),

-- Поставщик 8 (дополнительный)
('ООО "Спорт-Текс"', 
 'г. Ростов-на-Дону, ул. Береговая, д. 17', 
 '+7 (863) 890-12-34', 
 'Соколова Анна Викторовна', 
 '6112345678', 
 'sport@tex.ru');

-- ============ 2. ПРОДУКЦИЯ (минимум 5 на каждого поставщика) ============
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(50),
    base_price DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO products (name, description, category, base_price) VALUES
-- Верхняя одежда
('Куртка демисезонная мужская', 'Ветрозащитная куртка на синтепоне, водоотталкивающая пропитка', 'Верхняя одежда', 4500.00),
('Пальто женское классическое', 'Шерсть 80%, кашемир 20%, подкладка вискоза', 'Верхняя одежда', 8900.00),
('Пуховик зимний', 'Наполнитель: гусиный пух 90%, плотная ветрозащитная ткань', 'Верхняя одежда', 12500.00),
('Плащ демисезонный', 'Непромокаемая ткань, съемный капюшон', 'Верхняя одежда', 5600.00),
('Жилет утепленный', 'Стеганый, наполнитель холлофайбер', 'Верхняя одежда', 2800.00),

-- Брюки и джинсы
('Джинсы мужские классические', 'Прямой крой, синий деним, плотность 400 г/м²', 'Брюки', 3200.00),
('Джинсы женские skinny', 'Узкие, с эффектом потертости, эластан 5%', 'Брюки', 3500.00),
('Брюки классические мужские', 'Шерсть 60%, полиэстер 40%, стрелки', 'Брюки', 3800.00),
('Брюки женские офисные', 'Зауженные, со стрелками, ткань костюмная', 'Брюки', 2900.00),
('Шорты джинсовые', 'Деним, средней посадки, с отворотами', 'Брюки', 1800.00),

-- Рубашки и блузы
('Рубашка мужская классическая', 'Хлопок 100%, отложной воротник, манжеты на пуговицах', 'Рубашки', 2200.00),
('Рубашка женская офисная', 'Белая, хлопок 80%, полиэстер 20%', 'Блузы', 2100.00),
('Блуза шелковая', 'Искусственный шелк, свободный крой', 'Блузы', 2700.00),
('Рубашка-поло', 'Хлопок 95%, эластан 5%, трикотаж', 'Рубашки', 1600.00),
('Туника женская', 'Лен 70%, вискоза 30%, свободный силуэт', 'Блузы', 2300.00),

-- Трикотаж
('Футболка хлопковая', 'Оверсайз, принт, хлопок 100%, плотность 180 г/м²', 'Трикотаж', 1200.00),
('Свитшот женский', 'Начес, хлопок 85%, полиэстер 15%', 'Трикотаж', 2400.00),
('Худи мужское', 'Капюшон, кенгуру, хлопок 80%, полиэстер 20%', 'Трикотаж', 2900.00),
('Лонгслив', 'Длинный рукав, хлопок 95%, эластан 5%', 'Трикотаж', 1400.00),
('Водолазка', 'Трикотаж, хлопок 70%, вискоза 30%', 'Трикотаж', 1600.00),

-- Платья и юбки
('Платье-футляр', 'Черное, эластан 5%, хлопок 95%', 'Платья', 3400.00),
('Платье вечернее', 'Длинное, кружево, подкладка атлас', 'Платья', 8900.00),
('Юбка-карандаш', 'Классическая, шерсть 60%, полиэстер 40%', 'Юбки', 2500.00),
('Юбка-плиссе', 'Длина миди, полиэстер 100%', 'Юбки', 2100.00),
('Сарафан летний', 'Лен 100%, на бретелях', 'Платья', 2800.00),

-- Спортивная одежда
('Костюм спортивный женский', 'Флис, трикотаж, куртка+брюки', 'Спорт', 4200.00),
('Лосины спортивные', 'Эластан 20%, хлопок 80%', 'Спорт', 1800.00),
('Толстовка спортивная', 'Футер с начесом, капюшон', 'Спорт', 2600.00),
('Шорты спортивные', 'Сетка, быстросохнущая ткань', 'Спорт', 1100.00),
('Ветровка спортивная', 'Непромокаемая, легкая', 'Спорт', 3200.00);

-- ============ 3. ХАРАКТЕРИСТИКИ КАЧЕСТВА (8 характеристик) ============
CREATE TABLE characteristics (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    unit VARCHAR(20),
    delta_x_default FLOAT DEFAULT 0.5,
    weight INTEGER DEFAULT 20,
    description TEXT
);

INSERT INTO characteristics (name, unit, delta_x_default, weight, description) VALUES
('Состав ткани', '%', 1.0, 25, 'Процентное содержание основного волокна (хлопок/шерсть)'),
('Плотность ткани', 'г/м²', 10.0, 20, 'Вес квадратного метра ткани'),
('Устойчивость окраски', 'баллы', 0.5, 20, 'По 5-балльной шкале (1-5)'),
('Усадка после стирки', '%', 0.5, 15, 'Процент уменьшения размера после стирки'),
('Прочность швов', 'Н/см', 5.0, 20, 'Ньютон на сантиметр - нагрузка до разрыва'),
('Соответствие размеру', 'мм', 2.0, 25, 'Отклонение от заявленного размера (+/-)'),
('Качество упаковки', 'баллы', 0.5, 15, 'Внешний вид и целостность упаковки (1-5)'),
-- Износостойкость теперь в баллах (1-10), чтобы масштаб был как у других характеристик
('Износостойкость', 'баллы', 0.5, 20, 'Оценка износостойкости материала по 10-балльной шкале');

-- ============ 4. СВЯЗИ ПРОДУКТ-ПОСТАВЩИК-ХАРАКТЕРИСТИКИ ============
CREATE TABLE product_characteristics (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE CASCADE,
    characteristic_id INTEGER REFERENCES characteristics(id) ON DELETE CASCADE,
    min_norm FLOAT NOT NULL,
    max_norm FLOAT NOT NULL,
    real_value FLOAT NOT NULL,
    measurement_date TIMESTAMP DEFAULT NOW(),
    UNIQUE(product_id, supplier_id, characteristic_id)
);

-- ============ 5. ЗАПОЛНЕНИЕ ХАРАКТЕРИСТИК ДЛЯ ВСЕХ ПРОДУКТОВ ============

-- Функция для получения ID
DO $$
DECLARE
    sup RECORD;
    prod RECORD;
    char RECORD;
    random_val FLOAT;
    is_defect BOOLEAN;
BEGIN
    -- Для каждого поставщика
    FOR sup IN SELECT id, name FROM suppliers LOOP
        
        -- Для каждого продукта (минимум 5 на поставщика)
        FOR prod IN SELECT id, name FROM products ORDER BY random() LIMIT 6 LOOP
            
            -- Для каждой характеристики
            FOR char IN SELECT id, name, delta_x_default FROM characteristics LOOP
                
                -- Определяем, будет ли этот продукт у этого поставщика бракованным (20% вероятность)
                is_defect := (random() < 0.2);
                
                -- Генерируем реальное значение в зависимости от нормы и брака
                CASE char.name
                    -- Состав ткани (норма 70-100%)
                    WHEN 'Состав ткани' THEN
                        IF is_defect THEN
                            random_val := 50 + random() * 20; -- 50-70% (брак)
                        ELSE
                            random_val := 85 + random() * 15; -- 85-100% (норма)
                        END IF;
                    
                    -- Плотность ткани (норма 150-400)
                    WHEN 'Плотность ткани' THEN
                        IF is_defect THEN
                            random_val := 100 + random() * 80; -- 100-180 (слишком легкая)
                        ELSE
                            random_val := 200 + random() * 150; -- 200-350 (норма)
                        END IF;
                    
                    -- Устойчивость окраски (норма 4-5)
                    WHEN 'Устойчивость окраски' THEN
                        IF is_defect THEN
                            random_val := 2 + random() * 2; -- 2-4 (брак)
                        ELSE
                            random_val := 4 + random(); -- 4-5 (норма)
                        END IF;
                    
                    -- Усадка (норма 0-5%)
                    WHEN 'Усадка после стирки' THEN
                        IF is_defect THEN
                            random_val := 6 + random() * 4; -- 6-10% (брак)
                        ELSE
                            random_val := 1 + random() * 3; -- 1-4% (норма)
                        END IF;
                    
                    -- Прочность швов (норма 20-50)
                    WHEN 'Прочность швов' THEN
                        IF is_defect THEN
                            random_val := 10 + random() * 10; -- 10-20 (брак)
                        ELSE
                            random_val := 25 + random() * 20; -- 25-45 (норма)
                        END IF;
                    
                    -- Соответствие размеру (норма -10..+10 мм)
                    WHEN 'Соответствие размеру' THEN
                        IF is_defect THEN
                            IF random() < 0.5 THEN
                                random_val := -25 + random() * 10; -- -25..-15 (сильно маломерит)
                            ELSE
                                random_val := 15 + random() * 10; -- 15..25 (сильно большемерит)
                            END IF;
                        ELSE
                            random_val := -8 + random() * 16; -- -8..+8 (норма)
                        END IF;
                    
                    -- Качество упаковки (норма 4-5)
                    WHEN 'Качество упаковки' THEN
                        IF is_defect THEN
                            random_val := 1 + random() * 3; -- 1-3 (брак)
                        ELSE
                            random_val := 4 + random(); -- 4-5 (норма)
                        END IF;
                    
                    -- Износостойкость теперь по 10-балльной шкале (норма 7-10)
                    WHEN 'Износостойкость' THEN
                        IF is_defect THEN
                            random_val := 3 + random() * 4; -- 3-7 (брак - низкая износостойкость)
                        ELSE
                            random_val := 7 + random() * 3; -- 7-10 (норма - высокая износостойкость)
                        END IF;
                    
                    ELSE
                        random_val := 5;
                END CASE;
                
                -- Округляем до 2 знаков (исправлено для FLOAT)
                random_val := ROUND(random_val::numeric, 2)::float;
                
                -- Вставляем запись
                BEGIN
                    INSERT INTO product_characteristics 
                        (product_id, supplier_id, characteristic_id, min_norm, max_norm, real_value)
                    VALUES (
                        prod.id, sup.id, char.id,
                        CASE char.name
                            WHEN 'Состав ткани' THEN 70
                            WHEN 'Плотность ткани' THEN 150
                            WHEN 'Устойчивость окраски' THEN 4
                            WHEN 'Усадка после стирки' THEN 0
                            WHEN 'Прочность швов' THEN 20
                            WHEN 'Соответствие размеру' THEN -10
                            WHEN 'Качество упаковки' THEN 4
                            WHEN 'Износостойкость' THEN 7
                            ELSE 0
                        END,
                        CASE char.name
                            WHEN 'Состав ткани' THEN 100
                            WHEN 'Плотность ткани' THEN 400
                            WHEN 'Устойчивость окраски' THEN 5
                            WHEN 'Усадка после стирки' THEN 5
                            WHEN 'Прочность швов' THEN 50
                            WHEN 'Соответствие размеру' THEN 10
                            WHEN 'Качество упаковки' THEN 5
                            WHEN 'Износостойкость' THEN 10
                            ELSE 10
                        END,
                        random_val
                    )
                    ON CONFLICT DO NOTHING;
                EXCEPTION WHEN OTHERS THEN
                    -- Игнорируем ошибки уникальности
                END;
                
            END LOOP;
        END LOOP;
    END LOOP;
END $$;

-- Проверка результатов
SELECT 'Поставщики: ' || COUNT(*) FROM suppliers;
SELECT 'Продукты: ' || COUNT(*) FROM products;
SELECT 'Характеристики: ' || COUNT(*) FROM characteristics;
SELECT 'Связей: ' || COUNT(*) FROM product_characteristics;

-- Статистика по браку
SELECT 
    COUNT(*) as всего_характеристик,
    SUM(CASE WHEN real_value < min_norm OR real_value > max_norm THEN 1 ELSE 0 END) as отклонений,
    ROUND(100.0 * SUM(CASE WHEN real_value < min_norm OR real_value > max_norm THEN 1 ELSE 0 END) / COUNT(*), 2) as процент_брака
FROM product_characteristics;

-- Дополнительная статистика по каждой характеристике (исправлено с приведением типов)
SELECT 
    c.name as характеристика,
    COUNT(*) as всего_измерений,
    ROUND(AVG(pc.real_value)::numeric, 2) as среднее_значение,
    MIN(pc.real_value) as минимум,
    MAX(pc.real_value) as максимум,
    SUM(CASE WHEN pc.real_value < pc.min_norm OR pc.real_value > pc.max_norm THEN 1 ELSE 0 END) as отклонений,
    ROUND(100.0 * SUM(CASE WHEN pc.real_value < pc.min_norm OR pc.real_value > pc.max_norm THEN 1 ELSE 0 END) / COUNT(*), 2) as процент_брака
FROM product_characteristics pc
JOIN characteristics c ON pc.characteristic_id = c.id
GROUP BY c.name, c.id
ORDER BY c.id;