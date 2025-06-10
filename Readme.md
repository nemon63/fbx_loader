# 🚀 Загрузчик моделей FBX для Houdini - Руководство по установке

## 📋 Оглавление

1. [Установка](#установка)
2. [Структура файлов](#структура-файлов)
3. [Настройка полки](#настройка-полки)
4. [Использование](#использование)
5. [Решение проблем](#решение-проблем)
6. [Тестирование](#тестирование)
7. [Поддерживаемые форматы](#поддерживаемые-форматы)

## 📦 Установка

### Шаг 1: Определение директории установки

Найдите вашу пользовательскую директорию Houdini:
- **Windows**: `C:\Users\{username}\Documents\houdini{version}`
- **macOS**: `~/Library/Preferences/houdini/{version}`
- **Linux**: `~/houdini{version}`

### Шаг 2: Создание структуры директорий

Создайте следующую структуру папок:
```
{HOUDINI_USER_DIR}/
├── scripts/
│   └── python/
│       └── fbx_loader/
└── toolbar/
```

### Шаг 3: Размещение файлов

Поместите все исправленные Python файлы в папку `scripts/python/fbx_loader/`:

```
fbx_loader/
├── __init__.py
├── constants.py
├── utils.py
├── material_utils.py
├── model_processor.py
├── main.py
├── settings_dialog.py
├── logger.py
├── cache_manager.py
└── shelf_tool.py
```

## 📁 Структура файлов

### Основные модули

| Файл | Описание |
|------|----------|
| `constants.py` | Константы, настройки по умолчанию, валидация |
| `utils.py` | Вспомогательные функции (очистка имен, создание нод) |
| `material_utils.py` | Работа с материалами и текстурами |
| `model_processor.py` | Обработка моделей (отдельные/объединенные) |
| `main.py` | Основная логика импорта |
| `settings_dialog.py` | Диалог настроек PyQt |
| `logger.py` | Система логирования и отчетов |
| `cache_manager.py` | Кэширование для ускорения работы |
| `shelf_tool.py` | Скрипт запуска с полки |

### Ключевые улучшения

✅ **Исправлены все критические баги**:
- Проблемы с параметром `settings`
- Некорректная структура импортов
- Циклические зависимости
- Отсутствие проверки на существование файлов
- Проблемы с именованием нод

✅ **Добавлена робастность**:
- Обработка ошибок во всех функциях
- Fallback механизмы при сбоях
- Валидация входных данных
- Thread-safety для кэша

✅ **Улучшена производительность**:
- Оптимизированный поиск текстур
- LRU кэширование имен нод
- Умное кэширование материалов
- Предотвращение дублирования операций

## 🛠️ Настройка полки

### Автоматическое создание кнопки полки

1. Откройте Houdini
2. В Python Shell выполните:

```python
import hou
import os

# Путь к скрипту
scripts_dir = os.path.join(hou.homeHoudiniDirectory(), "scripts", "python", "fbx_loader")
shelf_script_path = os.path.join(scripts_dir, "shelf_tool.py")

# Создание полки, если её нет
shelf_set = hou.shelves.shelfSets().get("fbx_tools")
if not shelf_set:
    shelf_set = hou.shelves.newShelfSet("fbx_tools", "FBX Tools")

shelf = shelf_set.shelves().get("fbx_loader")
if not shelf:
    shelf = hou.shelves.newShelf("fbx_loader", "FBX Loader", shelf_set)

# Создание инструмента
tool = hou.shelves.newTool(
    file_path=None,
    name="fbx_model_importer",
    label="Import Models",
    script=f'exec(open(r"{shelf_script_path}").read())',
    language=hou.scriptLanguage.Python,
    icon="$HH/config/Icons/SOP/file.svg",
    help="Импорт моделей FBX/OBJ/ABC с автоматическим назначением материалов"
)

shelf.setTools([tool])
print("Кнопка создана успешно!")
```

### Ручное создание

1. Правой кнопкой по полке → **New Tool**
2. Заполните поля:
   - **Name**: `fbx_model_importer`
   - **Label**: `Import Models`
   - **Script Language**: `Python`
   - **Script**:
   ```python
   import sys
   import os
   
   scripts_dir = os.path.join(hou.homeHoudiniDirectory(), "scripts", "python", "fbx_loader")
   if scripts_dir not in sys.path:
       sys.path.append(scripts_dir)
   
   exec(open(os.path.join(scripts_dir, "shelf_tool.py")).read())
   ```

## 🎯 Использование

### Быстрый старт

1. **Нажмите кнопку** на полке "Import Models"
2. **Выберите режим импорта**:
   - **Отдельные геометрии** - каждая модель в своей geo-ноде
   - **Группировка по папкам** - модели группируются по директориям
   - **Все в один узел** - все модели в одной geo-ноде
3. **Настройте тип материала**:
   - **Principled Shader** (рекомендуется)
   - **Redshift Material**
   - **Standard Material**
4. **Выберите папку** с моделями и текстурами
5. **Дождитесь завершения** импорта

### Структура папок для оптимальной работы

```
project_folder/
├── models/
│   ├── character.fbx
│   ├── props/
│   │   ├── chair.fbx
│   │   └── table.fbx
│   └── environment/
│       └── building.fbx
├── textures/
│   ├── character_diffuse.png
│   ├── character_normal.png
│   ├── chair_basecolor.jpg
│   ├── chair_roughness.jpg
│   └── building_albedo.tga
└── materials/          # необязательно
    └── custom_mats.json
```

### Поддерживаемые соглашения по именованию текстур

| Тип текстуры | Ключевые слова |
|--------------|----------------|
| **Диффузная/Альбедо** | `diff`, `diffuse`, `albedo`, `basecolor`, `col`, `_d`, `-d` |
| **Нормали** | `normal`, `norm`, `nml`, `_n`, `-n` |
| **Шероховатость** | `rough`, `roughness`, `gloss`, `_r`, `-r` |
| **Металличность** | `metal`, `metallic`, `_m`, `-m` |
| **AO** | `ao`, `ambient`, `occlusion`, `_ao`, `-ao` |
| **Эмиссия** | `emissive`, `emission`, `emit`, `_e`, `-e` |

### Расширенные настройки

#### Вкладка "Основные"
- **Режим импорта**: Выбор стратегии организации моделей
- **Тип материала**: Выбор движка рендеринга
- **Масштаб**: Коэффициент масштабирования (0.01-100.0)
- **Кэширование**: Ускоряет повторные импорты

#### Вкладка "Текстуры"
- **Разрешение**: Целевое разрешение для оптимизации
- **Автоназначение**: Автоматический поиск текстур
- **Создание UV**: Генерация UV-развертки

#### Вкладка "Геометрия"
- **Пространства имен**: Очистка namespace
- **LOD уровни**: Автосоздание уровней детализации
- **Триангуляция**: Преобразование в треугольники
- **Сварка вершин**: Объединение близких вершин

#### Вкладка "Отчеты"
- **Генерация отчета**: HTML отчет с результатами
- **Лог импорта**: Подробный лог процесса
- **Режим отладки**: Расширенное логирование

## 🔧 Решение проблем

### Распространенные ошибки

#### 1. "Не удалось импортировать модули"
**Причина**: Неправильная структура папок или пути
**Решение**:
```python
import sys
import os
print("Python paths:")
for path in sys.path:
    print(f"  {path}")

# Проверьте путь к скриптам
scripts_path = os.path.join(hou.homeHoudiniDirectory(), "scripts", "python", "fbx_loader")
print(f"Scripts path: {scripts_path}")
print(f"Exists: {os.path.exists(scripts_path)}")
```

#### 2. "Ошибка создания материала"
**Причина**: Неподдерживаемый тип материала в текущей версии Houdini
**Решение**: Измените тип материала в настройках на "Standard Material"

#### 3. "Модели импортируются без материалов"
**Причина**: Неправильное именование текстур
**Решение**: 
- Убедитесь в правильном именовании текстур
- Включите режим отладки для анализа процесса

#### 4. "Не удалось создать подсеть"
**Причина**: Проблемы с именами узлов (спецсимволы, кириллица)
**Решение**: Переименуйте папки и файлы, используя только латинские буквы и цифры

### Диагностика

#### Проверка состояния системы
```python
# В Python Shell Houdini
import sys
sys.path.append(r"путь\к\fbx_loader")

from cache_manager import CacheManager
from logger import ImportLogger

# Тест кэша
cache = CacheManager(enabled=True)
print("Cache info:", cache.get_cache_size_info())

# Тест логгера
logger = ImportLogger(debug_mode=True)
logger.log_info("Тест логирования")
print("Log file:", logger.get_log_file_path())
```

#### Очистка кэша
```python
cache = CacheManager()
cache.clear_cache()
print("Кэш очищен")
```

## 🧪 Тестирование

### Набор тестовых данных

Создайте следующую структуру для тестирования:

```
test_data/
├── simple_test/
│   ├── cube.fbx
│   ├── cube_diffuse.png
│   └── cube_normal.png
├── complex_test/
│   ├── models/
│   │   ├── character.fbx
│   │   └── props/
│   │       ├── chair.fbx
│   │       └── table.obj
│   ├── textures/
│   │   ├── character_BaseColor.jpg
│   │   ├── character_Normal.jpg
│   │   ├── character_Roughness.jpg
│   │   ├── chair_diffuse.tga
│   │   └── table_albedo.png
│   └── materials/
└── edge_cases/
    ├── файл с пробелами.fbx
    ├── модель_кириллица.fbx
    ├── no_textures.obj
    └── empty_file.fbx
```

### Тестовые сценарии

#### 1. Базовое тестирование
- [ ] Импорт одной модели с одной текстурой
- [ ] Импорт нескольких моделей без текстур
- [ ] Импорт с различными типами материалов

#### 2. Тестирование текстур
- [ ] Автоматическое определение типов текстур
- [ ] UDIM последовательности
- [ ] Различные форматы изображений

#### 3. Стресс-тестирование
- [ ] Импорт 100+ моделей
- [ ] Модели с большим количеством материалов
- [ ] Очень длинные пути к файлам

#### 4. Граничные случаи
- [ ] Файлы с неподдерживаемыми символами в именах
- [ ] Поврежденные файлы моделей
- [ ] Недоступные файлы текстур
- [ ] Пустые папки

### Автоматическое тестирование

```python
# Скрипт для автоматического тестирования
def run_import_tests():
    import tempfile
    import shutil
    
    # Создаем тестовую структуру
    test_dir = os.path.join(tempfile.gettempdir(), "houdini_import_test")
    
    # Запускаем тесты
    test_results = []
    
    # Тест 1: Простой импорт
    try:
        from main import create_multi_material_models
        result = create_multi_material_models(merge_models=False)
        test_results.append(("simple_import", result is not None))
    except Exception as e:
        test_results.append(("simple_import", False, str(e)))
    
    # Тест 2: Объединенный импорт
    try:
        result = create_multi_material_models(merge_models=True)
        test_results.append(("merged_import", result is not None))
    except Exception as e:
        test_results.append(("merged_import", False, str(e)))
    
    # Выводим результаты
    for test in test_results:
        status = "✅ PASS" if test[1] else "❌ FAIL"
        error = f" - {test[2]}" if len(test) > 2 else ""
        print(f"{status} {test[0]}{error}")
    
    # Очистка
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

# Запуск тестов
run_import_tests()
```

## 📋 Поддерживаемые форматы

### Модели
- ✅ **FBX** (.fbx) - основной формат
- ✅ **OBJ** (.obj) - геометрия + материалы
- ✅ **Alembic** (.abc) - анимация и кэши
- ✅ **BGEO** (.bgeo, .bgeo.sc) - нативный Houdini
- ✅ **PLY** (.ply) - простая геометрия

### Текстуры
- ✅ **PNG** (.png) - с прозрачностью
- ✅ **JPEG** (.jpg, .jpeg) - сжатые
- ✅ **TGA** (.tga) - игровые текстуры
- ✅ **TIFF** (.tif, .tiff) - высокое качество
- ✅ **EXR** (.exr) - HDR изображения
- ✅ **HDR** (.hdr) - IBL карты
- ✅ **PIC** (.pic) - нативный Houdini
- ✅ **RAT** (.rat) - оптимизированные

### Соглашения UDIM
- Поддержка диапазона 1001-1100
- Форматы: `texture.1001.jpg`, `texture_1001.png`
- Автоматическое определение последовательностей

## 🚀 Производительность

### Рекомендации по оптимизации

1. **Включите кэширование** для ускорения повторных импортов
2. **Организуйте файлы** в логичную структуру папок
3. **Используйте групповой импорт** для больших проектов
4. **Оптимизируйте текстуры** до импорта
5. **Регулярно очищайте кэш** от устаревших данных

### Ограничения

- Максимум 20 моделей в одной группе (настраивается)
- Размер кэша ограничен 1000 записями
- Таймаут операций: 5 минут
- Максимальная длина имени ноды: 30 символов

## 📞 Поддержка

При возникновении проблем:

1. **Проверьте логи** - включите режим отладки
2. **Очистите кэш** - через CacheManager
3. **Обновите пути** - убедитесь в правильности структуры
4. **Проверьте права доступа** к файлам и папкам

### Полезные команды

```python
# Диагностика
import hou
print(f"Houdini version: {hou.applicationVersion()}")
print(f"User dir: {hou.homeHoudiniDirectory()}")

# Проверка модулей
import sys
print("Available modules:")
for module in ["utils", "main", "material_utils"]:
    try:
        exec(f"import {module}")
        print(f"✅ {module}")
    except ImportError as e:
        print(f"❌ {module}: {e}")
```

---

## 🎉 Готово!

Теперь у вас есть полностью функциональный и отказоустойчивый загрузчик моделей для Houdini с автоматическим назначением материалов. Наслаждайтесь быстрым и удобным импортом ваших 3D ресурсов!