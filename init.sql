-- Очистка старых таблиц
DROP TABLE IF EXISTS product_characteristics CASCADE;
DROP TABLE IF EXISTS characteristics CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;

-- Создание заново (модели поднимутся через Python)
-- Здесь оставляем заглушку, основная инициализация в models.py
SELECT 1;