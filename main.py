"""
Упрощенный главный модуль для импорта моделей без дублирования кода
"""
import hou
import os
import json
import re
import time
import math
from utils import clean_node_name, generate_unique_name, get_node_bbox, arrange_models_in_grid, safe_create_node, validate_file_path

# Импорт модулей с fallback
try:
    from material_utils import find_matching_textures, create_material_universal, get_texture_keywords,create_materialx_shader_improved,create_principled_shader
    MATERIAL_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Система материалов недоступна: {e}")
    MATERIAL_SYSTEM_AVAILABLE = False

try:
    from udim_utils import get_udim_statistics, print_udim_info
    UDIM_AVAILABLE = True
except ImportError:
    UDIM_AVAILABLE = False

# Импортируем константы
try:
    from constants import (
        SUPPORTED_MODEL_FORMATS, SUPPORTED_TEXTURE_FORMATS, ENHANCED_TEXTURE_KEYWORDS,
        LIMITS, ERROR_MESSAGES, WARNING_MESSAGES, INFO_MESSAGES
    )
except ImportError:
    # Fallback константы
    SUPPORTED_MODEL_FORMATS = ['.fbx', '.obj', '.abc', '.bgeo', '.bgeo.sc', '.ply']
    SUPPORTED_TEXTURE_FORMATS = ['.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff', '.exr', '.hdr']
    ENHANCED_TEXTURE_KEYWORDS = {
        "BaseMap": ["basemap", "diff", "dif", "albedo", "basecolor", "col", "color", "base"],
        "Normal": ["normal", "norm", "nml", "nrm", "_n", "-n", "nor"],
        "Roughness": ["rough", "roughness", "rgh", "gloss", "glossmap", "glossiness", "_r", "-r"],
        "Metallic": ["metal", "metallic", "met", "metalness", "_m", "-m"],
        "AO": ["ao", "ambient", "occlusion", "ambientocclusion", "_ao", "-ao"],
        "Emissive": ["emissive", "emission", "emit", "glow", "_e", "-e"]
    }
    LIMITS = {"max_models_per_group": 20, "timeout_seconds": 300}
    ERROR_MESSAGES = {
        "no_folder_selected": "Папка не выбрана.",
        "no_models_found": "Модели не найдены.",
        "no_obj_context": "Контекст /obj не найден!"
    }
    WARNING_MESSAGES = {"no_textures_found": "Внимание: Текстуры не найдены."}
    INFO_MESSAGES = {"import_started": "Начат импорт моделей"}


class ProgressTracker:
    """Класс для отслеживания прогресса"""
    
    def __init__(self, total_items, title="Прогресс импорта"):
        self.total_items = total_items
        self.current_item = 0
        self.title = title
        self.start_time = time.time()
        self.last_update_time = time.time()
        
        print(f"Начат процесс: {title} (всего элементов: {total_items})")
    
    def update(self, increment=1, description=""):
        """Обновляет прогресс"""
        self.current_item += increment
        current_time = time.time()
        
        # Обновляем каждые 0.5 секунды или при завершении
        if (current_time - self.last_update_time > 0.5 or 
            self.current_item >= self.total_items):
            
            percentage = (self.current_item / self.total_items) * 100
            elapsed_time = current_time - self.start_time
            
            if self.current_item > 0:
                eta = (elapsed_time / self.current_item) * (self.total_items - self.current_item)
                eta_str = f", осталось: {eta:.1f}с"
            else:
                eta_str = ""
            
            status_msg = f"{self.title}: {self.current_item}/{self.total_items} ({percentage:.1f}%){eta_str}"
            if description:
                status_msg += f" - {description}"
            
            print(status_msg)
            self.last_update_time = current_time
    
    def finish(self):
        """Завершает отслеживание прогресса"""
        total_time = time.time() - self.start_time
        print(f"Завершено: {self.title} за {total_time:.2f} секунд")


# =============== ОСНОВНЫЕ ФУНКЦИИ ИМПОРТА ===============

def create_multi_material_models_optimized(merge_models=False, settings=None, logger=None, cache_manager=None):
    """
    Оптимизированная функция импорта с отдельными материалами
    """
    start_time = time.time()
    
    try:
        # Проверяем среду
        obj_node = validate_import_environment()
        
        # Получаем путь к папке
        folder_path = get_folder_path_from_user()
        if not folder_path:
            if logger:
                logger.log_warning("Импорт отменен: папка не выбрана")
            hou.ui.displayMessage(ERROR_MESSAGES["no_folder_selected"], severity=hou.severityType.Error)
            return
        
        if logger:
            logger.log_import_start(folder_path, settings)
        
        print("=" * 60)
        print("ОПТИМИЗИРОВАННЫЙ ИМПОРТ МОДЕЛЕЙ")
        print("=" * 60)
        
        # Поиск файлов
        print("Поиск файлов...")
        model_files = find_model_files_optimized(folder_path, logger)
        if not model_files:
            if logger:
                logger.log_error("Импорт прерван: модели не найдены")
            hou.ui.displayMessage(ERROR_MESSAGES["no_models_found"], severity=hou.severityType.Error)
            return
        
        texture_files = find_texture_files_optimized(folder_path, logger)
        
        # Создаем matnet
        material_type = getattr(settings, 'material_type', 'principledshader')
        matnet = safe_create_node(obj_node, "matnet", "materials", allow_edit=True)
        print(f"Создан matnet для материалов типа: {material_type}")
        
        # Импорт моделей
        if merge_models:
            result = import_models_grouped(model_files, texture_files, matnet, folder_path, material_type, settings, logger, cache_manager)
        else:
            result = import_models_separate(model_files, texture_files, matnet, folder_path, material_type, settings, logger, cache_manager)
        
        # Статистика
        total_time = time.time() - start_time
        success_msg = f"Импорт завершен за {total_time:.2f} секунд!"
        success_msg += f"\nИмпортировано {len(model_files)} моделей"
        success_msg += f"\nТип материалов: {material_type}"
        success_msg += f"\nНайдено текстур: {len(texture_files)}"
        
        print("=" * 60)
        print("ИМПОРТ ЗАВЕРШЕН")
        print("=" * 60)
        print(success_msg)
        
        hou.ui.displayMessage(success_msg)
        
        if logger:
            logger.log_debug(success_msg)
        
        return result
        
    except Exception as e:
        error_msg = f"Критическая ошибка в импорте: {e}"
        print(f"ERROR: {error_msg}")
        if logger:
            logger.log_error(error_msg)
        hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
        return None


def create_unified_model_import_enhanced(settings=None, logger=None, cache_manager=None):
    """
    Улучшенный unified импорт - все модели в одну геометрию с сеткой
    """
    start_time = time.time()
    
    try:
        # Проверяем среду
        obj_node = validate_import_environment()
        
        # Получаем путь к папке
        folder_path = get_folder_path_from_user()
        if not folder_path:
            if logger:
                logger.log_warning("Импорт отменен: папка не выбрана")
            hou.ui.displayMessage(ERROR_MESSAGES["no_folder_selected"], severity=hou.severityType.Error)
            return
        
        if logger:
            logger.log_import_start(folder_path, settings)
        
        print("=" * 60)
        print("UNIFIED ИМПОРТ С СЕТКОЙ")
        print("=" * 60)
        
        # Поиск файлов
        print("Поиск файлов...")
        model_files = find_model_files_optimized(folder_path, logger)
        if not model_files:
            if logger:
                logger.log_error("Импорт прерван: модели не найдены")
            hou.ui.displayMessage(ERROR_MESSAGES["no_models_found"], severity=hou.severityType.Error)
            return
        
        texture_files = find_texture_files_optimized(folder_path, logger)
        
        # Создаем основной geo-узел
        folder_name = os.path.basename(folder_path)
        geo_name = clean_node_name(folder_name) if folder_name else "imported_models_geo"
        unique_geo_name = generate_unique_name(obj_node, "geo", geo_name)
        geo_node = safe_create_node(obj_node, "geo", unique_geo_name, allow_edit=True)
        
        # Создаем matnet
        material_type = getattr(settings, 'material_type', 'principledshader')
        matnet = safe_create_node(obj_node, "matnet", "materials", allow_edit=True)
        print(f"Создан matnet для материалов типа: {material_type}")
        
        # Импорт моделей с атрибутами
        print("Импорт моделей с атрибутами...")
        progress = ProgressTracker(len(model_files), "Импорт файлов")
        
        imported_models_info = []
        file_nodes = []
        
        for i, model_file in enumerate(model_files):
            try:
                progress.update(1, f"Файл: {os.path.basename(model_file)}")
                
                model_basename = os.path.basename(model_file)
                model_name = os.path.splitext(model_basename)[0]
                safe_model_name = clean_node_name(model_name)
                
                file_node_name = f"file_{i:04d}_{safe_model_name}" if safe_model_name else f"file_{i:04d}"
                file_node = geo_node.createNode("file", file_node_name)
                file_node.parm("file").set(model_file)
                
                # Добавляем атрибуты для Python SOP
                attrib_create = geo_node.createNode("attribcreate", f"name_{i:04d}")
                attrib_create.setInput(0, file_node)
                attrib_create.parm("name1").set("model_name")
                attrib_create.parm("class1").set(1)  # Primitive
                attrib_create.parm("type1").set(3)   # String
                attrib_create.parm("string1").set(model_name)
                
                attrib_create2 = geo_node.createNode("attribcreate", f"index_{i:04d}")
                attrib_create2.setInput(0, attrib_create)
                attrib_create2.parm("name1").set("model_index")
                attrib_create2.parm("class1").set(1)  # Primitive
                attrib_create2.parm("type1").set(0)   # Integer
                attrib_create2.parm("value1v1").set(i)
                
                file_nodes.append(attrib_create2)
                
                # Размещаем ноды
                file_node.moveToGoodPosition()
                attrib_create.moveToGoodPosition()
                attrib_create2.moveToGoodPosition()
                
                imported_models_info.append({
                    "file_node": file_node_name,
                    "model_path": model_file,
                    "model_basename": model_basename,
                    "model_name": model_name,
                    "index": i
                })
                
                if logger:
                    logger.log_model_processed(model_file, file_node.path())
                
            except Exception as e:
                error_msg = f"Ошибка импорта модели {model_file}: {e}"
                print(f"ERROR: {error_msg}")
                if logger:
                    logger.log_model_failed(model_file, str(e))
                continue
        
        progress.finish()
        
        # Создаем merge для объединения всех моделей
        merge_node = geo_node.createNode("merge", "merge_all_models")
        for file_node in file_nodes:
            merge_node.setNextInput(file_node)
        
        # Создание материала
        print("Создание материала...")
        folder_name = os.path.basename(folder_path)
        material_name = folder_name if folder_name else "unified_material"
        
        created_material = create_enhanced_material(
            matnet, material_name, texture_files,
            ENHANCED_TEXTURE_KEYWORDS, material_type, logger
        )
        
        if created_material:
            print(f"✓ Создан материал: {created_material.path()}")
            material_path = created_material.path()
        else:
            print("✗ Не удалось создать материал")
            material_path = ""
        
        # Создаем Python SOP для назначения материала и сетки
        python_node = geo_node.createNode("python", "assign_material_and_grid")
        python_node.setInput(0, merge_node)
        
        # Генерируем Python код
        python_code = generate_unified_python_code(
            imported_models_info, folder_path, texture_files,
            material_path, material_type, settings, logger
        )
        python_node.parm("python").set(python_code)
        
        # Настройка отображения
        python_node.setDisplayFlag(True)
        python_node.setRenderFlag(True)
        
        # Output null
        null_node = geo_node.createNode("null", "OUT")
        null_node.setInput(0, python_node)
        null_node.setDisplayFlag(True)
        null_node.setRenderFlag(True)
        
        # Размещаем ноды
        merge_node.moveToGoodPosition()
        python_node.moveToGoodPosition()
        null_node.moveToGoodPosition()
        matnet.moveToGoodPosition()
        geo_node.moveToGoodPosition()
        
        # Статистика
        total_time = time.time() - start_time
        success_msg = f"Unified импорт завершен за {total_time:.2f} секунд!"
        success_msg += f"\nИмпортировано {len(model_files)} моделей"
        success_msg += f"\nТип материалов: {material_type}"
        success_msg += f"\nНайдено текстур: {len(texture_files)}"
        
        # Настройки сетки
        enable_grid = getattr(settings, 'enable_grid_layout', True)
        if enable_grid:
            grid_cols = getattr(settings, 'grid_columns', 0)
            if grid_cols == 0:
                grid_cols = max(1, int(math.sqrt(len(model_files))))
            grid_spacing = getattr(settings, 'grid_spacing', 10.0)
            success_msg += f"\nСетка: {grid_cols} колонок, расстояние {grid_spacing}"
        else:
            success_msg += f"\nСетка отключена"
        
        print("=" * 60)
        print("UNIFIED ИМПОРТ ЗАВЕРШЕН")
        print("=" * 60)
        print(success_msg)
        
        hou.ui.displayMessage(success_msg)
        
        if logger:
            logger.log_debug(success_msg)
        
        return geo_node
        
    except Exception as e:
        error_msg = f"Критическая ошибка в unified импорте: {e}"
        print(f"ERROR: {error_msg}")
        if logger:
            logger.log_error(error_msg)
        hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
        return None


# =============== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===============

def validate_import_environment():
    """Проверяет готовность среды для импорта"""
    if not hasattr(hou, 'ui'):
        raise RuntimeError("Скрипт должен запускаться в интерактивном режиме Houdini")
    
    obj_node = hou.node("/obj")
    if not obj_node:
        raise RuntimeError(ERROR_MESSAGES["no_obj_context"])
    
    return obj_node


def get_folder_path_from_user():
    """Получает путь к папке от пользователя"""
    try:
        folder_path = hou.ui.selectFile(
            title="Выберите папку с моделями и текстурами",
            file_type=hou.fileType.Directory
        )
        
        if not folder_path:
            return None
        
        folder_path = os.path.normpath(folder_path.rstrip("/\\"))
        
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            raise ValueError(f"Выбранный путь не является существующей папкой: {folder_path}")
        
        return folder_path
        
    except Exception as e:
        hou.ui.displayMessage(f"Ошибка выбора папки: {e}", severity=hou.severityType.Error)
        return None


def find_model_files_optimized(folder_path, logger=None):
    """Оптимизированный поиск файлов моделей"""
    model_files = []
    
    if not folder_path or not os.path.exists(folder_path):
        return model_files
    
    print(f"Поиск моделей в: {folder_path}")
    
    try:
        # Используем os.scandir для более быстрого поиска
        with os.scandir(folder_path) as entries:
            for entry in entries:
                if entry.is_dir():
                    # Рекурсивно ищем в подпапках
                    subfolder_models = find_model_files_optimized(entry.path, logger)
                    model_files.extend(subfolder_models)
                elif entry.is_file():
                    if any(entry.name.lower().endswith(ext) for ext in SUPPORTED_MODEL_FORMATS):
                        is_valid, normalized_path = validate_file_path(entry.path)
                        if is_valid:
                            model_files.append(normalized_path)
                            if logger:
                                logger.log_model_found(normalized_path)
                        else:
                            print(f"Предупреждение: Пропущен недоступный файл: {entry.path}")
                            
    except Exception as e:
        if logger:
            logger.log_error(f"Ошибка при поиске моделей в {folder_path}: {e}")
        print(f"Ошибка при поиске моделей: {e}")
    
    return model_files
def create_enhanced_material_with_logging_v2(matnet_node, material_name, texture_files, 
                                         texture_keywords, material_type, logger=None):
    """
    УЛУЧШЕННАЯ версия создания MaterialX материала с Karma поддержкой
    """
    
    try:
        if logger:
            logger.log_debug(f"=== СОЗДАНИЕ УЛУЧШЕННОГО МАТЕРИАЛА ===")
            logger.log_debug(f"Материал: '{material_name}' типа '{material_type}'")
        
        # 1. Поиск текстур (остается прежним)
        from material_utils import find_matching_textures
        found_textures = find_matching_textures(
            material_name, texture_files, texture_keywords
        )
        
        if logger:
            logger.log_debug(f"Найдено текстур: {len(found_textures)}")
            for tex_type, tex_path in found_textures.items():
                udim_label = " (UDIM)" if '<UDIM>' in tex_path else ""
                logger.log_debug(f"  {tex_type}: {os.path.basename(tex_path)}{udim_label}")
        
        # 2. НОВОЕ: Определяем оптимальную MaterialX стратегию
        if material_type == "materialx":
            strategy = _determine_materialx_strategy(matnet_node, logger)
            logger.log_debug(f"MaterialX стратегия: {strategy['type']} ({strategy['reason']})")
            
            # Создаем материал согласно стратегии
            created_material = _create_material_by_strategy(
                matnet_node, material_name, found_textures, strategy, logger
            )
        else:
            # Обычные материалы (Principled, Redshift)
            from material_utils import create_principled_shader
            created_material = create_principled_shader(
                matnet_node, material_name, found_textures, material_type, logger
            )
        
        # 3. Логирование результата
        if created_material and logger:
            logger.log_material_created(
                material_name=material_name,
                material_path=created_material.path(),
                textures=found_textures
            )
            
            # Дополнительная информация о MaterialX
            if material_type == "materialx":
                logger.log_debug(f"✓ MaterialX материал создан: {created_material.type().name()}")
                logger.log_debug(f"✓ Путь: {created_material.path()}")
                
                # Анализируем созданную структуру
                _analyze_created_materialx(created_material, logger)
        
        elif logger:
            logger.log_material_failed(material_name, "Не удалось создать материал")
        
        return created_material
        
    except Exception as e:
        if logger:
            logger.log_material_failed(material_name, str(e))
        print(f"ERROR: Ошибка создания улучшенного материала {material_name}: {e}")
        return None



def _determine_materialx_strategy(matnet_node, logger=None):
    """
    Определяет лучшую стратегию MaterialX для текущей системы
    """
    
    def log_debug(msg):
        if logger: logger.log_debug(msg)
        print(f"MaterialX Strategy: {msg}")
    
    # Проверяем доступные типы нод
    available_nodes = []
    node_types = hou.nodeTypeCategories()["Vop"].nodeTypes()
    
    # Список MaterialX нод для проверки
    materialx_nodes = [
        "karmamaterial",
        "mtlxstandardsurface", 
        "usdpreviewsurface",
        "mtlximage",
        "subnet"
    ]
    
    for node_type in materialx_nodes:
        if node_type in node_types:
            available_nodes.append(node_type)
    
    log_debug(f"Доступные MaterialX ноды: {available_nodes}")
    
    # Стратегия выбора (по приоритету)
    if "karmamaterial" in available_nodes or "subnet" in available_nodes:
        log_debug("✓ Выбрана стратегия: Karma Material Subnet")
        return {
            'type': 'karma_material',
            'method': 'subnet_network',
            'reason': 'Karma Material доступен - максимальные возможности',
            'priority': 1
        }
    
    elif "mtlxstandardsurface" in available_nodes:
        log_debug("✓ Выбрана стратегия: MaterialX Standard Surface")
        return {
            'type': 'mtlxstandardsurface',
            'method': 'standard_materialx',
            'reason': 'MaterialX Standard Surface - полный MaterialX стандарт',
            'priority': 2
        }
    
    elif "usdpreviewsurface" in available_nodes:
        log_debug("⚠ Выбрана стратегия: USD Preview Surface (fallback)")
        return {
            'type': 'usdpreviewsurface',
            'method': 'usd_preview',
            'reason': 'USD Preview Surface - базовая совместимость',
            'priority': 3
        }
    
    else:
        log_debug("✗ MaterialX недоступен, fallback на Principled")
        return {
            'type': 'principledshader',
            'method': 'principled_fallback',
            'reason': 'MaterialX недоступен',
            'priority': 4
        }
        
        
def _create_material_by_strategy(matnet_node, material_name, texture_maps, strategy, logger):
    """
    Создает материал согласно выбранной стратегии
    """
    
    if strategy['type'] == 'karma_material':
        return _create_karma_material_subnet(matnet_node, material_name, texture_maps, logger)
    
    elif strategy['type'] == 'mtlxstandardsurface':
        return _create_standard_materialx(matnet_node, material_name, texture_maps, logger)
    
    elif strategy['type'] == 'usdpreviewsurface':
        # Используем исправленную функцию для USD Preview
        return _create_usd_preview_fixed(matnet_node, material_name, texture_maps, logger)
    
    else:
        # Fallback на Principled
        from material_utils import create_principled_shader
        return create_principled_shader(matnet_node, material_name, texture_maps, strategy['type'], logger)


def _create_karma_material_subnet(matnet_node, material_name, texture_maps, logger):
    """
    Создает современный Karma Material как Subnet
    """
    from utils import clean_node_name, generate_unique_name
    
    def log_debug(msg):
        if logger: logger.log_debug(msg)
        print(f"Karma Material: {msg}")
    
    try:
        # 1. Создаем Subnet для Karma Material
        safe_name = clean_node_name(material_name)
        unique_name = generate_unique_name(matnet_node, "subnet", f"{safe_name}_karma")
        
        karma_subnet = matnet_node.createNode("subnet", unique_name)
        karma_subnet.allowEditingOfContents()
        karma_subnet.setComment("Karma Material Network")
        
        log_debug(f"Создан Karma Subnet: {unique_name}")
        
        # 2. Внутренняя структура
        # Surface Shader
        surface_shader = None
        for shader_type in ["mtlxstandardsurface", "principled_bsdf"]:
            try:
                surface_shader = karma_subnet.createNode(shader_type, "surface1")
                log_debug(f"Создан surface: {shader_type}")
                break
            except Exception as e:
                log_debug(f"Не удалось создать {shader_type}: {e}")
        
        if not surface_shader:
            log_debug("Не удалось создать surface shader")
            return None
        
        # 3. Image ноды для текстур
        image_nodes = {}
        for tex_type, tex_path in texture_maps.items():
            try:
                img_name = f"img_{clean_node_name(tex_type.lower())}"
                img_node = karma_subnet.createNode("mtlximage", img_name)
                img_node.parm("file").set(tex_path)
                
                # Настройки для разных типов текстур
                if tex_type == "Normal":
                    if img_node.parm("signature"):
                        img_node.parm("signature").set("vector3")
                elif tex_type in ["Roughness", "Metallic", "AO"]:
                    if img_node.parm("signature"):
                        img_node.parm("signature").set("float")
                
                image_nodes[tex_type] = img_node
                log_debug(f"Создана image: {img_name}")
                
            except Exception as e:
                log_debug(f"Ошибка создания image {tex_type}: {e}")
        
        # 4. Подключения текстур
        _connect_karma_material_textures(surface_shader, image_nodes, log_debug)
        
        # 5. Material Builder (если доступен)
        try:
            mat_builder = karma_subnet.createNode("material_builder", "builder1")
            mat_builder.setInput(0, surface_shader)  # Surface
            
            # Output
            output = karma_subnet.createNode("output", "output1") 
            output.setInput(0, mat_builder)
            
            log_debug("Создан Material Builder + Output")
            
        except Exception as e:
            log_debug(f"Material Builder недоступен: {e}")
            # Простой output
            try:
                output = karma_subnet.createNode("output", "output1")
                output.setInput(0, surface_shader)
                log_debug("Создан простой Output")
            except:
                pass
        
        # 6. Размещение нод
        surface_shader.moveToGoodPosition()
        for img in image_nodes.values():
            img.moveToGoodPosition()
        
        log_debug(f"✓ Karma Material создан: {karma_subnet.path()}")
        return karma_subnet
        
    except Exception as e:
        if logger:
            logger.log_error(f"Ошибка создания Karma Material: {e}")
        return None


def _connect_karma_material_textures(surface_shader, image_nodes, log_debug):
    """
    Подключает текстуры к Karma material surface
    """
    
    shader_type = surface_shader.type().name().lower()
    
    # Карты подключений
    if "mtlxstandardsurface" in shader_type:
        texture_map = {
            "BaseMap": ("base_color", "Base Color"),
            "Normal": ("normal", "Normal"),
            "Roughness": ("specular_roughness", "Specular Roughness"), 
            "Metallic": ("metalness", "Metalness"),
            "AO": ("diffuse_roughness", "Diffuse Roughness"),
            "Emissive": ("emission_color", "Emission Color"),
            "Opacity": ("opacity", "Opacity")
        }
    else:  # principled_bsdf
        texture_map = {
            "BaseMap": ("basecolor", "Base Color"),
            "Normal": ("normal", "Normal"),
            "Roughness": ("roughness", "Roughness"),
            "Metallic": ("metallic", "Metallic"),
            "AO": ("ao", "AO"),
            "Emissive": ("emission", "Emission"),
            "Opacity": ("opacity", "Opacity")
        }
    
    connected = 0
    for tex_type, img_node in image_nodes.items():
        if tex_type in texture_map:
            param_name, input_label = texture_map[tex_type]
            
            try:
                # Поиск входа по label
                input_labels = surface_shader.inputLabels()
                input_index = -1
                
                for i, label in enumerate(input_labels):
                    if label.lower() == input_label.lower():
                        input_index = i
                        break
                
                if input_index >= 0:
                    surface_shader.setInput(input_index, img_node, 0)
                    log_debug(f"✓ {tex_type} -> {input_label}")
                    connected += 1
                else:
                    log_debug(f"✗ Не найден вход для {tex_type}")
                    
            except Exception as e:
                log_debug(f"Ошибка подключения {tex_type}: {e}")
    
    log_debug(f"Подключено {connected}/{len(image_nodes)} текстур")


def _create_usd_preview_fixed(matnet_node, material_name, texture_maps, logger):
    """
    ИСПРАВЛЕННАЯ версия USD Preview Surface с правильными подключениями
    """
    from utils import clean_node_name, generate_unique_name
    from material_utils import create_materialx_shader_improved
    
    # Используем улучшенную функцию
    return create_materialx_shader_improved(matnet_node, material_name, texture_maps, logger)


def _analyze_created_materialx(material_node, logger):
    """
    Анализирует созданный MaterialX материал
    """
    try:
        node_type = material_node.type().name()
        node_path = material_node.path()
        
        logger.log_debug(f"=== АНАЛИЗ MATERIALX МАТЕРИАЛА ===")
        logger.log_debug(f"Тип: {node_type}")
        logger.log_debug(f"Путь: {node_path}")
        
        # Если это subnet, анализируем внутреннюю структуру
        if node_type == "subnet":
            children = material_node.children()
            logger.log_debug(f"Внутренних нод: {len(children)}")
            for child in children:
                logger.log_debug(f"  - {child.name()}: {child.type().name()}")
        
        # Анализируем входы/выходы
        try:
            inputs = material_node.inputLabels()
            outputs = material_node.outputLabels()
            logger.log_debug(f"Входов: {len(inputs)}, Выходов: {len(outputs)}")
        except:
            pass
        
        logger.log_debug("=== КОНЕЦ АНАЛИЗА ===")
        
    except Exception as e:
        logger.log_debug(f"Ошибка анализа MaterialX: {e}")
        

def find_texture_files_optimized(folder_path, logger=None):
    """Оптимизированный поиск текстур с UDIM анализом"""
    texture_files = []
    
    if not folder_path or not os.path.exists(folder_path):
        return texture_files
    
    print(f"Поиск текстур в: {folder_path}")
    
    try:
        # Используем os.scandir для более быстрого поиска
        with os.scandir(folder_path) as entries:
            for entry in entries:
                if entry.is_dir():
                    # Рекурсивно ищем в подпапках
                    subfolder_textures = find_texture_files_optimized(entry.path, logger)
                    texture_files.extend(subfolder_textures)
                elif entry.is_file():
                    if any(entry.name.lower().endswith(ext) for ext in SUPPORTED_TEXTURE_FORMATS):
                        is_valid, normalized_path = validate_file_path(entry.path)
                        if is_valid:
                            texture_files.append(normalized_path)
                        else:
                            print(f"Предупреждение: Пропущен недоступный файл: {entry.path}")
        
        # Анализируем UDIM, если найдены текстуры
        if texture_files and UDIM_AVAILABLE:
            try:
                udim_stats = get_udim_statistics(texture_files)
                if udim_stats['udim_sequences'] > 0:
                    print(f"UDIM АНАЛИЗ: Найдено {udim_stats['udim_sequences']} UDIM последовательностей")
                    print(f"UDIM тайлов: {udim_stats['udim_tiles']}, одиночных текстур: {udim_stats['single_textures']}")
                    
                    if logger:
                        logger.log_info(f"UDIM: {udim_stats['udim_sequences']} последовательностей, {udim_stats['udim_tiles']} тайлов")
                        
                    # Показываем детальную UDIM информацию только если последовательностей немного
                    if udim_stats['udim_sequences'] <= 3:
                        print_udim_info(texture_files)
            except Exception as e:
                print(f"Ошибка UDIM анализа: {e}")
                if logger:
                    logger.log_warning(f"Ошибка UDIM анализа: {e}")
        
        if logger:
            if texture_files:
                logger.log_debug(f"Найдено текстур: {len(texture_files)}")
            else:
                logger.log_warning("Текстуры не найдены")
        
        print(f"Найдено {len(texture_files)} текстур")
        
    except Exception as e:
        if logger:
            logger.log_error(f"Критическая ошибка при поиске текстур: {e}")
        print(f"Ошибка при поиске текстур: {e}")
    
    return texture_files


def create_enhanced_material(matnet_node, material_name, texture_files, texture_keywords, material_type, logger=None):
    """Создает материал с использованием системы материалов"""
    
    try:
        if logger:
            logger.log_debug(f"Создание материала '{material_name}' типа '{material_type}'")
        
        # Поиск текстур
        if MATERIAL_SYSTEM_AVAILABLE:
            found_textures = find_matching_textures(
                material_name, texture_files, texture_keywords
            )
        else:
            # Fallback на простой поиск
            found_textures = {}
            if texture_files:
                found_textures["BaseMap"] = texture_files[0]
        
        if logger:
            logger.log_debug(f"Найдено текстур для '{material_name}': {len(found_textures)}")
            for tex_type, tex_path in found_textures.items():
                udim_label = " (UDIM)" if '<UDIM>' in tex_path else ""
                logger.log_debug(f"  {tex_type}: {os.path.basename(tex_path)}{udim_label}")
        
        # Создание материала
        if MATERIAL_SYSTEM_AVAILABLE:
            created_material = create_material_universal(
                matnet_node, material_name, found_textures, material_type, logger
            )
        else:
            # Fallback - создаем простой материал
            created_material = matnet_node.createNode("material", clean_node_name(material_name))
        
        if created_material and logger:
            logger.log_material_created(
                material_name=material_name,
                material_path=created_material.path(),
                textures=found_textures
            )
            logger.log_debug(f"Создан материал типа: {created_material.type().name()}")
        elif logger:
            logger.log_material_failed(material_name, "Не удалось создать материал")
        
        return created_material
        
    except Exception as e:
        if logger:
            logger.log_material_failed(material_name, str(e))
        print(f"ERROR: Ошибка создания материала {material_name}: {e}")
        return None


def import_models_separate(model_files, texture_files, matnet, folder_path, material_type, settings, logger, cache_manager):
    """Импорт моделей как отдельные геометрии"""
    print(f"Импорт {len(model_files)} моделей как отдельные геометрии...")
    
    # Используем model_processor если доступен
    try:
        from model_processor import process_models_optimized
        
        obj_node = hou.node("/obj")
        models_info = []
        material_cache = {}
        
        process_models_optimized(
            model_files, obj_node, matnet, folder_path, texture_files, 
            ENHANCED_TEXTURE_KEYWORDS, material_cache, models_info, settings, logger
        )
        
        # Размещаем модели в сетке
        if models_info:
            arrange_models_in_grid(models_info)
        
        print(f"Импортировано {len(models_info)} моделей отдельно")
        return True
        
    except ImportError:
        print("model_processor недоступен, используем fallback")
        return _import_models_simple_fallback(model_files, texture_files, matnet, material_type, logger)


def import_models_grouped(model_files, texture_files, matnet, folder_path, material_type, settings, logger, cache_manager):
    """Импорт моделей с группировкой по папкам"""
    print(f"Импорт {len(model_files)} моделей с группировкой...")
    
    # Группируем файлы по папкам
    from collections import defaultdict
    groups = defaultdict(list)
    
    for model_file in model_files:
        folder = os.path.dirname(model_file)
        folder_name = os.path.basename(folder) if folder else "root"
        groups[folder_name].append(model_file)
    
    print(f"Создано {len(groups)} групп")
    
    obj_node = hou.node("/obj")
    
    for group_name, group_files in groups.items():
        if len(group_files) > LIMITS.get("max_models_per_group", 20):
            print(f"Предупреждение: Группа {group_name} содержит {len(group_files)} моделей, что превышает лимит")
        
        try:
            # Создаем subnet для группы
            subnet_name = clean_node_name(group_name)
            subnet = safe_create_node(obj_node, "subnet", f"group_{subnet_name}")
            
            # Импортируем модели в subnet
            for model_file in group_files:
                _import_single_model_to_subnet(model_file, subnet, matnet, texture_files, material_type, logger)
            
            print(f"Группа {group_name}: импортировано {len(group_files)} моделей")
            
        except Exception as e:
            print(f"Ошибка импорта группы {group_name}: {e}")
            if logger:
                logger.log_error(f"Ошибка импорта группы {group_name}: {e}")
            continue
    
    return True


def _import_models_simple_fallback(model_files, texture_files, matnet, material_type, logger):
    """Простой fallback импорт без зависимостей"""
    obj_node = hou.node("/obj")
    
    for i, model_file in enumerate(model_files):
        try:
            model_name = os.path.splitext(os.path.basename(model_file))[0]
            safe_name = clean_node_name(model_name)
            
            # Создаем geo
            geo_name = generate_unique_name(obj_node, "geo", safe_name)
            geo_node = safe_create_node(obj_node, "geo", geo_name)
            
            # Создаем file node
            file_node = geo_node.createNode("file", "file_in")
            file_node.parm("file").set(model_file)
            file_node.setDisplayFlag(True)
            file_node.setRenderFlag(True)
            
            if logger:
                logger.log_model_processed(model_file, geo_node.path())
            
        except Exception as e:
            print(f"Ошибка импорта {model_file}: {e}")
            if logger:
                logger.log_model_failed(model_file, str(e))
    
    return True


def _import_single_model_to_subnet(model_file, subnet, matnet, texture_files, material_type, logger):
    """Импортирует одну модель в subnet"""
    try:
        model_name = os.path.splitext(os.path.basename(model_file))[0]
        safe_name = clean_node_name(model_name)
        
        # Создаем geo в subnet
        geo_node = safe_create_node(subnet, "geo", safe_name)
        
        # Создаем file node
        file_node = geo_node.createNode("file", "file_in")
        file_node.parm("file").set(model_file)
        file_node.setDisplayFlag(True)
        file_node.setRenderFlag(True)
        
        if logger:
            logger.log_model_processed(model_file, geo_node.path())
        
    except Exception as e:
        if logger:
            logger.log_model_failed(model_file, str(e))
        raise
def _create_standard_materialx(matnet_node, material_name, texture_maps, logger):
    """
    Создает MaterialX Standard Surface материал
    """
    from utils import clean_node_name, generate_unique_name
    
    def log_debug(msg):
        if logger: logger.log_debug(msg)
        print(f"MaterialX Standard: {msg}")
    
    def log_error(msg):
        if logger: logger.log_error(msg)
        print(f"ERROR MaterialX Standard: {msg}")
    
    try:
        # 1. Создаем уникальное имя
        safe_name = clean_node_name(material_name)
        unique_name = generate_unique_name(matnet_node, "mtlxstandardsurface", f"{safe_name}_mtlx")
        
        # 2. Создаем MaterialX Standard Surface
        standard_surface = matnet_node.createNode("mtlxstandardsurface", unique_name)
        if not standard_surface:
            log_error("Не удалось создать mtlxstandardsurface")
            return None
        
        log_debug(f"Создан MaterialX Standard Surface: {unique_name}")
        
        # 3. Создаем image ноды для текстур
        image_nodes = {}
        for tex_type, tex_path in texture_maps.items():
            try:
                img_name = f"{safe_name}_{clean_node_name(tex_type.lower())}_img"
                img_node = matnet_node.createNode("mtlximage", img_name)
                img_node.parm("file").set(tex_path)
                
                # Настройки для разных типов текстур
                _configure_materialx_image_node(img_node, tex_type, log_debug)
                
                image_nodes[tex_type] = img_node
                log_debug(f"Создана image нода: {img_name}")
                
            except Exception as e:
                log_debug(f"Ошибка создания image ноды {tex_type}: {e}")
        
        # 4. Подключаем image ноды к Standard Surface
        _connect_standard_materialx_textures(standard_surface, image_nodes, texture_maps, log_debug)
        
        # 5. Создаем material wrapper
        material_wrapper = _create_materialx_wrapper(matnet_node, safe_name, standard_surface, log_debug, log_error)
        
        # 6. Размещаем ноды
        standard_surface.moveToGoodPosition()
        for img_node in image_nodes.values():
            img_node.moveToGoodPosition()
        if material_wrapper:
            material_wrapper.moveToGoodPosition()
        
        log_debug(f"✓ MaterialX Standard Surface создан: {standard_surface.path()}")
        return material_wrapper if material_wrapper else standard_surface
        
    except Exception as e:
        log_error(f"Ошибка создания MaterialX Standard Surface: {e}")
        return None


def _configure_materialx_image_node(img_node, tex_type, log_debug):
    """
    Настраивает MaterialX image ноду в зависимости от типа текстуры
    """
    try:
        # Базовые настройки
        if img_node.parm("filecolorspace"):
            if tex_type == "Normal":
                img_node.parm("filecolorspace").set("Raw")
                if img_node.parm("signature"):
                    img_node.parm("signature").set("vector3")
            elif tex_type in ["Roughness", "Metallic", "AO", "Height", "Opacity"]:
                img_node.parm("filecolorspace").set("Raw")
                if img_node.parm("signature"):
                    img_node.parm("signature").set("float")
            else:  # BaseMap, Emissive
                img_node.parm("filecolorspace").set("sRGB")
                if img_node.parm("signature"):
                    img_node.parm("signature").set("color3")
        
        log_debug(f"Настроена image нода для {tex_type}")
        
    except Exception as e:
        log_debug(f"Ошибка настройки image ноды {tex_type}: {e}")


def _connect_standard_materialx_textures(surface_node, image_nodes, texture_maps, log_debug):
    """
    Подключает image ноды к MaterialX Standard Surface
    """
    
    # Карта подключений для MaterialX Standard Surface
    connection_map = {
        "BaseMap": "base_color",
        "Normal": "normal",
        "Roughness": "specular_roughness",
        "Metallic": "metalness", 
        "AO": "diffuse_roughness",
        "Emissive": "emission_color",
        "Opacity": "opacity",
        "Height": "displacement",
        "Specular": "specular"
    }
    
    connected_count = 0
    
    for tex_type, img_node in image_nodes.items():
        if tex_type in connection_map:
            param_name = connection_map[tex_type]
            
            try:
                # Способ 1: Прямое подключение через параметр
                target_parm = surface_node.parm(param_name)
                if target_parm:
                    source_path = f"{img_node.path()}/out"
                    target_parm.set(source_path)
                    log_debug(f"✓ StandardMX: {tex_type} -> {param_name}")
                    connected_count += 1
                    continue
                
                # Способ 2: Поиск по входам
                input_labels = surface_node.inputLabels()
                input_index = -1
                
                # Поиск подходящего входа
                for i, label in enumerate(input_labels):
                    label_clean = label.lower().replace(' ', '').replace('_', '')
                    param_clean = param_name.lower().replace('_', '')
                    
                    if label_clean == param_clean or param_name.lower() in label.lower():
                        input_index = i
                        break
                
                if input_index >= 0:
                    surface_node.setInput(input_index, img_node, 0)
                    log_debug(f"✓ StandardMX: {tex_type} -> input[{input_index}]")
                    connected_count += 1
                else:
                    log_debug(f"✗ StandardMX: не найден вход для {tex_type}")
                    
            except Exception as e:
                log_debug(f"Ошибка подключения {tex_type}: {e}")
    
    log_debug(f"StandardMX: подключено {connected_count}/{len(image_nodes)} текстур")


def _create_materialx_wrapper(matnet_node, safe_name, surface_node, log_debug, log_error):
    """
    Создает material wrapper для MaterialX surface
    """
    try:
        from utils import generate_unique_name
        
        wrapper_name = generate_unique_name(matnet_node, "material", f"{safe_name}_material")
        
        # Пробуем создать разные типы wrapper'ов
        wrapper_types = ["material", "principledshader", "subnet"]
        material_wrapper = None
        
        for wrapper_type in wrapper_types:
            try:
                material_wrapper = matnet_node.createNode(wrapper_type, wrapper_name)
                if material_wrapper:
                    log_debug(f"Создан MaterialX wrapper типа: {wrapper_type}")
                    break
            except Exception as e:
                log_debug(f"Не удалось создать wrapper {wrapper_type}: {e}")
                continue
        
        if not material_wrapper:
            log_debug("Не удалось создать MaterialX wrapper")
            return None
        
        # Подключаем surface к wrapper
        if surface_node:
            try:
                # Способ 1: Через параметр surface
                if material_wrapper.parm("surface"):
                    material_wrapper.parm("surface").set(surface_node.path())
                    log_debug("Surface подключен через параметр 'surface'")
                    
                # Способ 2: Через shop_surfacepath
                elif material_wrapper.parm("shop_surfacepath"):
                    material_wrapper.parm("shop_surfacepath").set(surface_node.path())
                    log_debug("Surface подключен через 'shop_surfacepath'")
                    
                # Способ 3: Через setInput
                else:
                    input_labels = material_wrapper.inputLabels()
                    if input_labels:
                        # Ищем подходящий вход
                        surface_input_index = -1
                        for i, label in enumerate(input_labels):
                            if "surface" in label.lower():
                                surface_input_index = i
                                break
                        
                        if surface_input_index >= 0:
                            material_wrapper.setInput(surface_input_index, surface_node)
                            log_debug(f"Surface подключен через вход {surface_input_index}")
                        else:
                            # Подключаем к первому входу
                            material_wrapper.setInput(0, surface_node)
                            log_debug("Surface подключен к первому входу")
                
            except Exception as e:
                log_error(f"Ошибка подключения surface к wrapper: {e}")
        
        return material_wrapper
        
    except Exception as e:
        log_error(f"Ошибка создания MaterialX wrapper: {e}")
        return None


def _create_usd_preview_fixed(matnet_node, material_name, texture_maps, logger):
    """
    ИСПРАВЛЕННАЯ версия создания USD Preview Surface материала
    """
    from utils import clean_node_name, generate_unique_name
    
    def log_debug(msg):
        if logger: logger.log_debug(msg)
        print(f"USD Preview: {msg}")
    
    def log_error(msg):
        if logger: logger.log_error(msg)
        print(f"ERROR USD Preview: {msg}")
    
    try:
        # 1. Создаем уникальное имя
        safe_name = clean_node_name(material_name)
        unique_name = generate_unique_name(matnet_node, "usdpreviewsurface", f"{safe_name}_usd")
        
        # 2. Создаем USD Preview Surface
        usd_surface = matnet_node.createNode("usdpreviewsurface", unique_name)
        if not usd_surface:
            log_error("Не удалось создать usdpreviewsurface")
            return None
        
        log_debug(f"Создан USD Preview Surface: {unique_name}")
        
        # 3. Создаем image ноды для текстур
        image_nodes = {}
        for tex_type, tex_path in texture_maps.items():
            try:
                img_name = f"{safe_name}_{clean_node_name(tex_type.lower())}_img"
                img_node = matnet_node.createNode("mtlximage", img_name)
                img_node.parm("file").set(tex_path)
                
                # Настройки для USD Preview
                _configure_materialx_image_node(img_node, tex_type, log_debug)
                
                image_nodes[tex_type] = img_node
                log_debug(f"Создана image нода: {img_name}")
                
            except Exception as e:
                log_debug(f"Ошибка создания image ноды {tex_type}: {e}")
        
        # 4. ИСПРАВЛЕННОЕ подключение к USD Preview Surface
        _connect_usd_preview_textures_fixed(usd_surface, image_nodes, texture_maps, log_debug)
        
        # 5. Создаем material wrapper
        material_wrapper = _create_materialx_wrapper(matnet_node, safe_name, usd_surface, log_debug, log_error)
        
        # 6. Размещаем ноды
        usd_surface.moveToGoodPosition()
        for img_node in image_nodes.values():
            img_node.moveToGoodPosition()
        if material_wrapper:
            material_wrapper.moveToGoodPosition()
        
        log_debug(f"✓ USD Preview Surface создан: {usd_surface.path()}")
        return material_wrapper if material_wrapper else usd_surface
        
    except Exception as e:
        log_error(f"Ошибка создания USD Preview Surface: {e}")
        return None


def _connect_usd_preview_textures_fixed(surface_node, image_nodes, texture_maps, log_debug):
    """
    ИСПРАВЛЕННОЕ подключение текстур к USD Preview Surface
    """
    
    # ИСПРАВЛЕННАЯ карта подключений с правильными именами для USD Preview Surface
    connection_map = {
        "BaseMap": ("Diffuse Color", "diffuseColor"),       # ИСПРАВЛЕНО: правильные имена
        "Normal": ("Normal", "normal"),
        "Roughness": ("Roughness", "roughness"),
        "Metallic": ("Metallic", "metallic"),
        "AO": ("Occlusion", "occlusion"),                   # ИСПРАВЛЕНО: Occlusion, не AO
        "Emissive": ("Emissive Color", "emissiveColor"),
        "Opacity": ("Opacity", "opacity")
    }
    
    connected_count = 0
    
    # Получаем список входов для отладки
    input_labels = surface_node.inputLabels()
    log_debug(f"Доступные входы USD Preview: {input_labels}")
    
    for tex_type, img_node in image_nodes.items():
        if tex_type in connection_map:
            input_label, param_name = connection_map[tex_type]
            
            try:
                # Способ 1: Поиск по точному имени входа
                input_index = -1
                for i, label in enumerate(input_labels):
                    if label == input_label:  # Точное совпадение
                        input_index = i
                        break
                
                if input_index >= 0:
                    surface_node.setInput(input_index, img_node, 0)
                    log_debug(f"✓ USD Preview: {tex_type} -> {input_label} [index {input_index}]")
                    connected_count += 1
                    continue
                
                # Способ 2: Поиск по параметру
                target_parm = surface_node.parm(param_name)
                if target_parm:
                    source_path = f"{img_node.path()}/out"
                    target_parm.set(source_path)
                    log_debug(f"✓ USD Preview: {tex_type} -> {param_name} (parm)")
                    connected_count += 1
                    continue
                
                # Способ 3: Поиск по похожему имени
                for i, label in enumerate(input_labels):
                    if (tex_type.lower() in label.lower() or 
                        input_label.lower() in label.lower()):
                        surface_node.setInput(i, img_node, 0)
                        log_debug(f"✓ USD Preview: {tex_type} -> {label} [fuzzy match, index {i}]")
                        connected_count += 1
                        break
                else:
                    log_debug(f"✗ USD Preview: не найден вход для {tex_type} (искали '{input_label}')")
                    
            except Exception as e:
                log_debug(f"Ошибка подключения {tex_type}: {e}")
    
    log_debug(f"USD Preview: подключено {connected_count}/{len(image_nodes)} текстур")


def _ensure_unique_material_name(matnet_node, base_name):
    """
    Обеспечивает уникальность имени материала (если не импортирована из utils)
    """
    try:
        from utils import generate_unique_name
        return generate_unique_name(matnet_node, "material", base_name)
    except ImportError:
        # Fallback реализация
        counter = 1
        current_name = base_name
        
        while matnet_node.node(current_name) is not None:
            current_name = f"{base_name}_{counter}"
            counter += 1
            if counter > 1000:  # Защита от бесконечного цикла
                import time
                current_name = f"{base_name}_{int(time.time() % 10000)}"
                break
        
        return current_name


# ДОПОЛНИТЕЛЬНО: Функция для отладки MaterialX нод
def debug_materialx_capabilities(matnet_node, logger=None):
    """
    Отладочная функция для проверки доступных MaterialX возможностей
    """
    def log_debug(msg):
        if logger: logger.log_debug(msg)
        print(f"MaterialX Debug: {msg}")
    
    try:
        # Проверяем доступные типы нод
        node_types = hou.nodeTypeCategories()["Vop"].nodeTypes()
        
        materialx_nodes = {
            "Karma Material": ["karmamaterial", "subnet"],
            "MaterialX Standard": ["mtlxstandardsurface"],
            "USD Preview": ["usdpreviewsurface"], 
            "MaterialX Image": ["mtlximage"],
            "Material Builder": ["material_builder"],
            "Wrappers": ["material", "principledshader"]
        }
        
        log_debug("=== ПРОВЕРКА MATERIALX ВОЗМОЖНОСТЕЙ ===")
        
        for category, node_list in materialx_nodes.items():
            available = []
            for node_type in node_list:
                if node_type in node_types:
                    available.append(node_type)
            
            status = "✓" if available else "✗"
            log_debug(f"{status} {category}: {available if available else 'недоступно'}")
        
        # Рекомендация
        if "karmamaterial" in node_types or "subnet" in node_types:
            log_debug("🎯 РЕКОМЕНДАЦИЯ: Используйте Karma Material для максимальных возможностей")
        elif "mtlxstandardsurface" in node_types:
            log_debug("🎯 РЕКОМЕНДАЦИЯ: Используйте MaterialX Standard Surface")
        elif "usdpreviewsurface" in node_types:
            log_debug("⚠️  РЕКОМЕНДАЦИЯ: USD Preview Surface (ограниченные возможности)")
        else:
            log_debug("❌ MaterialX недоступен, используйте Principled Shader")
        
        log_debug("=== КОНЕЦ ПРОВЕРКИ ===")
        
    except Exception as e:
        log_debug(f"Ошибка проверки MaterialX возможностей: {e}")

def generate_unified_python_code(imported_models_info, folder_path, texture_files, 
                                  material_path, material_type, settings, logger):
    """Генерирует Python код для unified импорта"""
    
    # Нормализуем пути
    folder_path_fixed = os.path.normpath(folder_path).replace(os.sep, "/")
    material_path_fixed = os.path.normpath(material_path).replace(os.sep, "/") if material_path else ""
    
    # Настройки сетки
    enable_grid = getattr(settings, 'enable_grid_layout', True)
    grid_spacing = getattr(settings, 'grid_spacing', 10.0)
    grid_columns = getattr(settings, 'grid_columns', 0)
    
    return f'''
import hou
import os
import math

def main():
    print("DEBUG SOP: === UNIFIED ОБРАБОТЧИК ===")
    
    node = hou.pwd()
    geo = node.geometry()
    
    # Данные
    folder_path = "{folder_path_fixed}"
    material_path = "{material_path_fixed}"
    material_type = "{material_type}"
    
    # Настройки сетки
    enable_grid = {enable_grid}
    grid_spacing = {grid_spacing}
    grid_columns = {grid_columns}
    
    print(f"DEBUG SOP: Папка: {{folder_path}}")
    print(f"DEBUG SOP: Материал: {{material_path}}")
    print(f"DEBUG SOP: Тип материала: {{material_type}}")
    print(f"DEBUG SOP: Сетка: включена={{enable_grid}}, колонок={{grid_columns}}, расстояние={{grid_spacing}}")
    print(f"DEBUG SOP: Примитивов: {{len(geo.prims())}}")
    
    # Атрибут материала
    mat_attr = geo.findPrimAttrib("shop_materialpath")
    if not mat_attr:
        geo.addAttrib(hou.attribType.Prim, "shop_materialpath", "")
        mat_attr = geo.findPrimAttrib("shop_materialpath")
    
    # Группируем примитивы по model_index для сетки
    from collections import defaultdict
    model_groups = defaultdict(list)
    for prim in geo.prims():
        try:
            model_index = prim.attribValue("model_index")
            if model_index is not None:
                model_groups[model_index].append(prim)
            else:
                model_groups[0].append(prim)
        except:
            model_groups[0].append(prim)
    
    print(f"DEBUG SOP: Найдено {{len(model_groups)}} групп моделей")
    
    # Применяем материал
    if material_path:
        print(f"DEBUG SOP: === НАЗНАЧЕНИЕ МАТЕРИАЛА ===")
        assigned_count = 0
        for prim in geo.prims():
            try:
                prim.setAttribValue(mat_attr, material_path)
                assigned_count += 1
            except Exception as e:
                print(f"DEBUG SOP: Ошибка назначения материала: {{e}}")
                continue
        
        print(f"DEBUG SOP: ✓ Материал назначен {{assigned_count}} примитивам")
        print(f"DEBUG SOP: ✓ Тип материала: {{material_type}}")
        print(f"DEBUG SOP: ✓ Путь материала: {{material_path}}")
    else:
        print(f"DEBUG SOP: ⚠ Материал не создан, назначение пропущено")
    
    # Применяем сетку
    if enable_grid and len(model_groups) > 1:
        print(f"DEBUG SOP: === ПРИМЕНЕНИЕ СЕТКИ ===")
        print(f"DEBUG SOP: Применяем сетку к {{len(model_groups)}} моделям")
        
        if grid_columns == 0:
            grid_columns = max(1, int(math.sqrt(len(model_groups))))
        
        print(f"DEBUG SOP: Сетка {{grid_columns}} колонок, расстояние {{grid_spacing}}")
        
        # Собираем все точки для каждой модели и вычисляем их параметры
        model_points = {{}}
        model_centers = {{}}
        model_bboxes = {{}}
        global_min_y = float('inf')
        max_bbox_size = 0
        
        for model_index, prims in model_groups.items():
            if not prims:
                continue
                
            # Собираем все уникальные точки модели
            points_set = set()
            for prim in prims:
                for vertex in prim.vertices():
                    points_set.add(vertex.point())
            
            model_points[model_index] = list(points_set)
            
            # Вычисляем bounding box и центр модели
            if model_points[model_index]:
                positions = [p.position() for p in model_points[model_index]]
                
                min_x = min(pos.x() for pos in positions)
                max_x = max(pos.x() for pos in positions)
                min_y = min(pos.y() for pos in positions)
                max_y = max(pos.y() for pos in positions)
                min_z = min(pos.z() for pos in positions)
                max_z = max(pos.z() for pos in positions)
                
                # Размеры bounding box
                bbox_size_x = max_x - min_x
                bbox_size_y = max_y - min_y
                bbox_size_z = max_z - min_z
                
                model_bboxes[model_index] = {{
                    'min': hou.Vector3(min_x, min_y, min_z),
                    'max': hou.Vector3(max_x, max_y, max_z),
                    'size': hou.Vector3(bbox_size_x, bbox_size_y, bbox_size_z)
                }}
                
                # Центр модели
                center_x = (min_x + max_x) / 2
                center_y = (min_y + max_y) / 2
                center_z = (min_z + max_z) / 2
                model_centers[model_index] = hou.Vector3(center_x, center_y, center_z)
                
                # Отслеживаем глобальную минимальную Y и максимальный размер
                global_min_y = min(global_min_y, min_y)
                max_bbox_size = max(max_bbox_size, bbox_size_x, bbox_size_z)
                
                print(f"DEBUG SOP: Модель {{model_index}}: размер {{bbox_size_x:.2f}}x{{bbox_size_y:.2f}}x{{bbox_size_z:.2f}}, центр {{model_centers[model_index]}}")
        
        # Вычисляем адаптивное расстояние сетки
        adaptive_spacing = max(grid_spacing, max_bbox_size * 1.2)  # 20% отступ
        print(f"DEBUG SOP: Адаптивное расстояние сетки: {{adaptive_spacing:.2f}} (макс. размер объекта: {{max_bbox_size:.2f}})")
        
        # Применяем трансформацию
        for model_index, points in model_points.items():
            if not points:
                continue
            
            col = model_index % grid_columns
            row = model_index // grid_columns
            
            # Целевая позиция для центра модели
            target_x = col * adaptive_spacing
            target_z = row * adaptive_spacing
            
            # Выравниваем все объекты по одной поверхности (глобальная минимальная Y)
            current_min_y = model_bboxes[model_index]['min'].y()
            target_y_offset = global_min_y - current_min_y
            
            target_center = hou.Vector3(target_x, model_centers[model_index].y() + target_y_offset, target_z)
            
            # Вычисляем смещение
            offset = target_center - model_centers[model_index]
            
            print(f"DEBUG SOP: Модель {{model_index}} -> позиция ({{target_x:.2f}}, {{target_y_offset:.2f}}, {{target_z:.2f}}), смещение {{offset}}")
            
            # Применяем смещение ко всем точкам модели
            transformed_count = 0
            for point in points:
                try:
                    old_pos = point.position()
                    new_pos = old_pos + offset
                    point.setPosition(new_pos)
                    transformed_count += 1
                except Exception as e:
                    print(f"DEBUG SOP: Ошибка трансформации точки: {{e}}")
                    continue
            
            print(f"DEBUG SOP: Трансформировано {{transformed_count}} точек для модели {{model_index}}")
    else:
        print(f"DEBUG SOP: Сетка отключена или только одна модель")
    
    print(f"DEBUG SOP: === ИТОГОВАЯ СТАТИСТИКА ===")
    print(f"DEBUG SOP: ✓ Обработано примитивов: {{len(geo.prims())}}")
    print(f"DEBUG SOP: ✓ Групп моделей: {{len(model_groups)}}")
    
    if material_path:
        print(f"DEBUG SOP: ✓ Материал: {{material_type}} ({{material_path}})")
    
    if enable_grid:
        print(f"DEBUG SOP: ✓ Сетка: {{grid_columns}}x{{math.ceil(len(model_groups)/grid_columns)}}")

print("DEBUG SOP: Запуск unified обработчика")
main()
print("DEBUG SOP: Unified обработчик завершен")
'''


# =============== ОБЕРТКИ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ ===============

def create_multi_material_models(merge_models=False, settings=None, logger=None, cache_manager=None):
    """Обертка для обратной совместимости"""
    return create_multi_material_models_optimized(merge_models, settings, logger, cache_manager)


def create_unified_model_import_optimized(settings=None, logger=None, cache_manager=None):
    """Обертка для обратной совместимости"""
    return create_unified_model_import_enhanced(settings, logger, cache_manager)


def create_unified_model_import(settings=None, logger=None, cache_manager=None):
    """Обертка для обратной совместимости"""
    return create_unified_model_import_enhanced(settings, logger, cache_manager)


def create_unified_model_import_with_grid_support_fixed(settings=None, logger=None, cache_manager=None):
    """Обертка для обратной совместимости"""
    return create_unified_model_import_enhanced(settings, logger, cache_manager)