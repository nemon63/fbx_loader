from cache_manager import find_matching_textures
from material_utils import create_principled_shader

def main():
    node = hou.pwd()
    geo = node.geometry()
    
    # Получаем переданные данные
    model_file = "''' + model_file_fixed + '''"
    folder_path = "''' + folder_path_fixed + '''"
    model_basename = ''' + model_basename_str + '''
    
    # Данные для текстур и материалов - загружаем напрямую
    texture_files = ''' + texture_files_str + '''
    texture_keywords = ''' + texture_keywords_str + '''
    material_cache = ''' + material_cache_str + '''
    
    matnet_path = "''' + matnet_path_fixed + '''"
    matnet_node = hou.node(matnet_path)
    if not matnet_node:
        print("Не удалось найти matnet!")
        return
    
    print(f"Обработка модели: {model_basename}")
    print(f"Путь к материалам: {matnet_path}")
    
    # Проверяем наличие атрибута shop_materialpath или другого атрибута материала
    mat_attr = None
    for attr_name in ["shop_materialpath", "material", "mat", "materialpath"]:
        mat_attr = geo.findPrimAttrib(attr_name)
        if mat_attr:
            print(f"Найден атрибут материала: {attr_name}")
            break
    
    if not mat_attr:
        print("Атрибут материала не найден в модели. Создаем новый атрибут.")
        geo.addAttrib(hou.attribType.Prim, "shop_materialpath", "")
        mat_attr = geo.findPrimAttrib("shop_materialpath")
    
    # Собираем все уникальные материалы
    material_values = set()
    for prim in geo.prims():
        val = prim.attribValue(mat_attr)
        if isinstance(val, str) and val:
            material_values.add(val)
    
    print(f"Найдено {len(material_values)} уникальных материалов")
    
    # Если в модели нет материалов, создадим один материал по умолчанию
    if not material_values:
        print("В модели нет материалов. Создаем материал по умолчанию.")
        default_mat_name = os.path.splitext(model_basename)[0]
        material_values.add(default_mat_name)
    
    # Словарь для соответствия старых и новых путей материалов
    material_mapping = {}
    
    # Создаём материалы для каждого уникального значения
    for mat_path in material_values:
        # Извлекаем имя материала из пути
        if "/" in mat_path:
            mat_name = os.path.basename(mat_path)
        else:
            mat_name = mat_path
        
        print(f"Обработка материала: {mat_name}")
        
        # Используем имя модели как префикс для имени материала для уникальности
        model_prefix = os.path.splitext(model_basename)[0]
        unique_mat_name = f"{model_prefix}_{mat_name}"
        unique_mat_name = clean_node_name(unique_mat_name)
        
        # Проверяем, создавали ли мы уже этот материал
        if mat_name in material_cache:
            # Используем существующий материал
            material_mapping[mat_path] = material_cache[mat_name]
            print(f"Используем существующий материал: {material_cache[mat_name]}")
            continue
        
        # Ищем текстуры для этого материала
        found_textures = find_matching_textures(mat_name, texture_files, texture_keywords, model_basename)
        
        # Создаём и настраиваем Principled Shader
        material = create_principled_shader(matnet_node, unique_mat_name, found_textures)
        
        # Запоминаем путь к новому материалу
        material_mapping[mat_path] = material.path()
        material_cache[mat_name] = material.path()
        
        print(f"Создан материал: {material.path()}")
    
    # Обновляем кэш материалов в JSON
    try:
        # Используя ваш подход - нормализуем путь и заменяем разделители
        cache_dir = os.path.dirname(model_file)
        cache_path = os.path.join(cache_dir, "material_cache.json")
        # Нормализуем путь
        cache_path = os.path.normpath(cache_path)
        # Заменяем системный разделитель на "/"
        cache_path = cache_path.replace(os.sep, "/")
        with open(cache_path, "w") as f:
            json.dump(material_cache, f, indent=4)
        print(f"Кэш материалов сохранен в: {cache_path}")
    except Exception as e:
        # Игнорируем ошибки при записи кэша
        print(f"Не удалось сохранить кэш материалов: {e}")
    
    # Если у нас нет никаких материалов в матнете, добавим хотя бы один
    if not material_mapping:
        default_mat_name = clean_node_name(f"{model_prefix}_default")
        default_textures = {}
        for texture_file in texture_files:
            texture_basename = os.path.basename(texture_file).lower()
            for texture_type, keywords in texture_keywords.items():
                if texture_type not in default_textures:
                    for keyword in keywords:
                        if keyword in texture_basename:
                            default_textures[texture_type] = texture_file
                            break
        default_material = create_principled_shader(matnet_node, default_mat_name, default_textures)
        material_mapping["default"] = default_material.path()
        print(f"Создан материал по умолчанию: {default_material.path()}")
    
    # Переназначаем пути к материалам для всех примитивов
    if material_mapping:
        default_material_path = list(material_mapping.values())[0]  # Берем первый материал как дефолтный
        for prim in geo.prims():
            old_mat_path = prim.attribValue(mat_attr)
            if old_mat_path in material_mapping:
                prim.setAttribValue(mat_attr, material_mapping[old_mat_path])
            else:
                # Если материал не найден, используем дефолтный
                prim.setAttribValue(mat_attr, default_material_path)
    
    print(f"Обработано {len(material_mapping)} материалов для модели {model_basename}.")# Скрипт для полки Houdini (FBX_LOADER)
import hou
import os
import json
import re

# Основная функция для импорта моделей с материалами
def create_multi_material_models():
    """
    Улучшенный скрипт для импорта моделей с автоматическим назначением материалов.
    
    Функциональность:
    1) Выбор папки с моделями (FBX/OBJ/ABC) и текстурами
    2) Автоматический поиск моделей и текстур в указанной папке
    3) Создание отдельных геометрий для каждой модели
    4) Создание matnet для всех материалов
    5) Автоматическое распознавание и назначение текстур для каждого материала
    6) Расстановка моделей по сетке с учетом их bounding box
    """

    # --- Шаг A: Выбрать папку ---
    folder_path = hou.ui.selectFile(
        title="Выберите папку с моделями и текстурами",
        file_type=hou.fileType.Directory
    )
    
    if not folder_path:
        hou.ui.displayMessage("Папка не выбрана.", severity=hou.severityType.Error)
        return
    
    # Нормализуем путь к папке (убираем косую черту в конце)
    folder_path = folder_path.rstrip("/\\")
    
    # --- Шаг B: Найти все модели (FBX/OBJ/ABC) ---
    model_files = []
    for root, dirs, files in os.walk(folder_path):
        for fname in files:
            if fname.lower().endswith(('.fbx', '.obj', '.abc')):
                model_files.append(os.path.join(root, fname))
    
    if not model_files:
        hou.ui.displayMessage("Модели (.fbx / .obj / .abc) не найдены.", severity=hou.severityType.Error)
        return

    # --- Шаг C: Создаём главный Subnet в /obj ---
    obj_node = hou.node("/obj")
    if not obj_node:
        hou.ui.displayMessage("Контекст /obj не найден!", severity=hou.severityType.Error)
        return
    
    # Создаем безопасное имя для главной подсети
    main_subnet_name = os.path.basename(folder_path)
    main_subnet_name = generate_unique_name(obj_node, "subnet", main_subnet_name)
    
    # Создаем главную подсеть
    try:
        main_subnet = obj_node.createNode("subnet", main_subnet_name)
        main_subnet.allowEditingOfContents()
    except hou.OperationFailed as e:
        hou.ui.displayMessage(f"Ошибка создания подсети: {e}", severity=hou.severityType.Error)
        return
    
    # --- Шаг D: Создаём общий matnet для всех материалов ---
    try:
        matnet = main_subnet.createNode("matnet", "materials")
        matnet.allowEditingOfContents()
    except hou.OperationFailed as e:
        hou.ui.displayMessage(f"Ошибка создания matnet: {e}", severity=hou.severityType.Error)
        return
    
    # --- Шаг E: Словарь для поиска текстур по ключевым словам ---
    texture_keywords = {
        "BaseMap": ["basemap", "diff", "dif", "albedo", "basecolor", "col", "color", "base", "alb", "bc", "diffuse", "color", "_d", "-d", "_c", "-c"],
        "Normal": ["normal", "norm", "nml", "nrm", "_n", "-n", "nor"],
        "Roughness": ["rough", "roughness", "gloss", "glossmap", "glossiness", "_r", "-r", "rgh"],
        "Metallic": ["metal", "metallic", "metalness", "_m", "-m"],
        "AO": ["ao", "ambient", "occlusion", "ambientocclusion", "_ao", "-ao"],
        "Emissive": ["emissive", "emission", "emit", "glow", "_e", "-e"]
    }
    
    # --- Шаг F: Найти все текстуры в папке и подпапках ---
    texture_files = []
    texture_dirs = [folder_path]  # Начинаем с основной папки
    
    # Поиск папок с текстурами (любая папка, содержащая "text" в названии)
    for root, dirs, files in os.walk(folder_path):
        for dirname in dirs:
            if "text" in dirname.lower():
                texture_dirs.append(os.path.join(root, dirname))
        # Также добавляем все подпапки первого уровня
        if root == folder_path:
            for dirname in dirs:
                if os.path.join(root, dirname) not in texture_dirs:
                    texture_dirs.append(os.path.join(root, dirname))
    
    # Собираем все файлы изображений из обнаруженных папок
    image_extensions = ['.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff', '.exr', '.hdr']
    for texture_dir in texture_dirs:
        for root, dirs, files in os.walk(texture_dir):
            for fname in files:
                if any(fname.lower().endswith(ext) for ext in image_extensions):
                    texture_files.append(os.path.join(root, fname))
    
    print(f"Найдено текстур: {len(texture_files)}")
    for texture in texture_files[:10]:  # Выводим первые 10 текстур для отладки
        print(f"- {texture}")
    if len(texture_files) > 10:
        print(f"... и еще {len(texture_files) - 10} текстур")
    
    # --- Шаг G: Обработка каждой модели ---
    models_info = []  # Для хранения информации о bounding box каждой модели
    material_cache = {}  # Кэш уже созданных материалов для переиспользования
    
    # Группируем модели по папкам для создания подсетей
    model_groups = {}
    for model_file in model_files:
        # Получаем относительный путь от основной папки
        rel_path = os.path.relpath(os.path.dirname(model_file), folder_path)
        if rel_path == '.':
            group_name = 'main'  # Для файлов в корне
        else:
            group_name = rel_path.replace(os.sep, '_')
        
        if group_name not in model_groups:
            model_groups[group_name] = []
        
        model_groups[group_name].append(model_file)
    
    # Создаем подсети для каждой группы моделей
    for group_name, group_models in model_groups.items():
        print(f"\nОбработка группы: {group_name} ({len(group_models)} моделей)")
        
        # Если в группе больше 20 моделей, разбиваем на подгруппы
        if len(group_models) > 20:
            # Создаем основную подсеть для этой группы
            group_subnet_name = generate_unique_name(main_subnet, "subnet", group_name)
            
            try:
                group_subnet = main_subnet.createNode("subnet", group_subnet_name)
                group_subnet.allowEditingOfContents()
            except hou.OperationFailed as e:
                print(f"Ошибка создания подсети для группы {group_name}: {e}")
                # Используем основную подсеть вместо недоступной подсети группы
                group_subnet = main_subnet
            
            # Разбиваем модели на подгруппы по 20 моделей
            subgroups = [group_models[i:i + 20] for i in range(0, len(group_models), 20)]
            
            for subgroup_idx, subgroup_models in enumerate(subgroups):
                subgroup_name = f"{group_name}_batch_{subgroup_idx+1}"
                subgroup_name = generate_unique_name(group_subnet, "subnet", subgroup_name)
                
                print(f"  Создание подгруппы: {subgroup_name} ({len(subgroup_models)} моделей)")
                
                try:
                    # Создаем подсеть для подгруппы
                    subgroup_subnet = group_subnet.createNode("subnet", subgroup_name)
                    subgroup_subnet.allowEditingOfContents()
                    
                    # Обрабатываем модели в подгруппе
                    process_models(subgroup_models, subgroup_subnet, matnet, folder_path, 
                                  texture_files, texture_keywords, material_cache, models_info)
                    
                    # Перемещаем подсеть в хорошее положение
                    subgroup_subnet.moveToGoodPosition()
                except hou.OperationFailed as e:
                    print(f"Ошибка создания подсети для подгруппы {subgroup_name}: {e}")
                    # Если не можем создать подсеть для подгруппы, используем родительскую подсеть
                    process_models(subgroup_models, group_subnet, matnet, folder_path, 
                                  texture_files, texture_keywords, material_cache, models_info)
            
            # Перемещаем основную подсеть группы в хорошее положение
            group_subnet.moveToGoodPosition()
        else:
            # Создаем подсеть для группы, если это не главная группа
            if group_name == 'main':
                subnet = main_subnet  # Используем основную подсеть для моделей в корне
            else:
                # Очищаем имя группы от недопустимых символов
                safe_group_name = generate_unique_name(main_subnet, "subnet", group_name)
                
                try:
                    subnet = main_subnet.createNode("subnet", safe_group_name)
                    subnet.allowEditingOfContents()
                except hou.OperationFailed as e:
                    print(f"Ошибка создания подсети для группы {group_name}: {e}")
                    # Используем основную подсеть вместо недоступной подсети группы
                    subnet = main_subnet
            
            # Обрабатываем модели в группе
            process_models(group_models, subnet, matnet, folder_path, 
                          texture_files, texture_keywords, material_cache, models_info)
            
            # Если это подсеть, перемещаем её в хорошее положение
            if group_name != 'main':
                subnet.moveToGoodPosition()
    
    # --- Шаг H: Расстановка моделей по сетке ---
    if len(models_info) > 1:
        arrange_models_in_grid(models_info)
    
    # Разложим основные ноды
    matnet.moveToGoodPosition()
    main_subnet.moveToGoodPosition()
    
    hou.ui.displayMessage(f"Импортировано {len(model_files)} моделей и назначены материалы!")
    return main_subnet


def process_models(models, parent_node, matnet, folder_path, texture_files, texture_keywords, material_cache, models_info):
    """Обрабатывает список моделей и создает для них геометрию"""
    for model_idx, model_file in enumerate(models):
        # Имя ноды берём из названия файла модели
        model_basename = os.path.basename(model_file)
        model_name = os.path.splitext(model_basename)[0]
        
        # Создаем уникальное имя для геометрии
        node_name = f"model_{model_idx:02d}_{model_name}"
        node_name = generate_unique_name(parent_node, "geo", node_name)
        
        print(f"  Обработка модели: {model_name} -> {node_name}")
        
        try:
            # Создаём geo для модели
            geo_node = parent_node.createNode("geo", node_name)
            geo_node.allowEditingOfContents()
            
            # Создаём ноду File для импорта
            file_node = geo_node.createNode("file", "file_in")
            file_node.parm("file").set(model_file)
            
            # Создаём Python SOP для назначения материалов
            python_node = geo_node.createNode("python", "assign_materials")
            python_node.setInput(0, file_node)
            
            # Код для Python SOP
            try:
                python_code = generate_python_sop_code(model_file, folder_path, texture_files, 
                                                matnet.path(), texture_keywords, material_cache)
                python_node.parm("python").set(python_code)
            except Exception as e:
                print(f"Ошибка генерации кода Python для {model_name}: {e}")
                continue
            
            # Для последующей расстановки моделей нам нужна информация о bounding box
            file_node.setDisplayFlag(True)
            file_node.setRenderFlag(True)
            
            # Применяем Python SOP
            python_node.setDisplayFlag(True)
            python_node.setRenderFlag(True)
            
            # Разложим ноды внутри geo
            file_node.moveToGoodPosition()
            python_node.moveToGoodPosition()
            
            # Добавляем null для чистоты
            null_node = geo_node.createNode("null", "OUT")
            null_node.setInput(0, python_node)
            null_node.setDisplayFlag(True)
            null_node.setRenderFlag(True)
            null_node.moveToGoodPosition()
            
            # Для последующей расстановки собираем bounding box
            bbox = get_node_bbox(null_node)
            models_info.append({
                "node": geo_node,
                "bbox": bbox
            })
        except hou.OperationFailed as e:
            print(f"Ошибка создания геометрии для модели {model_name}: {e}")
            continue


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
    # Сначала применяем базовую очистку имени
    safe_name = clean_node_name(base_name)
    
    # Если имя слишком длинное, обрезаем его
    if len(safe_name) > 30:
        safe_name = safe_name[:30]
    
    # Проверяем, существует ли такой узел уже
    if parent_node.node(safe_name) is None:
        # Если узла с таким именем нет, это имя уникально
        return safe_name
    
    # Если узел с таким именем существует, добавляем числовой суффикс
    counter = 1
    while True:
        unique_name = f"{safe_name}_{counter}"
        if parent_node.node(unique_name) is None:
            # Нашли уникальное имя
            return unique_name
        counter += 1


def clean_node_name(name):
    """Очищает имя узла от недопустимых символов и ограничивает длину"""
    if not name:
        return "node"
    
    # Конвертируем в строку на всякий случай
    name = str(name)
    
    # Удалить все символы, кроме букв, цифр и подчеркивания
    import re
    cleaned_name = re.sub(r'[^\w]', '_', name)
    
    # Убедимся, что имя не начинается с цифры
    if cleaned_name and cleaned_name[0].isdigit():
        cleaned_name = 'n_' + cleaned_name
    
    # Ограничиваем длину имени (Houdini может иметь ограничения на длину имен)
    if len(cleaned_name) > 50:
        cleaned_name = cleaned_name[:50]
    
    # Удалить любые дублированные подчеркивания
    while '__' in cleaned_name:
        cleaned_name = cleaned_name.replace('__', '_')
    
    # Удалить подчеркивания в начале и конце
    cleaned_name = cleaned_name.strip('_')
    
    # Финальная проверка, если имя оказалось пустым
    if not cleaned_name:
        cleaned_name = "node"
    
    return cleaned_name


def generate_python_sop_code(model_file, folder_path, texture_files, matnet_path, texture_keywords, material_cache):
    """Генерирует Python-код для SOP, который назначает материалы"""
    
    # Исправляем пути - используем нормализацию путей
    model_file_fixed = os.path.normpath(model_file).replace(os.sep, "/")
    folder_path_fixed = os.path.normpath(folder_path).replace(os.sep, "/")
    matnet_path_fixed = os.path.normpath(matnet_path).replace(os.sep, "/")
    model_basename = os.path.basename(model_file)
    
    # Исправляем пути в списке текстур
    texture_files_fixed = [os.path.normpath(path).replace(os.sep, "/") for path in texture_files]
    
    # Преобразуем данные в строки
    texture_files_str = repr(texture_files_fixed)
    texture_keywords_str = repr(texture_keywords)
    material_cache_str = repr(material_cache)
    model_basename_str = repr(model_basename)
    
    # Формируем код Python SOP
    python_code = '''
import hou
import os
import json
import re

def clean_node_name(name):
    """Очищает имя узла от недопустимых символов и ограничивает длину"""
    if not name:
        return "node"
    
    # Конвертируем в строку на всякий случай
    name = str(name)
    
    # Удалить все символы, кроме букв, цифр и подчеркивания
    cleaned_name = re.sub(r'[^\w]', '_', name)
    
    # Убедимся, что имя не начинается с цифры
    if cleaned_name and cleaned_name[0].isdigit():
        cleaned_name = 'n_' + cleaned_name
    
    # Ограничиваем длину имени (Houdini может иметь ограничения на длину имен)
    if len(cleaned_name) > 50:
        cleaned_name = cleaned_name[:50]
    
    # Удалить любые дублированные подчеркивания
    while '__' in cleaned_name:
        cleaned_name = cleaned_name.replace('__', '_')
    
    # Удалить подчеркивания в начале и конце
    cleaned_name = cleaned_name.strip('_')
    
    # Финальная проверка, если имя оказалось пустым
    if not cleaned_name:
        cleaned_name = "node"
    
    return cleaned_name

def find_matching_textures(material_name, texture_files, texture_keywords, model_basename):
    """Находит текстуры, соответствующие данному материалу"""
    found_textures = {}
    material_name_lower = material_name.lower().replace(" ", "_")
    model_name_lower = os.path.splitext(model_basename)[0].lower()
    
    print(f"Ищем текстуры для материала: {material_name_lower}")
    print(f"Имя модели: {model_name_lower}")
    
    # Метод 1: Прямое совпадение - текстура содержит имя материала
    for texture_file in texture_files:
        texture_basename = os.path.basename(texture_file).lower()
        
        # Проверяем, содержит ли название текстуры имя материала
        if material_name_lower in texture_basename:
            for texture_type, keywords in texture_keywords.items():
                if texture_type not in found_textures:
                    for keyword in keywords:
                        if keyword in texture_basename:
                            found_textures[texture_type] = texture_file
                            print(f"Найдена текстура (метод 1): {texture_type} = {texture_basename}")
                            break
    
    # Метод 2: Проверка по частям имени материала
    if len(found_textures) < len(texture_keywords):
        material_parts = re.split(r"[_\-\s.]+", material_name_lower)
        material_parts = [part for part in material_parts if len(part) > 2]
        
        for texture_file in texture_files:
            texture_basename = os.path.basename(texture_file).lower()
            
            # Проверяем, содержит ли название текстуры любую значимую часть имени материала
            if any(part in texture_basename for part in material_parts):
                for texture_type, keywords in texture_keywords.items():
                    if texture_type not in found_textures:
                        for keyword in keywords:
                            if keyword in texture_basename:
                                found_textures[texture_type] = texture_file
                                print(f"Найдена текстура (метод 2): {texture_type} = {texture_basename}")
                                break
    
    # Метод 3: Поиск по имени модели
    if len(found_textures) < len(texture_keywords):
        for texture_file in texture_files:
            texture_basename = os.path.basename(texture_file).lower()
            
            # Проверяем, содержит ли название текстуры имя модели
            if model_name_lower in texture_basename:
                for texture_type, keywords in texture_keywords.items():
                    if texture_type not in found_textures:
                        for keyword in keywords:
                            if keyword in texture_basename:
                                found_textures[texture_type] = texture_file
                                print(f"Найдена текстура (метод 3): {texture_type} = {texture_basename}")
                                break
    
    # Метод 4: Поиск общих префиксов в текстурах
    if len(found_textures) < len(texture_keywords):
        # Группируем текстуры по префиксам
        texture_groups = {}
        
        for texture_file in texture_files:
            texture_basename = os.path.basename(texture_file).lower()
            parts = texture_basename.split("_")
            
            if len(parts) >= 2:
                # Используем первую часть как префикс
                prefix = parts[0]
                if prefix not in texture_groups:
                    texture_groups[prefix] = []
                texture_groups[prefix].append(texture_file)
        
        # Ищем префикс, который соответствует имени модели или материала
        matching_prefixes = []
        
        # Сначала проверяем, есть ли префикс, соответствующий имени модели
        model_prefix = model_name_lower.split("_")[0]
        if model_prefix in texture_groups:
            matching_prefixes.append(model_prefix)
        
        # Затем проверяем, есть ли префикс, соответствующий имени материала
        material_prefix = material_name_lower.split("_")[0]
        if material_prefix in texture_groups and material_prefix not in matching_prefixes:
            matching_prefixes.append(material_prefix)
        
        # Если нет точных совпадений, берем префикс с наибольшим количеством текстур
        if not matching_prefixes and texture_groups:
            largest_prefix = max(texture_groups.keys(), key=lambda k: len(texture_groups[k]))
            matching_prefixes.append(largest_prefix)
        
        # Обрабатываем найденные префиксы
        for prefix in matching_prefixes:
            print(f"Рассматриваем группу текстур с префиксом: {prefix}")
            for texture_file in texture_groups[prefix]:
                texture_basename = os.path.basename(texture_file).lower()
                for texture_type, keywords in texture_keywords.items():
                    if texture_type not in found_textures:
                        for keyword in keywords:
                            if keyword in texture_basename:
                                found_textures[texture_type] = texture_file
                                print(f"Найдена текстура (метод 4): {texture_type} = {texture_basename}")
                                break
    
    # Метод 5: Поиск по ключевым словам типов текстур в любых доступных текстурах
    if len(found_textures) < len(texture_keywords):
        print("Ищем любые подходящие текстуры по ключевым словам")
        
        for texture_type, keywords in texture_keywords.items():
            if texture_type not in found_textures:
                for texture_file in texture_files:
                    texture_basename = os.path.basename(texture_file).lower()
                    for keyword in keywords:
                        if keyword in texture_basename:
                            found_textures[texture_type] = texture_file
                            print(f"Найдена текстура (метод 5): {texture_type} = {texture_basename}")
                            break
                    if texture_type in found_textures:
                        break
    
    print(f"Всего найдено текстур для материала {material_name_lower}: {len(found_textures)}")
    return found_textures

def create_principled_shader(matnet_node, material_name, texture_maps):
    """Создаёт и настраивает Principled Shader с указанными текстурами"""
    # Очищаем имя материала для использования в качестве имени ноды
    safe_name = clean_node_name(material_name)
    
    # Укорачиваем имя, если оно слишком длинное
    if len(safe_name) > 30:
        safe_name = safe_name[:30]
    
    # Если у нас уже есть узел с таким именем, добавим суффикс
    counter = 1
    original_name = safe_name
    while matnet_node.node(safe_name) is not None:
        safe_name = f"{original_name}_{counter}"
        counter += 1
    
    print(f"Создаем материал: {safe_name}")
    for tex_type, tex_path in texture_maps.items():
        print(f"- Текстура {tex_type}: {os.path.basename(tex_path)}")
    
    # Создаём Principled Shader
    try:
        material = matnet_node.createNode("principledshader", safe_name)
    except hou.OperationFailed:
        try:
            material = matnet_node.createNode("principledshader::2.0", safe_name)
        except hou.OperationFailed:
            try:
                material = matnet_node.createNode("redshift::Material", safe_name)
            except:
                try:
                    # Если не удалось создать ни один из шейдеров, попробуем создать базовый
                    material = matnet_node.createNode("material", safe_name)
                except hou.OperationFailed:
                    # Если всё ещё не удалось, используем ещё более простое имя
                    random_name = f"mat_{hash(material_name) % 10000:04d}"
                    material = matnet_node.createNode("material", random_name)
    
    # Базовый цвет белый для начала
    if hasattr(material, "parmTuple") and material.parmTuple("basecolor"):
        material.parmTuple("basecolor").set((1.0, 1.0, 1.0))
    
    # Подключаем текстуры для Principled Shader
    # BaseMap (диффузная карта)
    if "BaseMap" in texture_maps:
        print(f"Устанавливаем BaseMap: {texture_maps['BaseMap']}")
        try:
            if material.parm("basecolor_useTexture"):
                material.parm("basecolor_useTexture").set(True)
                material.parm("basecolor_texture").set(texture_maps["BaseMap"])
            elif material.parm("diffuse_texture"):
                material.parm("diffuse_texture").set(texture_maps["BaseMap"])
            elif material.parm("tex0"):  # Для базовых материалов
                material.parm("tex0").set(texture_maps["BaseMap"])
        except:
            print(f"Не удалось установить BaseMap")
    
    # Normal map
    if "Normal" in texture_maps:
        print(f"Устанавливаем Normal: {texture_maps['Normal']}")
        try:
            if material.parm("baseNormal_useTexture"):
                material.parm("baseNormal_useTexture").set(True)
                material.parm("baseNormal_texture").set(texture_maps["Normal"])
            elif material.parm("normal_texture"):
                material.parm("normal_texture").set(texture_maps["Normal"])
        except:
            print(f"Не удалось установить Normal map")
    
    # Roughness map
    if "Roughness" in texture_maps:
        print(f"Устанавливаем Roughness: {texture_maps['Roughness']}")
        try:
            if material.parm("rough_useTexture"):
                material.parm("rough_useTexture").set(True)
                material.parm("rough_texture").set(texture_maps["Roughness"])
            elif material.parm("roughness_texture"):
                material.parm("roughness_texture").set(texture_maps["Roughness"])
        except:
            print(f"Не удалось установить Roughness map")
    
    # Metallic map
    if "Metallic" in texture_maps:
        print(f"Устанавливаем Metallic: {texture_maps['Metallic']}")
        try:
            if material.parm("metallic_useTexture"):
                material.parm("metallic_useTexture").set(True)
                material.parm("metallic_texture").set(texture_maps["Metallic"])
            elif material.parm("metalness_texture"):
                material.parm("metalness_texture").set(texture_maps["Metallic"])
        except:
            print(f"Не удалось установить Metallic map")
    
    # AO map
    if "AO" in texture_maps:
        print(f"Устанавливаем AO: {texture_maps['AO']}")
        try:
            if material.parm("baseAO_useTexture"):
                material.parm("baseAO_useTexture").set(True)
                material.parm("baseAO_texture").set(texture_maps["AO"])
            elif material.parm("ao_texture"):
                material.parm("ao_texture").set(texture_maps["AO"])
        except:
            print(f"Не удалось установить AO map")
    
    # Emission map
    if "Emissive" in texture_maps:
        print(f"Устанавливаем Emissive: {texture_maps['Emissive']}")
        try:
            if material.parm("emitcolor_useTexture"):
                material.parm("emitcolor_useTexture").set(True)
                material.parm("emitcolor_texture").set(texture_maps["Emissive"])
            elif material.parm("emission_texture"):
                material.parm("emission_texture").set(texture_maps["Emissive"])
        except:
            print(f"Не удалось установить Emissive map")
    
    # Разложим ноду материала на вьюпорте для удобства
    material.moveToGoodPosition()
    
    return material

def main():
    node = hou.pwd()
    geo = node.geometry()
    
    # Получаем переданные данные
    model_file = "''' + model_file_fixed + '''"
    folder_path = "''' + folder_path_fixed + '''"
    model_basename = os.path.basename(model_file)
    
    # Данные для текстур и материалов - загружаем напрямую
    texture_files = ''' + texture_files_str + '''
    texture_keywords = ''' + texture_keywords_str + '''
    material_cache = ''' + material_cache_str + '''
    
    matnet_path = "''' + matnet_path_fixed + '''"
    matnet_node = hou.node(matnet_path)
    if not matnet_node:
        print("Не удалось найти matnet!")
        return
    
    print(f"Обработка модели: {model_basename}")
    print(f"Путь к материалам: {matnet_path}")
    
    # Проверяем наличие атрибута shop_materialpath или другого атрибута материала
    mat_attr = None
    for attr_name in ["shop_materialpath", "material", "mat", "materialpath"]:
        mat_attr = geo.findPrimAttrib(attr_name)
        if mat_attr:
            print(f"Найден атрибут материала: {attr_name}")
            break
    
    if not mat_attr:
        print("Атрибут материала не найден в модели. Создаем новый атрибут.")
        geo.addAttrib(hou.attribType.Prim, "shop_materialpath", "")
        mat_attr = geo.findPrimAttrib("shop_materialpath")
    
    # Собираем все уникальные материалы
    material_values = set()
    for prim in geo.prims():
        val = prim.attribValue(mat_attr)
        if isinstance(val, str) and val:
            material_values.add(val)
    
    print(f"Найдено {len(material_values)} уникальных материалов")
    
    # Если в модели нет материалов, создадим один материал по умолчанию
    if not material_values:
        print("В модели нет материалов. Создаем материал по умолчанию.")
        default_mat_name = os.path.splitext(model_basename)[0]
        material_values.add(default_mat_name)
    
    # Словарь для соответствия старых и новых путей материалов
    material_mapping = {}
    
    # Создаём материалы для каждого уникального значения
    for mat_path in material_values:
        # Извлекаем имя материала из пути
        if "/" in mat_path:
            mat_name = os.path.basename(mat_path)
        else:
            mat_name = mat_path
        
        print(f"Обработка материала: {mat_name}")
        
        # Проверяем, создавали ли мы уже этот материал
        if mat_name in material_cache:
            # Используем существующий материал
            material_mapping[mat_path] = material_cache[mat_name]
            print(f"Используем существующий материал: {material_cache[mat_name]}")
            continue
        
        # Ищем текстуры для этого материала
        found_textures = find_matching_textures(mat_name, texture_files, texture_keywords, model_basename)
        
        # Создаём и настраиваем Principled Shader
        material = create_principled_shader(matnet_node, mat_name, found_textures)
        
        # Запоминаем путь к новому материалу
        material_mapping[mat_path] = material.path()
        material_cache[mat_name] = material.path()
        
        print(f"Создан материал: {material.path()}")
    
    # Обновляем кэш материалов в JSON
    try:
        # Используя ваш подход - нормализуем путь и заменяем разделители
        cache_dir = os.path.dirname(model_file)
        cache_path = os.path.join(cache_dir, "material_cache.json")
        # Нормализуем путь
        cache_path = os.path.normpath(cache_path)
        # Заменяем системный разделитель на "/"
        cache_path = cache_path.replace(os.sep, "/")
        with open(cache_path, "w") as f:
            json.dump(material_cache, f, indent=4)
        print(f"Кэш материалов сохранен в: {cache_path}")
    except Exception as e:
        # Игнорируем ошибки при записи кэша
        print(f"Не удалось сохранить кэш материалов: {e}")
    
    # Если у нас нет никаких материалов в матнете, добавим хотя бы один
    if not material_mapping:
        default_mat_name = os.path.splitext(model_basename)[0]
        default_textures = {}
        for texture_file in texture_files:
            texture_basename = os.path.basename(texture_file).lower()
            for texture_type, keywords in texture_keywords.items():
                if texture_type not in default_textures:
                    for keyword in keywords:
                        if keyword in texture_basename:
                            default_textures[texture_type] = texture_file
                            break
        default_material = create_principled_shader(matnet_node, default_mat_name, default_textures)
        material_mapping["default"] = default_material.path()
        print(f"Создан материал по умолчанию: {default_material.path()}")
    
    # Переназначаем пути к материалам для всех примитивов
    if material_mapping:
        default_material_path = list(material_mapping.values())[0]  # Берем первый материал как дефолтный
        for prim in geo.prims():
            old_mat_path = prim.attribValue(mat_attr)
            if old_mat_path in material_mapping:
                prim.setAttribValue(mat_attr, material_mapping[old_mat_path])
            else:
                # Если материал не найден, используем дефолтный
                prim.setAttribValue(mat_attr, default_material_path)
    
    print(f"Обработано {len(material_mapping)} материалов для модели {model_basename}.")

main()
'''
    
    return python_code


def get_node_bbox(node):
    """Получает bounding box ноды"""
    try:
        geo = node.geometry()
        if not geo:
            return {
                "min": (0, 0, 0),
                "max": (1, 1, 1),
                "size": (1, 1, 1),
                "center": (0.5, 0.5, 0.5)
            }
        
        bbox = geo.boundingBox()
        if not bbox:
            return {
                "min": (0, 0, 0),
                "max": (1, 1, 1),
                "size": (1, 1, 1),
                "center": (0.5, 0.5, 0.5)
            }
        
        min_pt = bbox.minvec()
        max_pt = bbox.maxvec()
        size = max_pt - min_pt
        center = bbox.center()
        
        return {
            "min": (min_pt[0], min_pt[1], min_pt[2]),
            "max": (max_pt[0], max_pt[1], max_pt[2]),
            "size": (size[0], size[1], size[2]),
            "center": (center[0], center[1], center[2])
        }
    except:
        # Возвращаем значения по умолчанию в случае ошибки
        return {
            "min": (0, 0, 0),
            "max": (1, 1, 1),
            "size": (1, 1, 1),
            "center": (0.5, 0.5, 0.5)
        }


def arrange_models_in_grid(models_info):
    """Размещает модели в сетке с учетом их bounding box"""
    try:
        # Определяем максимальный размер по X для расстановки по сетке
        max_x_size = max(model["bbox"]["size"][0] for model in models_info)
        max_z_size = max(model["bbox"]["size"][2] for model in models_info)
        
        # Добавляем небольшой отступ между моделями
        spacing_x = max_x_size * 1.2
        spacing_z = max_z_size * 1.2
        
        # Определяем количество колонок в сетке (примерно квадратное расположение)
        num_cols = int(1.5 * (len(models_info) ** 0.5))
        if num_cols < 1:
            num_cols = 1
        
        for i, model_info in enumerate(models_info):
            node = model_info["node"]
            
            # Вычисляем позицию в сетке
            col = i % num_cols
            row = i // num_cols
            
            # Устанавливаем позицию ноды
            x_pos = col * spacing_x
            z_pos = row * spacing_z
            
            # Получаем текущее преобразование ноды
            xform = node.parmTuple("t")
            if xform:
                xform.set((x_pos, 0, z_pos))
    except Exception as e:
        # Игнорируем ошибки при расстановке моделей
        print(f"Не удалось расставить модели: {e}")

# Этот код выполнится при нажатии кнопки на полке
create_multi_material_models()