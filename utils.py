"""
Вспомогательные функции для импорта моделей - исправленная версия
"""
import hou
import os
import re


def clean_node_name(name):
    """Очищает имя узла от недопустимых символов и ограничивает длину"""
    if not name:
        return "default_node"
    
    # Конвертируем в строку на всякий случай
    name = str(name).strip()
    
    # Если пустая строка после strip
    if not name:
        return "default_node"
    
    # Транслитерация кириллицы или полная замена
    # Заменяем все символы, которые не являются ASCII буквами, цифрами или подчеркиванием
    cleaned_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    # Убедимся, что имя не начинается с цифры
    if cleaned_name and cleaned_name[0].isdigit():
        cleaned_name = 'n_' + cleaned_name
    
    # Ограничиваем длину имени
    if len(cleaned_name) > 30:
        cleaned_name = cleaned_name[:30]
    
    # Удаляем дублированные подчеркивания
    while '__' in cleaned_name:
        cleaned_name = cleaned_name.replace('__', '_')
    
    # Удаляем подчеркивания в начале и конце
    cleaned_name = cleaned_name.strip('_')
    
    # Проверяем, что имя не пустое и достаточно длинное
    if not cleaned_name or len(cleaned_name) < 2:
        cleaned_name = "default_node"
    
    # Убедимся, что имя не состоит только из цифр после очистки
    if cleaned_name.isdigit():
        cleaned_name = f"node_{cleaned_name}"
    
    return cleaned_name


def generate_unique_name(parent_node, node_type, base_name):
    """
    Генерирует гарантированно уникальное имя для узла.
    
    Args:
        parent_node: Родительский узел, в котором будет создан новый узел
        node_type: Тип создаваемого узла
        base_name: Базовое имя, которое нужно сделать уникальным
    
    Returns:
        str: Уникальное имя для узла
    """
    # Проверяем входные параметры
    if not parent_node:
        raise ValueError("parent_node не может быть None")
    
    if not base_name:
        base_name = node_type or "node"
    
    # Сначала применяем базовую очистку имени
    safe_name = clean_node_name(base_name)
    
    # Если имя пустое или состоит только из цифр, добавим префикс
    if not safe_name or safe_name.isdigit():
        safe_name = f"{node_type}_{safe_name}" if safe_name else (node_type or "node")
    
    # Если имя слишком длинное, обрезаем его (оставляем место для суффикса)
    if len(safe_name) > 25:
        safe_name = safe_name[:25]
    
    # Проверяем, существует ли такой узел уже
    try:
        if parent_node.node(safe_name) is None:
            # Если узла с таким именем нет, это имя уникально
            return safe_name
    except Exception:
        # Если не можем проверить существование узла, продолжаем с добавлением суффикса
        pass
    
    # Если узел с таким именем существует, добавляем числовой суффикс
    counter = 1
    max_attempts = 1000  # Защита от бесконечного цикла
    
    while counter <= max_attempts:
        unique_name = f"{safe_name}_{counter}"
        try:
            if parent_node.node(unique_name) is None:
                # Нашли уникальное имя
                return unique_name
        except Exception:
            # Если не можем проверить, используем это имя
            return unique_name
        counter += 1
    
    # Если не смогли найти уникальное имя за разумное время, используем временную метку
    import time
    timestamp_suffix = str(int(time.time() * 1000))[-6:]  # Последние 6 цифр timestamp
    return f"{safe_name}_{timestamp_suffix}"


def get_node_bbox(node):
    """Получает bounding box ноды с улучшенной обработкой ошибок"""
    default_bbox = {
        "min": (0, 0, 0),
        "max": (1, 1, 1),
        "size": (1, 1, 1),
        "center": (0.5, 0.5, 0.5)
    }
    
    if not node:
        print("Предупреждение: Передан None узел в get_node_bbox")
        return default_bbox
    
    try:
        geo = node.geometry()
        if not geo:
            print(f"Предупреждение: Узел {node.path()} не содержит геометрии")
            return default_bbox
        
        bbox = geo.boundingBox()
        if not bbox:
            print(f"Предупреждение: Не удалось получить bounding box для узла {node.path()}")
            return default_bbox
        
        # Проверяем, что bounding box валидный
        try:
            min_pt = bbox.minvec()
            max_pt = bbox.maxvec()
            
            # Проверяем на NaN или бесконечные значения
            if (any(not _is_finite_number(coord) for coord in min_pt) or 
                any(not _is_finite_number(coord) for coord in max_pt)):
                print(f"Предупреждение: Некорректные координаты bounding box для узла {node.path()}")
                return default_bbox
            
            size = max_pt - min_pt
            center = bbox.center()
            
            return {
                "min": (min_pt[0], min_pt[1], min_pt[2]),
                "max": (max_pt[0], max_pt[1], max_pt[2]),
                "size": (size[0], size[1], size[2]),
                "center": (center[0], center[1], center[2])
            }
            
        except Exception as e:
            print(f"Ошибка при обработке bounding box для узла {node.path()}: {e}")
            return default_bbox
            
    except Exception as e:
        print(f"Ошибка при получении bounding box для узла {getattr(node, 'path', lambda: 'unknown')()}: {e}")
        return default_bbox


def _is_finite_number(value):
    """Проверяет, является ли значение конечным числом (не NaN и не infinity)"""
    try:
        import math
        return math.isfinite(float(value))
    except (ValueError, TypeError, OverflowError):
        return False


def arrange_models_in_grid(models_info):
    """Размещает модели в сетке с учетом их bounding box"""
    if not models_info:
        print("Нет моделей для расстановки")
        return
    
    try:
        # Фильтруем модели с валидными bounding box
        valid_models = []
        for model in models_info:
            if (model and isinstance(model, dict) and 
                "bbox" in model and "node" in model and 
                model["node"] is not None):
                valid_models.append(model)
        
        if not valid_models:
            print("Нет валидных моделей для расстановки")
            return
        
        # Определяем максимальный размер по X и Z для расстановки по сетке
        try:
            max_x_size = max(model["bbox"]["size"][0] for model in valid_models if model["bbox"]["size"][0] > 0)
            max_z_size = max(model["bbox"]["size"][2] for model in valid_models if model["bbox"]["size"][2] > 0)
        except (ValueError, IndexError, KeyError):
            # Fallback значения, если не можем вычислить размеры
            max_x_size = 10.0
            max_z_size = 10.0
        
        # Добавляем небольшой отступ между моделями
        spacing_x = max_x_size * 1.2
        spacing_z = max_z_size * 1.2
        
        # Определяем количество колонок в сетке (примерно квадратное расположение)
        num_cols = max(1, int(1.5 * (len(valid_models) ** 0.5)))
        
        # Размещаем модели
        for i, model_info in enumerate(valid_models):
            try:
                node = model_info["node"]
                if not node:
                    continue
                
                # Вычисляем позицию в сетке
                col = i % num_cols
                row = i // num_cols
                
                # Устанавливаем позицию ноды
                x_pos = col * spacing_x
                z_pos = row * spacing_z
                
                # Получаем параметр трансформации
                xform = node.parmTuple("t")
                if xform:
                    xform.set((x_pos, 0, z_pos))
                    print(f"Модель {node.name()} размещена в позиции ({x_pos:.1f}, 0, {z_pos:.1f})")
                else:
                    print(f"Предупреждение: Не найден параметр трансформации для узла {node.name()}")
                    
            except Exception as e:
                print(f"Ошибка при размещении модели {i}: {e}")
                continue
                
    except Exception as e:
        print(f"Ошибка при расстановке моделей: {e}")


def safe_create_node(parent_node, node_type, node_name, allow_edit=True):
    """Безопасное создание узла с обработкой ошибок"""
    if not parent_node:
        raise ValueError("parent_node не может быть None")
    
    if not node_type:
        raise ValueError("node_type не может быть пустым")
    
    # Очищаем и проверяем имя узла
    safe_name = clean_node_name(node_name) if node_name else node_type
    unique_name = generate_unique_name(parent_node, node_type, safe_name)
    
    try:
        # Создаем узел
        new_node = parent_node.createNode(node_type, unique_name)
        
        if new_node and allow_edit:
            try:
                new_node.allowEditingOfContents()
            except AttributeError:
                # Не все типы узлов поддерживают allowEditingOfContents
                pass
            except Exception as e:
                print(f"Предупреждение: Не удалось разрешить редактирование содержимого для узла {unique_name}: {e}")
        
        return new_node
        
    except hou.OperationFailed as e:
        print(f"Ошибка создания узла {node_type} с именем {unique_name}: {e}")
        raise
    except Exception as e:
        print(f"Неожиданная ошибка при создании узла {node_type}: {e}")
        raise


def validate_file_path(file_path):
    """Проверяет существование и доступность файла"""
    if not file_path:
        return False, "Путь к файлу пустой"
    
    try:
        # Нормализуем путь
        normalized_path = os.path.normpath(file_path)
        
        # Проверяем существование
        if not os.path.exists(normalized_path):
            return False, f"Файл не существует: {normalized_path}"
        
        # Проверяем, что это файл, а не директория
        if not os.path.isfile(normalized_path):
            return False, f"Путь указывает на директорию, а не на файл: {normalized_path}"
        
        # Проверяем доступность для чтения
        if not os.access(normalized_path, os.R_OK):
            return False, f"Файл недоступен для чтения: {normalized_path}"
        
        return True, normalized_path
        
    except Exception as e:
        return False, f"Ошибка при проверке файла {file_path}: {e}"


def get_supported_model_extensions():
    """Возвращает список поддерживаемых расширений моделей"""
    return ['.fbx', '.obj', '.abc', '.bgeo', '.bgeo.sc', '.ply']


def get_supported_texture_extensions():
    """Возвращает список поддерживаемых расширений текстур"""
    return ['.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff', '.exr', '.hdr', '.pic', '.rat']


def find_files_by_extensions(directory, extensions, recursive=True):
    """Находит файлы с указанными расширениями в директории"""
    if not directory or not os.path.exists(directory):
        return []
    
    found_files = []
    extensions_lower = [ext.lower() for ext in extensions]
    
    try:
        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in extensions_lower):
                        file_path = os.path.join(root, file)
                        found_files.append(os.path.normpath(file_path))
        else:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if (os.path.isfile(file_path) and 
                    any(file.lower().endswith(ext) for ext in extensions_lower)):
                    found_files.append(os.path.normpath(file_path))
                    
    except Exception as e:
        print(f"Ошибка при поиске файлов в {directory}: {e}")
    
    return found_files