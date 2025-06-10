# Документация по системе MaterialX

## Обзор

Новая система MaterialX для загрузчика моделей Houdini представляет собой модульную архитектуру для создания сложных сетей шейдеров MaterialX с автоматическим назначением текстур.

## Архитектура системы

### Основные компоненты

1. **MaterialXBuilder** (`materialx_builder.py`)
   - Создает полноценные MaterialX сети шейдеров
   - Автоматически создает image ноды для каждой текстуры
   - Подключает текстуры к правильным входам MaterialX поверхности
   - Размещает ноды в network editor

2. **PrincipledBuilder** (`principled_builder.py`)
   - Создает Principled Shader материалы
   - Поддерживает Redshift материалы
   - Настраивает texture ноды с правильными color space
   - Подключает текстуры к шейдеру

3. **MaterialBuilderManager** (`material_builder_manager.py`)
   - Универсальный менеджер для всех типов материалов
   - Автоматически выбирает лучший тип материала
   - Проверяет доступность различных типов материалов
   - Предоставляет единый API

## Установка

### Структура файлов

```
$HOUDINI_USER_PREF_DIR/scripts/python/fbx_loader/
├── materialx_builder.py          # Новый - MaterialX Builder
├── principled_builder.py         # Новый - Principled Builder  
├── material_builder_manager.py   # Новый - Универсальный менеджер
├── material_utils.py            # Обновлен для интеграции
├── main.py                      # Обновлен для новой системы
├── test_materialx_system.py     # Новый - Тестирование
├── utils.py
├── constants.py
├── udim_utils.py
├── model_processor.py
├── settings_dialog.py
├── logger.py
├── cache_manager.py
└── shelf_tool.py
```

### Проверка установки

Запустите тест системы:

```python
# В Python Shell Houdini
exec(open("$HOUDINI_USER_PREF_DIR/scripts/python/fbx_loader/test_materialx_system.py").read())
```

## Использование

### Основной интерфейс

1. **Запуск через полку Houdini**
   - Используйте кнопку на полке как обычно
   - В диалоге настроек выберите тип материала:
     - `MaterialX Solaris` - для современных USD/Karma workflow
     - `Principled Shader` - для традиционного рендеринга
     - `Redshift Material` - для Redshift рендеринга

2. **Автоматический выбор типа материала**
   - Система автоматически определяет лучший тип материала
   - Учитывает наличие UDIM текстур
   - Проверяет доступность MaterialX в Houdini

### Программное использование

#### Создание MaterialX материала

```python
from material_builder_manager import create_material_universal

# Создание MaterialX материала
texture_maps = {
    "BaseMap": "/path/to/basecolor.<UDIM>.jpg",
    "Normal": "/path/to/normal.<UDIM>.png",
    "Roughness": "/path/to/roughness.<UDIM>.exr",
    "Metallic": "/path/to/metallic.<UDIM>.tga"
}

matnet = hou.node("/obj/materials")
material = create_material_universal(
    matnet, 
    "my_material", 
    texture_maps, 
    "materialx"
)
```

#### Создание Principled материала

```python
material = create_material_universal(
    matnet,
    "my_material", 
    texture_maps,
    "principledshader"
)
```

#### Автоматический выбор типа

```python
material = create_material_universal(
    matnet,
    "my_material",
    texture_maps,
    "auto"  # Автоматический выбор
)
```

## Возможности MaterialX системы

### MaterialX Builder

**Создаваемые ноды:**
- `mtlxstandardsurface` или `usdpreviewsurface` (основная поверхность)
- `mtlximage` ноды для каждой текстуры
- `material` нода-обертка

**Поддерживаемые текстуры:**
- BaseMap → `base_color`
- Normal → `normal`
- Roughness → `specular_roughness`
- Metallic → `metalness`
- AO → `diffuse_roughness`
- Emissive → `emission_color`
- Opacity → `opacity`
- Height → `displacement`

**Особенности:**
- Автоматическая настройка color space для разных типов текстур
- Полная поддержка UDIM последовательностей
- Правильное размещение нод в network editor
- Подключение через выходы image нод (color/float/vector)

### Principled Builder

**Создаваемые ноды:**
- `principledshader` или `principledshader::2.0`
- `texture` ноды для каждой текстуры
- Поддержка `redshift::Material`

**Подключения:**
- BaseMap → `basecolor_texture`
- Normal → `baseNormal_texture` (с активацией `baseBumpAndNormal_enable`)
- Roughness → `rough_texture`
- Metallic → `metallic_texture`
- AO → `baseAO_texture`
- Emissive → `emissive_texture`
- Opacity → `opac_texture`

## UDIM поддержка

### Автоматическое обнаружение

Система автоматически:
- Обнаруживает UDIM последовательности (1001, 1002, 1003...)
- Создает пути с `<UDIM>` плейсхолдерами
- Группирует тайлы по базовому имени
- Валидирует последовательности

### Примеры UDIM путей

```
Входные файлы:
- texture_basecolor.1001.jpg
- texture_basecolor.1002.jpg  
- texture_basecolor.1003.jpg

Результат:
- /path/to/texture_basecolor.<UDIM>.jpg
```

## API Reference

### MaterialBuilderManager

```python
class MaterialBuilderManager:
    def create_material(matnet_node, material_name, texture_maps, material_type)
    def get_recommended_material_type(texture_maps=None)
    def get_available_material_types()
    def validate_material_type(material_type)
    def get_capabilities_info()
```

### MaterialXBuilder

```python
class MaterialXBuilder:
    def __init__(matnet_node, material_name, logger=None)
    def create_material_network(texture_maps)
    def get_created_nodes()
    def get_main_material_node()
```

### PrincipledBuilder

```python
class PrincipledBuilder:
    def __init__(matnet_node, material_name, material_type, logger=None)
    def create_material_network(texture_maps)
    def get_created_nodes()
    def get_main_material_node()
```

## Диагностика и отладка

### Проверка возможностей

```python
from material_builder_manager import get_material_manager

manager = get_material_manager()
manager.print_capabilities_info()
```

### Тестирование системы

```python
# Запуск полного теста
from test_materialx_system import run_full_test
results = run_full_test()
```

### Логирование

Система поддерживает подробное логирование:

```python
from logger import ImportLogger

logger = ImportLogger(debug_mode=True)
material = create_material_universal(
    matnet, "test_material", textures, "materialx"
)
# Логи будут содержать детальную информацию о создании MaterialX сети
```

## Совместимость

### Требования Houdini

- **MaterialX**: Houdini 18.5+ с поддержкой MaterialX нод
- **USD/Solaris**: Рекомендуется Houdini 19.0+ для полной MaterialX поддержки
- **Karma**: Для лучшей MaterialX поддержки

### Обратная совместимость

Система полностью обратно совместима:
- Если новая система недоступна, используется legacy код
- Старые скрипты продолжают работать без изменений
- Fallback на Principled Shader при недоступности MaterialX

## Примеры использования

### Пример 1: Создание MaterialX для USD рендеринга

```python
import hou
from material_builder_manager import MaterialBuilderManager

# Создаем менеджер
manager = MaterialBuilderManager()

# Проверяем возможности
if manager.capabilities["materialx"]:
    # Создаем MaterialX материал
    matnet = hou.node("/obj").createNode("matnet", "usd_materials")
    
    textures = {
        "BaseMap": "/textures/wood_basecolor.<UDIM>.jpg",
        "Normal": "/textures/wood_normal.<UDIM>.png",
        "Roughness": "/textures/wood_roughness.<UDIM>.exr"
    }
    
    material = manager.create_material(
        matnet, "wood_material", textures, "materialx"
    )
    
    print(f"Created MaterialX material: {material.path()}")
```

### Пример 2: Автоматический выбор типа материала

```python
from material_builder_manager import create_material_universal

# Система автоматически выберет лучший тип
material = create_material_universal(
    matnet,
    "auto_material",
    texture_maps,
    "auto"  # Автоматический выбор
)
```

### Пример 3: Массовое создание материалов

```python
from material_builder_manager import get_material_manager

manager = get_material_manager()
materials = []

for material_name, textures in material_data.items():
    material_type = manager.get_recommended_material_type(textures)
    material = manager.create_material(
        matnet, material_name, textures, material_type
    )
    materials.append(material)
```

## Часто задаваемые вопросы

### Q: Как узнать, поддерживается ли MaterialX в моей версии Houdini?

A: Используйте функцию проверки:

```python
from materialx_builder import is_materialx_available
print("MaterialX доступен:", is_materialx_available())
```

### Q: Что делать, если MaterialX недоступен?

A: Система автоматически использует fallback на Principled Shader. Никаких дополнительных действий не требуется.

### Q: Как создать MaterialX материал программно?

A: См. примеры в разделе "Программное использование" выше.

### Q: Поддерживаются ли UDIM текстуры в MaterialX?

A: Да, полностью поддерживаются. Система автоматически обнаруживает UDIM последовательности и создает правильные пути с `<UDIM>` плейсхолдерами.

### Q: Можно ли использовать систему с другими рендерерами?

A: Да:
- MaterialX работает с Karma, Arnold (с USD)
- Principled Shader работает с Mantra, Karma
- Redshift Material работает с Redshift

## Changelog

### v2.0 (Новая система MaterialX)
- ✅ Добавлен MaterialXBuilder для создания полноценных MaterialX сетей
- ✅ Добавлен PrincipledBuilder для улучшенных Principled материалов
- ✅ Добавлен MaterialBuilderManager как универсальный API
- ✅ Полная поддержка UDIM в MaterialX
- ✅ Автоматический выбор типа материала
- ✅ Обратная совместимость с существующими скриптами
- ✅ Подробное логирование процесса создания материалов
- ✅ Система тестирования и диагностики

### v1.x (Legacy система)
- Базовое создание MaterialX нод без сетей
- Ограниченная поддержка UDIM
- Только Principled Shader с основными возможностями