"""
Константы и настройки для загрузчика моделей - с поддержкой MaterialX, сетки и полной UDIM поддержкой
"""

# Поддерживаемые форматы файлов
SUPPORTED_MODEL_FORMATS = ['.fbx', '.obj', '.abc', '.bgeo', '.bgeo.sc', '.ply']
SUPPORTED_TEXTURE_FORMATS = ['.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff', '.exr', '.hdr', '.pic', '.rat']

# РАСШИРЕННЫЕ ключевые слова для определения типов текстур (обновлено с современными PBR соглашениями)
ENHANCED_TEXTURE_KEYWORDS = {
    "BaseMap": [
        # Классические названия
        "basemap", "diff", "dif", "diffuse", "albedo", "basecolor", "col", "color", 
        "base", "alb", "bc", "_d", "-d", "_c", "-c", "diffmap", "colormap", "diffusemap",
        # Современные PBR соглашения
        "_color", "_base", "_basecolor", "_albedo", "BaseColor", "Albedo", "Base_Color",
        # Вариации без подчеркивания  
        "BaseMap", "DiffuseMap", "ColorMap", "Diffuse", "Color"
    ],
    "Normal": [
        # Классические названия
        "normal", "norm", "nml", "nrm", "_n", "-n", "nor", "normalmap", "normalmaps",
        # Bump и height как альтернативы
        "bump", "bumpmap", "_bump", "_b", "-b", "relief", "bumpmaps",
        # Современные соглашения
        "Normal", "NormalMap", "Normal_Map", "_normal", "_norm", "_nml"
    ],
    "Roughness": [
        # Основные названия
        "rough", "roughness", "rgh", "_r", "-r", "roughnessmap", "roughmaps",
        # Gloss (инвертированный roughness)
        "gloss", "glossmap", "glossiness", "smoothness", "smooth",
        # Современные соглашения
        "Roughness", "RoughnessMap", "Rough", "_roughness", "_rough", "_rgh"
    ],
    "Metallic": [
        # Основные названия
        "metal", "metallic", "met", "metalness", "_m", "-m", "metallicmap", "metallicmaps",
        # Specular как альтернатива
        "spec", "specular", "_s", "-s", "specularmap", "specularmaps",
        # Современные соглашения  
        "Metallic", "MetallicMap", "Metal", "_metallic", "_metal", "_met"
    ],
    "AO": [
        # Основные названия
        "ao", "ambient", "occlusion", "ambientocclusion", "_ao", "-ao", 
        "occlusionmap", "ambientocclusionmap", "aomaps",
        # Современные соглашения
        "AO", "AmbientOcclusion", "Ambient_Occlusion", "_ambientocclusion"
    ],
    "Emissive": [
        # Основные названия  
        "emissive", "emission", "emit", "glow", "_e", "-e", "emissionmap",
        "emissivemap", "selfillum", "emissivemaps",
        # Современные соглашения
        "Emissive", "EmissiveMap", "Emission", "Emit", "_emissive", "_emission"
    ],
    "Height": [
        # Основные названия
        "height", "heightmap", "displacement", "disp", "_h", "-h", 
        "displacementmap", "parallax", "heightmaps",
        # Современные соглашения
        "Height", "HeightMap", "Displacement", "Disp", "_height", "_disp", "_displacement"
    ],
    "Bump": [
        # Основные названия (оставляем отдельно от Normal для обратной совместимости)
        "bump", "bumpmap", "_b", "-b", "relief", "bumpmaps",
        # Современные соглашения
        "Bump", "BumpMap", "_bump"
    ],
    "Opacity": [
        # Основные названия
        "opacity", "alpha", "transparent", "transparency", "_a", "-a", 
        "_o", "-o", "opacitymap", "alphamap", "mask", "opacitymaps",
        # Современные соглашения
        "Opacity", "OpacityMap", "Alpha", "AlphaMap", "_opacity", "_alpha"
    ],
    "Specular": [
        # Основные названия (отдельно от Metallic для non-PBR материалов)
        "specular", "spec", "_s", "-s", "specularmap", "reflection", "refl", "specularmaps",
        # Современные соглашения
        "Specular", "SpecularMap", "Reflection", "_specular", "_spec"
    ],
    "Translucency": [
        # Основные названия
        "translucency", "translucent", "subsurface", "sss", "_t", "-t",
        "subsurfacemap", "translucencymap", "scattering", "translucencymaps",
        # Современные соглашения
        "Translucency", "Subsurface", "SSS", "_translucency", "_subsurface", "_sss"
    ]
}

# Старые ключевые слова для обратной совместимости
DEFAULT_TEXTURE_KEYWORDS = ENHANCED_TEXTURE_KEYWORDS

# РАСШИРЕННАЯ UDIM конфигурация
UDIM_CONFIG = {
    # Основные настройки
    "pattern": r'^(.+)[._](\d{4})\.(jpg|jpeg|png|tga|tif|tiff|exr|hdr|pic|rat)$',
    "range_start": 1001,
    "range_end": 1100,
    "min_tiles": 2,  # Минимальное количество тайлов для определения как UDIM
    "placeholder": "<UDIM>",
    
    # Расширенные настройки
    "alternative_patterns": [
        # Альтернативные UDIM паттерны
        r'^(.+)\.(\d{4})\.(jpg|jpeg|png|tga|tif|tiff|exr|hdr|pic|rat)$',  # точка разделитель
        r'^(.+)_(\d{4})\.(jpg|jpeg|png|tga|tif|tiff|exr|hdr|pic|rat)$',   # подчеркивание разделитель
        r'^(.+)-(\d{4})\.(jpg|jpeg|png|tga|tif|tiff|exr|hdr|pic|rat)$',   # дефис разделитель
    ],
    
    # UDIM диапазоны для разных форматов
    "ranges": {
        "standard": {"start": 1001, "end": 1100},    # Стандартный UDIM 10x10
        "extended": {"start": 1001, "end": 1999},    # Расширенный диапазон
        "maya": {"start": 1001, "end": 1100},        # Maya UDIM
        "mari": {"start": 1001, "end": 1999},        # Mari UDIM (расширенный)
        "mudbox": {"start": 0, "end": 99}            # Mudbox использует 0-99
    },
    
    # Настройки валидации
    "validation": {
        "check_sequence_gaps": True,          # Проверять пропуски в последовательности
        "allow_single_tiles": False,         # Разрешать одиночные тайлы как UDIM
        "max_gap_tolerance": 5,              # Максимальный допустимый пропуск в последовательности
        "require_consecutive": False         # Требовать последовательные номера
    },
    
    # Настройки поиска
    "search": {
        "case_sensitive": False,             # Чувствительность к регистру
        "deep_scan": True,                   # Глубокое сканирование поддиректорий
        "cache_results": True,               # Кэшировать результаты поиска UDIM
        "group_by_material": True            # Группировать UDIM по материалам
    },
    
    # Настройки отображения и логирования
    "display": {
        "show_tile_count": True,             # Показывать количество тайлов
        "show_range": True,                  # Показывать диапазон тайлов
        "show_gaps": True,                   # Показывать пропуски в последовательности
        "compact_logging": False             # Компактное логирование
    },
    
    # Поддерживаемые плейсхолдеры
    "placeholders": {
        "standard": "<UDIM>",                # Стандартный плейсхолдер
        "alternative": ["<udim>", "%(UDIM)d", "$UDIM", "{UDIM}"],
        "custom_format": "<UDIM:04d>"        # Кастомный формат с нулями
    }
}

# Типы материалов и их приоритеты (теперь включая MaterialX)
MATERIAL_TYPES = {
    "principledshader": ["principledshader", "principledshader::2.0", "material"],
    "materialx": ["materialx", "usdpreviewsurface", "standardsurface", "principled_bsdf"],
    "redshift::Material": ["redshift::Material", "principledshader", "material"],
    "material": ["material", "principledshader"]
}

# Настройки по умолчанию с поддержкой MaterialX, UDIM и сетки
DEFAULT_SETTINGS = {
    "import_mode": "separate",  # separate, grouped, merged
    "material_type": "principledshader",  # principledshader, materialx, redshift::Material, material
    "scale_factor": 1.0,
    "use_cache": True,
    "texture_resolution": "original",
    "auto_assign_textures": True,
    "create_missing_uvs": False,
    "remove_namespaces": True,
    "create_lods": False,
    "triangulate": False,
    "weld_vertices": False,
    "weld_threshold": 0.001,
    "generate_report": True,
    "show_import_log": True,
    "debug_mode": False,
    "organize_nodes": True,
    "center_pivots": False,
    "convert_to_assets": False,
    
    # UDIM настройки
    "enable_udim": True,                     # Включить поддержку UDIM
    "udim_auto_detect": True,                # Автоматическое обнаружение UDIM
    "udim_min_tiles": 2,                     # Минимальное количество тайлов для UDIM
    "udim_validate_sequence": True,          # Валидировать UDIM последовательности
    "udim_show_statistics": True,            # Показывать статистику UDIM
    
    # Настройки сетки (для режима "merged")
    "enable_grid_layout": True,              # Включить размещение по сетке
    "grid_spacing": 10.0,                    # Расстояние между моделями в сетке
    "auto_calculate_grid": True,             # Автоматически вычислять размер сетки
    "grid_columns": 0,                       # Количество колонок (0 = автоматически)
    
    # MaterialX настройки
    "materialx_workflow": "solaris",         # solaris, lops, karma
    "materialx_enable_displacement": True,   # Включить displacement для MaterialX
    "materialx_auto_convert": False          # Автоматически конвертировать из других типов
}

# Ограничения и лимиты
LIMITS = {
    "max_models_per_group": 20,  # Максимальное количество моделей в одной группе
    "max_node_name_length": 30,  # Максимальная длина имени узла
    "max_cache_size": 1000,      # Максимальный размер кэша
    "max_import_attempts": 3,    # Максимальное количество попыток импорта модели
    "timeout_seconds": 300,      # Таймаут для операций импорта (в секундах)
    "batch_size": 20,           # Размер батча для обработки
    "progress_update_interval": 0.5,  # Интервал обновления прогресса в секундах
    
    # UDIM лимиты
    "max_udim_tiles": 100,       # Максимальное количество UDIM тайлов
    "max_udim_sequences": 50,    # Максимальное количество UDIM последовательностей
    "udim_scan_depth": 3,        # Максимальная глубина сканирования для UDIM
    
    # Лимиты сетки
    "max_grid_columns": 50,      # Максимальное количество колонок в сетке
    "min_grid_spacing": 1.0,     # Минимальное расстояние между моделями
    "max_grid_spacing": 100.0,   # Максимальное расстояние между моделями
    "max_models_in_grid": 1000   # Максимальное количество моделей в сетке
}

# Пути и директории
PATHS = {
    "cache_dir_name": "model_import_cache",
    "logs_dir_name": "model_import_logs",
    "settings_filename": "import_settings.json",
    "material_cache_filename": "material_cache.json",
    "node_names_cache_filename": "node_names_cache.json",
    "textures_cache_filename": "textures_cache.json",
    "udim_cache_filename": "udim_cache.json",      # Кэш для UDIM данных
    "materialx_cache_filename": "materialx_cache.json"  # Кэш для MaterialX материалов
}

# Шаблоны имен файлов
FILE_PATTERNS = {
    "log_file": "import_log_{timestamp}.log",
    "report_file": "import_report_{timestamp}.html",
    "backup_file": "{original_name}.backup",
    "udim_pattern": "{base_name}.{udim}.{extension}",    # Паттерн для UDIM файлов
    "udim_placeholder": "{base_name}.<UDIM>.{extension}", # Паттерн с плейсхолдером
    "materialx_shader": "mtlx_{material_name}_{timestamp}"  # Паттерн для MaterialX шейдеров
}

# Настройки генерации сетки для размещения моделей
GRID_SETTINGS = {
    "spacing_multiplier": 1.2,  # Множитель для расстояния между моделями
    "sqrt_multiplier": 1.5,     # Множитель для вычисления количества колонок
    "min_columns": 1,           # Минимальное количество колонок
    "max_columns": 10,          # Максимальное количество колонок
    "auto_spacing": True,       # Автоматически вычислять расстояние на основе размера моделей
    "padding_factor": 0.2,      # Фактор отступа (20% от размера модели)
    "enable_controller": True,   # Создавать контроллер сетки
    "controller_params": {      # Параметры контроллера
        "enable_grid": True,
        "grid_spacing": 10.0,
        "grid_columns": 0,      # 0 = автоматически
        "show_bounds": False    # Показывать границы моделей
    }
}

# Настройки Python SOP
PYTHON_SOP_CONFIG = {
    "function_name": "main",
    "import_statements": [
        "import hou",
        "import os",
        "import json",
        "import re",
        "import math"
    ],
    "max_code_length": 50000,  # Максимальная длина Python кода для SOP
    "enable_udim_support": True,  # Включить UDIM поддержку в генерируемом коде
    "enable_materialx_support": True  # Включить MaterialX поддержку в генерируемом коде
}

# Сообщения об ошибках с UDIM и MaterialX поддержкой
ERROR_MESSAGES = {
    "no_folder_selected": "Папка не выбрана.",
    "no_models_found": "Модели (.fbx / .obj / .abc) не найдены.",
    "no_obj_context": "Контекст /obj не найден!",
    "material_creation_failed": "Не удалось создать материал",
    "geometry_creation_failed": "Ошибка создания геометрии",
    "file_not_found": "Файл не существует",
    "invalid_path": "Некорректный путь к файлу",
    "cache_error": "Ошибка при работе с кэшем",
    "import_timeout": "Таймаут при импорте модели",
    "texture_assignment_failed": "Ошибка назначения текстур",
    
    # UDIM ошибки
    "udim_sequence_invalid": "Некорректная UDIM последовательность",
    "udim_tiles_missing": "Отсутствуют UDIM тайлы",
    "udim_pattern_error": "Ошибка в UDIM паттерне",
    
    # MaterialX ошибки
    "materialx_not_supported": "MaterialX не поддерживается в текущей версии Houdini",
    "materialx_creation_failed": "Не удалось создать MaterialX материал",
    "materialx_solaris_required": "MaterialX требует Solaris workflow",
    
    # Ошибки сетки
    "grid_creation_failed": "Не удалось создать контроллер сетки",
    "grid_spacing_invalid": "Некорректное расстояние в сетке",
    "too_many_models_for_grid": "Слишком много моделей для размещения в сетке"
}

# Предупреждения с UDIM, MaterialX и сеткой поддержкой
WARNING_MESSAGES = {
    "no_textures_found": "Внимание: Текстуры не найдены. Будут созданы материалы без текстур.",
    "large_model_count": "Большое количество моделей может замедлить работу.",
    "cache_disabled": "Кэширование отключено - это может замедлить повторные импорты.",
    "debug_mode_enabled": "Режим отладки включен - будет создано много логов.",
    "partial_texture_assignment": "Не все текстуры удалось назначить на материал.",
    
    # UDIM предупреждения
    "udim_incomplete_sequence": "Обнаружена неполная UDIM последовательность",
    "udim_mixed_formats": "Смешанные форматы в UDIM последовательности",
    "udim_large_sequence": "Большая UDIM последовательность может замедлить работу",
    
    # MaterialX предупреждения
    "materialx_fallback_to_principled": "MaterialX недоступен, используется Principled Shader",
    "materialx_limited_texture_support": "Некоторые типы текстур не поддерживаются в MaterialX",
    "materialx_requires_karma": "Для полной поддержки MaterialX рекомендуется Karma рендерер",
    
    # Предупреждения сетки
    "grid_auto_spacing_used": "Использовано автоматическое расстояние в сетке",
    "grid_many_models": "Большое количество моделей в сетке может повлиять на производительность",
    "grid_controller_recommended": "Рекомендуется использовать контроллер сетки для управления"
}

# Информационные сообщения с UDIM, MaterialX и сеткой поддержкой
INFO_MESSAGES = {
    "import_started": "Начат импорт моделей",
    "import_finished": "Импорт завершен",
    "cache_enabled": "Кэширование включено",
    "material_assigned": "Материал назначен",
    "texture_found": "Найдена текстура",
    "batch_processing": "Обработка батча моделей",
    "optimization_enabled": "Включена оптимизация производительности",
    
    # UDIM сообщения
    "udim_sequence_detected": "Обнаружена UDIM последовательность",
    "udim_tiles_processed": "UDIM тайлы обработаны",
    "udim_cache_updated": "Кэш UDIM обновлен",
    
    # MaterialX сообщения
    "materialx_workflow_enabled": "Включен MaterialX workflow",
    "materialx_material_created": "Создан MaterialX материал",
    "materialx_textures_assigned": "MaterialX текстуры назначены",
    
    # Сообщения сетки
    "grid_layout_enabled": "Включено размещение по сетке",
    "grid_controller_created": "Создан контроллер сетки",
    "grid_models_arranged": "Модели размещены в сетке"
}

# HTML шаблоны для отчетов (расширены для UDIM, MaterialX и сетки)
HTML_TEMPLATES = {
    "report_css": """
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            color: #333;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            margin-top: 0;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 10px;
        }
        h2 {
            color: #3498db;
            margin-top: 20px;
        }
        .summary {
            display: flex;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        .summary-item {
            flex: 1;
            min-width: 150px;
            padding: 15px;
            margin: 5px;
            border-radius: 4px;
            background-color: #ecf0f1;
        }
        .summary-item.success {
            background-color: #d5f5e3;
        }
        .summary-item.warning {
            background-color: #fdebd0;
        }
        .summary-item.error {
            background-color: #f5b7b1;
        }
        .summary-item.udim {
            background-color: #e8f4fd;
            border-left: 4px solid #3498db;
        }
        .summary-item.materialx {
            background-color: #f0e8ff;
            border-left: 4px solid #9b59b6;
        }
        .summary-item.grid {
            background-color: #e8f8f5;
            border-left: 4px solid #1abc9c;
        }
        .summary-item h3 {
            margin-top: 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th, td {
            padding: 8px 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #ecf0f1;
        }
        tr:hover {
            background-color: #f9f9f9;
        }
        .success {
            color: #27ae60;
        }
        .warning {
            color: #e67e22;
        }
        .error {
            color: #e74c3c;
        }
        .udim {
            color: #3498db;
            font-weight: bold;
        }
        .materialx {
            color: #9b59b6;
            font-weight: bold;
        }
        .grid {
            color: #1abc9c;
            font-weight: bold;
        }
        .udim-badge {
            background-color: #3498db;
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            margin-left: 5px;
        }
        .materialx-badge {
            background-color: #9b59b6;
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            margin-left: 5px;
        }
        .grid-badge {
            background-color: #1abc9c;
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            margin-left: 5px;
        }
        .collapsible {
            background-color: #f1f1f1;
            color: #444;
            cursor: pointer;
            padding: 18px;
            width: 100%;
            border: none;
            text-align: left;
            outline: none;
            font-size: 16px;
            margin-bottom: 1px;
        }
        .active, .collapsible:hover {
            background-color: #ddd;
        }
        .content {
            padding: 0 18px;
            display: none;
            overflow: hidden;
            background-color: #f9f9f9;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: #ecf0f1;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background-color: #3498db;
            transition: width 0.3s ease;
        }
    """
}

# Валидация настроек с UDIM, MaterialX и сеткой поддержкой
VALIDATION_RULES = {
    "import_mode": ["separate", "grouped", "merged"],
    "material_type": ["principledshader", "materialx", "redshift::Material", "material"],
    "texture_resolution": ["original", "1K", "2K", "4K"],
    "scale_factor_min": 0.01,
    "scale_factor_max": 100.0,
    "weld_threshold_min": 0.0001,
    "weld_threshold_max": 0.1,
    
    # UDIM валидация
    "udim_min_tiles_min": 1,
    "udim_min_tiles_max": 100,
    
    # Валидация сетки
    "grid_spacing_min": 1.0,
    "grid_spacing_max": 100.0,
    "grid_columns_min": 0,
    "grid_columns_max": 50,
    
    # MaterialX валидация
    "materialx_workflow": ["solaris", "lops", "karma"]
}

# Настройки производительности с UDIM, MaterialX и сеткой поддержкой
PERFORMANCE_CONFIG = {
    "enable_multithreading": False,  # Пока отключено для стабильности
    "memory_optimization": True,
    "cache_texture_searches": True,
    "lazy_material_creation": True,
    "batch_node_creation": True,
    "progress_reporting": True,
    
    # UDIM производительность
    "udim_parallel_processing": False,  # Параллельная обработка UDIM
    "udim_memory_limit": 1024,         # Лимит памяти для UDIM (MB)
    "udim_cache_size": 200,            # Размер кэша UDIM
    
    # MaterialX производительность
    "materialx_cache_enabled": True,    # Кэширование MaterialX материалов
    "materialx_async_creation": False,  # Асинхронное создание MaterialX
    "materialx_batch_assignment": True, # Батчевое назначение MaterialX текстур
    
    # Производительность сетки
    "grid_lazy_layout": True,          # Ленивое размещение в сетке
    "grid_batch_transform": True,      # Батчевые трансформации
    "grid_optimize_spacing": True      # Оптимизация расстояний в сетке
}

# Конфигурация отладки с UDIM, MaterialX и сеткой поддержкой
DEBUG_CONFIG = {
    "verbose_texture_search": True,
    "log_material_parameters": True,
    "trace_performance": True,
    "validate_file_paths": True,
    "check_node_creation": True,
    
    # UDIM отладка
    "udim_verbose_logging": True,      # Подробное логирование UDIM
    "udim_trace_sequences": True,      # Трассировка UDIM последовательностей
    "udim_validate_tiles": True,       # Валидация каждого UDIM тайла
    
    # MaterialX отладка
    "materialx_verbose_logging": True, # Подробное логирование MaterialX
    "materialx_trace_creation": True,  # Трассировка создания MaterialX
    "materialx_validate_params": True, # Валидация параметров MaterialX
    
    # Отладка сетки
    "grid_verbose_logging": True,      # Подробное логирование сетки
    "grid_trace_layout": True,         # Трассировка размещения в сетке
    "grid_validate_positions": True    # Валидация позиций в сетке
}


def validate_settings(settings_dict):
    """Валидирует настройки импорта с расширенными проверками включая UDIM, MaterialX и сетку"""
    errors = []
    
    if not isinstance(settings_dict, dict):
        errors.append("Настройки должны быть словарем")
        return errors
    
    # Проверяем обязательные поля
    for key, valid_values in VALIDATION_RULES.items():
        if key.endswith('_min') or key.endswith('_max'):
            continue
            
        if isinstance(valid_values, list):
            if key in settings_dict and settings_dict[key] not in valid_values:
                errors.append(f"Некорректное значение для {key}: {settings_dict[key]}. Допустимые: {valid_values}")
    
    # Проверяем числовые ограничения
    if "scale_factor" in settings_dict:
        value = settings_dict["scale_factor"]
        if not isinstance(value, (int, float)):
            errors.append("scale_factor должен быть числом")
        elif not (VALIDATION_RULES["scale_factor_min"] <= value <= VALIDATION_RULES["scale_factor_max"]):
            errors.append(f"scale_factor должен быть между {VALIDATION_RULES['scale_factor_min']} и {VALIDATION_RULES['scale_factor_max']}")
    
    if "weld_threshold" in settings_dict:
        value = settings_dict["weld_threshold"]
        if not isinstance(value, (int, float)):
            errors.append("weld_threshold должен быть числом")
        elif not (VALIDATION_RULES["weld_threshold_min"] <= value <= VALIDATION_RULES["weld_threshold_max"]):
            errors.append(f"weld_threshold должен быть между {VALIDATION_RULES['weld_threshold_min']} и {VALIDATION_RULES['weld_threshold_max']}")
    
    # Проверяем UDIM настройки
    if "udim_min_tiles" in settings_dict:
        value = settings_dict["udim_min_tiles"]
        if not isinstance(value, int):
            errors.append("udim_min_tiles должен быть целым числом")
        elif not (VALIDATION_RULES["udim_min_tiles_min"] <= value <= VALIDATION_RULES["udim_min_tiles_max"]):
            errors.append(f"udim_min_tiles должен быть между {VALIDATION_RULES['udim_min_tiles_min']} и {VALIDATION_RULES['udim_min_tiles_max']}")
    
    # Проверяем настройки сетки
    if "grid_spacing" in settings_dict:
        value = settings_dict["grid_spacing"]
        if not isinstance(value, (int, float)):
            errors.append("grid_spacing должен быть числом")
        elif not (VALIDATION_RULES["grid_spacing_min"] <= value <= VALIDATION_RULES["grid_spacing_max"]):
            errors.append(f"grid_spacing должен быть между {VALIDATION_RULES['grid_spacing_min']} и {VALIDATION_RULES['grid_spacing_max']}")
    
    if "grid_columns" in settings_dict:
        value = settings_dict["grid_columns"]
        if not isinstance(value, int):
            errors.append("grid_columns должен быть целым числом")
        elif not (VALIDATION_RULES["grid_columns_min"] <= value <= VALIDATION_RULES["grid_columns_max"]):
            errors.append(f"grid_columns должен быть между {VALIDATION_RULES['grid_columns_min']} и {VALIDATION_RULES['grid_columns_max']}")
    
    # Проверяем логические значения
    bool_settings = [
        'use_cache', 'auto_assign_textures', 'create_missing_uvs', 'remove_namespaces', 
        'create_lods', 'triangulate', 'weld_vertices', 'generate_report', 'show_import_log', 
        'debug_mode', 'organize_nodes', 'center_pivots', 'convert_to_assets',
        'enable_udim', 'udim_auto_detect', 'udim_validate_sequence', 'udim_show_statistics',
        'enable_grid_layout', 'auto_calculate_grid', 'materialx_enable_displacement', 'materialx_auto_convert'
    ]
    
    for bool_setting in bool_settings:
        if bool_setting in settings_dict and not isinstance(settings_dict[bool_setting], bool):
            errors.append(f"{bool_setting} должен быть логическим значением (True/False)")
    
    # Проверяем совместимость MaterialX с режимом импорта
    if settings_dict.get("material_type") == "materialx" and settings_dict.get("import_mode") != "merged":
        errors.append("MaterialX рекомендуется использовать с режимом 'Все в один узел' для лучшей совместимости с Solaris")
    
    return errors


def get_default_settings():
    """Возвращает копию настроек по умолчанию"""
    return DEFAULT_SETTINGS.copy()


def get_texture_keywords():
    """Возвращает копию расширенных ключевых слов для текстур"""
    return {k: v.copy() for k, v in ENHANCED_TEXTURE_KEYWORDS.items()}


def get_material_types():
    """Возвращает доступные типы материалов включая MaterialX"""
    return list(MATERIAL_TYPES.keys())


def get_performance_config():
    """Возвращает конфигурацию производительности"""
    return PERFORMANCE_CONFIG.copy()


def get_debug_config():
    """Возвращает конфигурацию отладки"""
    return DEBUG_CONFIG.copy()


def get_udim_config():
    """Возвращает конфигурацию UDIM"""
    return UDIM_CONFIG.copy()


def get_grid_settings():
    """Возвращает настройки сетки"""
    return GRID_SETTINGS.copy()


def is_supported_model_format(file_path):
    """Проверяет, поддерживается ли формат модели"""
    if not file_path:
        return False
    
    return any(file_path.lower().endswith(ext) for ext in SUPPORTED_MODEL_FORMATS)


def is_supported_texture_format(file_path):
    """Проверяет, поддерживается ли формат текстуры"""
    if not file_path:
        return False
    
    return any(file_path.lower().endswith(ext) for ext in SUPPORTED_TEXTURE_FORMATS)


def get_texture_type_by_filename(filename):
    """Определяет тип текстуры по имени файла"""
    if not filename:
        return "BaseMap"
    
    filename_lower = filename.lower()
    
    for texture_type, keywords in ENHANCED_TEXTURE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in filename_lower:
                return texture_type
    
    return "BaseMap"


def is_udim_filename(filename):
    """Проверяет, соответствует ли имя файла UDIM паттерну"""
    if not filename:
        return False
    
    import re
    
    # Проверяем основной паттерн
    main_pattern = re.compile(UDIM_CONFIG["pattern"], re.IGNORECASE)
    if main_pattern.match(filename):
        return True
    
    # Проверяем альтернативные паттерны
    for alt_pattern in UDIM_CONFIG.get("alternative_patterns", []):
        alt_regex = re.compile(alt_pattern, re.IGNORECASE)
        if alt_regex.match(filename):
            return True
    
    return False


def extract_udim_info(filename):
    """Извлекает информацию о UDIM из имени файла"""
    if not filename:
        return None
    
    import re
    
    # Пробуем основной паттерн
    main_pattern = re.compile(UDIM_CONFIG["pattern"], re.IGNORECASE)
    match = main_pattern.match(filename)
    
    if match:
        return {
            "base_name": match.group(1),
            "udim_number": int(match.group(2)),
            "extension": match.group(3),
            "pattern_type": "main"
        }
    
    # Пробуем альтернативные паттерны
    for i, alt_pattern in enumerate(UDIM_CONFIG.get("alternative_patterns", [])):
        alt_regex = re.compile(alt_pattern, re.IGNORECASE)
        match = alt_regex.match(filename)
        
        if match:
            return {
                "base_name": match.group(1),
                "udim_number": int(match.group(2)),
                "extension": match.group(3),
                "pattern_type": f"alternative_{i}"
            }
    
    return None


def is_materialx_supported():
    """Проверяет, поддерживается ли MaterialX в текущей версии Houdini"""
    try:
        import hou
        # Проверяем наличие MaterialX нод
        node_types = hou.nodeTypeCategories()["Vop"].nodeTypes()
        return "materialx" in node_types or "usdpreviewsurface" in node_types
    except Exception:
        return False


def get_optimal_grid_layout(model_count):
    """Возвращает оптимальное расположение сетки для количества моделей"""
    if model_count <= 0:
        return {"columns": 1, "rows": 1}
    
    import math
    
    # Стремимся к квадратной сетке
    columns = max(1, int(math.sqrt(model_count)))
    rows = max(1, math.ceil(model_count / columns))
    
    # Корректируем для лучшего соотношения сторон
    if rows > columns * 1.5:
        columns += 1
        rows = math.ceil(model_count / columns)
    
    return {
        "columns": columns,
        "rows": rows,
        "total_cells": columns * rows,
        "efficiency": model_count / (columns * rows)
    }


def print_supported_formats():
    """Выводит список поддерживаемых форматов"""
    print("Поддерживаемые форматы моделей:")
    for fmt in SUPPORTED_MODEL_FORMATS:
        print(f"  {fmt}")
    
    print("\nПоддерживаемые форматы текстур:")
    for fmt in SUPPORTED_TEXTURE_FORMATS:
        print(f"  {fmt}")


def print_texture_keywords():
    """Выводит список ключевых слов для текстур"""
    print("Ключевые слова для определения типов текстур:")
    for texture_type, keywords in ENHANCED_TEXTURE_KEYWORDS.items():
        print(f"\n{texture_type}:")
        for keyword in keywords:
            print(f"  {keyword}")


def print_material_types():
    """Выводит поддерживаемые типы материалов"""
    print("Поддерживаемые типы материалов:")
    for material_type, fallbacks in MATERIAL_TYPES.items():
        print(f"\n{material_type}:")
        print(f"  Основной: {fallbacks[0]}")
        if len(fallbacks) > 1:
            print(f"  Fallback: {', '.join(fallbacks[1:])}")


def print_udim_config():
    """Выводит конфигурацию UDIM"""
    print("UDIM конфигурация:")
    print(f"  Диапазон: {UDIM_CONFIG['range_start']}-{UDIM_CONFIG['range_end']}")
    print(f"  Минимум тайлов: {UDIM_CONFIG['min_tiles']}")
    print(f"  Плейсхолдер: {UDIM_CONFIG['placeholder']}")
    print(f"  Основной паттерн: {UDIM_CONFIG['pattern']}")
    
    alt_patterns = UDIM_CONFIG.get("alternative_patterns", [])
    if alt_patterns:
        print(f"  Альтернативные паттерны: {len(alt_patterns)}")
        for i, pattern in enumerate(alt_patterns):
            print(f"    {i+1}. {pattern}")


def print_grid_settings():
    """Выводит настройки сетки"""
    print("Настройки сетки:")
    grid_settings = get_grid_settings()
    for key, value in grid_settings.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for sub_key, sub_value in value.items():
                print(f"    {sub_key}: {sub_value}")
        else:
            print(f"  {key}: {value}")