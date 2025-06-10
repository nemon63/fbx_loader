"""
Утилиты для работы с UDIM текстурами - полная реализация
"""
import os
import re
from collections import defaultdict

# Импортируем константы UDIM
try:
    from constants import UDIM_CONFIG
except ImportError:
    # Fallback если constants недоступны
    UDIM_CONFIG = {
        "pattern": r'^(.+)[._](\d{4})\.(jpg|jpeg|png|tga|tif|tiff|exr|hdr)$',
        "range_start": 1001,
        "range_end": 1100,
        "min_tiles": 2,
        "placeholder": "<UDIM>"
    }


def detect_udim_sequences(texture_files):
    """
    Обнаруживает UDIM последовательности в списке файлов текстур
    
    Args:
        texture_files (list): Список путей к файлам текстур
        
    Returns:
        dict: {
            'udim_sequences': {base_name: {'pattern': path_with_placeholder, 'tiles': [tile_numbers], 'files': [file_paths]}},
            'single_textures': [non_udim_files]
        }
    """
    
    udim_pattern = re.compile(UDIM_CONFIG["pattern"], re.IGNORECASE)
    udim_groups = defaultdict(list)
    single_textures = []
    
    print(f"DEBUG UDIM: Анализируем {len(texture_files)} файлов на UDIM последовательности")
    
    # Группируем файлы по UDIM паттернам
    for texture_file in texture_files:
        filename = os.path.basename(texture_file)
        match = udim_pattern.match(filename)
        
        if match:
            base_name = match.group(1)  # Базовое имя без UDIM номера
            udim_number = int(match.group(2))  # UDIM номер (1001, 1002, etc.)
            extension = match.group(3)  # Расширение файла
            
            # Проверяем, что UDIM номер в допустимом диапазоне
            if UDIM_CONFIG["range_start"] <= udim_number <= UDIM_CONFIG["range_end"]:
                udim_groups[base_name].append({
                    'file': texture_file,
                    'udim': udim_number,
                    'extension': extension
                })
                print(f"DEBUG UDIM: Найден UDIM тайл: {filename} -> база: {base_name}, номер: {udim_number}")
            else:
                single_textures.append(texture_file)
                print(f"DEBUG UDIM: UDIM номер {udim_number} вне диапазона для файла: {filename}")
        else:
            single_textures.append(texture_file)
    
    # Создаем UDIM последовательности
    udim_sequences = {}
    
    for base_name, tiles in udim_groups.items():
        if len(tiles) >= UDIM_CONFIG["min_tiles"]:
            # Сортируем тайлы по UDIM номеру
            tiles.sort(key=lambda x: x['udim'])
            
            # Создаем путь с UDIM плейсхолдером
            first_tile = tiles[0]
            directory = os.path.dirname(first_tile['file'])
            extension = first_tile['extension']
            
            # Формируем UDIM путь
            udim_pattern_path = os.path.join(directory, f"{base_name}.{UDIM_CONFIG['placeholder']}.{extension}")
            udim_pattern_path = os.path.normpath(udim_pattern_path).replace(os.sep, "/")
            
            udim_sequences[base_name] = {
                'pattern': udim_pattern_path,
                'tiles': [tile['udim'] for tile in tiles],
                'files': [tile['file'] for tile in tiles],
                'tile_count': len(tiles)
            }
            
            print(f"DEBUG UDIM: Создана UDIM последовательность '{base_name}': {len(tiles)} тайлов")
            print(f"DEBUG UDIM: Паттерн: {udim_pattern_path}")
            print(f"DEBUG UDIM: Тайлы: {[tile['udim'] for tile in tiles]}")
        else:
            # Недостаточно тайлов для UDIM, добавляем как обычные текстуры
            for tile in tiles:
                single_textures.append(tile['file'])
            print(f"DEBUG UDIM: Недостаточно тайлов для UDIM '{base_name}': {len(tiles)} < {UDIM_CONFIG['min_tiles']}")
    
    print(f"DEBUG UDIM: Итого найдено {len(udim_sequences)} UDIM последовательностей и {len(single_textures)} одиночных текстур")
    
    return {
        'udim_sequences': udim_sequences,
        'single_textures': single_textures
    }


def find_matching_textures_with_udim(material_name, texture_files, texture_keywords, model_basename=""):
    """
    Расширенная функция поиска текстур с поддержкой UDIM
    
    Args:
        material_name (str): Имя материала
        texture_files (list): Список файлов текстур
        texture_keywords (dict): Словарь ключевых слов для типов текстур
        model_basename (str): Базовое имя модели
        
    Returns:
        dict: Найденные текстуры, где UDIM используют плейсхолдер
    """
    
    if not material_name or not texture_files:
        return {}
    
    print(f"DEBUG UDIM: Поиск текстур с UDIM поддержкой для материала '{material_name}'")
    
    # Обнаруживаем UDIM последовательности
    udim_analysis = detect_udim_sequences(texture_files)
    udim_sequences = udim_analysis['udim_sequences']
    single_textures = udim_analysis['single_textures']
    
    # Объединяем UDIM паттерны и одиночные текстуры для поиска
    all_texture_candidates = []
    
    # Добавляем UDIM паттерны
    for base_name, udim_info in udim_sequences.items():
        all_texture_candidates.append({
            'path': udim_info['pattern'],
            'name': base_name,
            'type': 'udim',
            'tile_count': udim_info['tile_count']
        })
    
    # Добавляем одиночные текстуры
    for texture_file in single_textures:
        filename = os.path.splitext(os.path.basename(texture_file))[0]
        all_texture_candidates.append({
            'path': texture_file,
            'name': filename,
            'type': 'single'
        })
    
    print(f"DEBUG UDIM: Всего кандидатов для поиска: {len(all_texture_candidates)} ({len(udim_sequences)} UDIM + {len(single_textures)} одиночных)")
    
    # Ищем соответствия
    found_textures = {}
    
    # Подготавливаем базовые имена для поиска
    material_name_lower = material_name.lower().replace(" ", "_")
    model_name_lower = os.path.splitext(model_basename)[0].lower() if model_basename else ""
    
    search_bases = []
    if material_name_lower:
        search_bases.append(material_name_lower)
        material_parts = re.split(r"[_\-\s.]+", material_name_lower)
        search_bases.extend([part for part in material_parts if len(part) > 2])
    
    if model_name_lower:
        search_bases.append(model_name_lower)
        model_parts = re.split(r"[_\-\s.]+", model_name_lower)
        search_bases.extend([part for part in model_parts if len(part) > 2])
    
    print(f"DEBUG UDIM: Базовые имена для поиска: {search_bases}")
    
    # Основной поиск
    for candidate in all_texture_candidates:
        candidate_name_lower = candidate['name'].lower()
        candidate_path = candidate['path']
        candidate_type = candidate['type']
        
        print(f"DEBUG UDIM: Анализируем кандидата: {candidate['name']} ({candidate_type})")
        
        # Проверяем соответствие базовым именам
        matches_base = False
        for base in search_bases:
            if base in candidate_name_lower:
                matches_base = True
                print(f"DEBUG UDIM: Найдено соответствие базовому имени '{base}' в '{candidate['name']}'")
                break
        
        # Определяем тип текстуры по ключевым словам
        texture_type_found = None
        for texture_type, keywords in texture_keywords.items():
            if texture_type in found_textures:
                continue  # Уже найдена текстура этого типа
                
            for keyword in keywords:
                if keyword in candidate_name_lower:
                    texture_type_found = texture_type
                    print(f"DEBUG UDIM: Найдено ключевое слово '{keyword}' -> тип '{texture_type}' в '{candidate['name']}'")
                    break
            
            if texture_type_found:
                break
        
        # Добавляем текстуру
        if texture_type_found and texture_type_found not in found_textures:
            if matches_base or len(search_bases) == 0:
                found_textures[texture_type_found] = candidate_path
                
                if candidate_type == 'udim':
                    tile_count = candidate.get('tile_count', 0)
                    print(f"DEBUG UDIM: ✓ Назначена UDIM текстура {texture_type_found}: {candidate['name']} ({tile_count} тайлов)")
                else:
                    print(f"DEBUG UDIM: ✓ Назначена обычная текстура {texture_type_found}: {candidate['name']}")
            else:
                print(f"DEBUG UDIM: Пропущена текстура {candidate['name']} (не соответствует базовому имени)")
    
    # Агрессивный поиск, если ничего не найдено
    if not found_textures:
        print("DEBUG UDIM: Первичный поиск не дал результатов, пробуем агрессивный поиск")
        
        for candidate in all_texture_candidates:
            candidate_name_lower = candidate['name'].lower()
            candidate_path = candidate['path']
            
            for texture_type, keywords in texture_keywords.items():
                if texture_type in found_textures:
                    continue
                    
                for keyword in keywords:
                    if keyword in candidate_name_lower:
                        found_textures[texture_type] = candidate_path
                        print(f"DEBUG UDIM: Агрессивный поиск - {texture_type}: {candidate['name']}")
                        break
                        
                if texture_type in found_textures:
                    break
    
    # Fallback
    if not found_textures and all_texture_candidates:
        first_candidate = all_texture_candidates[0]
        found_textures["BaseMap"] = first_candidate['path']
        print(f"DEBUG UDIM: Fallback - используем первую текстуру как BaseMap: {first_candidate['name']}")
    
    print(f"DEBUG UDIM: Итого найдено текстур: {len(found_textures)}")
    for tex_type, tex_path in found_textures.items():
        if UDIM_CONFIG['placeholder'] in tex_path:
            print(f"DEBUG UDIM: {tex_type}: {os.path.basename(tex_path)} (UDIM)")
        else:
            print(f"DEBUG UDIM: {tex_type}: {os.path.basename(tex_path)}")
    
    return found_textures


def validate_udim_sequence(files):
    """
    Проверяет валидность UDIM последовательности
    
    Args:
        files (list): Список файлов UDIM тайлов
        
    Returns:
        bool: True если последовательность валидна
    """
    if len(files) < UDIM_CONFIG["min_tiles"]:
        return False
    
    udim_pattern = re.compile(UDIM_CONFIG["pattern"], re.IGNORECASE)
    udim_numbers = []
    
    for file_path in files:
        filename = os.path.basename(file_path)
        match = udim_pattern.match(filename)
        
        if not match:
            return False
        
        udim_number = int(match.group(2))
        if not (UDIM_CONFIG["range_start"] <= udim_number <= UDIM_CONFIG["range_end"]):
            return False
        
        udim_numbers.append(udim_number)
    
    # Проверяем, что нет дубликатов
    return len(udim_numbers) == len(set(udim_numbers))


def create_udim_pattern_path(first_file):
    """
    Создает UDIM паттерн путь из первого файла последовательности
    
    Args:
        first_file (str): Путь к первому файлу UDIM последовательности
        
    Returns:
        str: Путь с UDIM плейсхолдером
    """
    udim_pattern = re.compile(UDIM_CONFIG["pattern"], re.IGNORECASE)
    filename = os.path.basename(first_file)
    match = udim_pattern.match(filename)
    
    if not match:
        return first_file
    
    base_name = match.group(1)
    extension = match.group(3)
    directory = os.path.dirname(first_file)
    
    udim_path = os.path.join(directory, f"{base_name}.{UDIM_CONFIG['placeholder']}.{extension}")
    return os.path.normpath(udim_path).replace(os.sep, "/")


def get_udim_info_from_path(udim_path):
    """
    Извлекает информацию о UDIM из пути с плейсхолдером
    
    Args:
        udim_path (str): Путь с UDIM плейсхолдером
        
    Returns:
        dict: Информация о UDIM или None
    """
    if UDIM_CONFIG['placeholder'] not in udim_path:
        return None
    
    directory = os.path.dirname(udim_path)
    filename_pattern = os.path.basename(udim_path)
    
    # Заменяем плейсхолдер на regex паттерн
    regex_pattern = filename_pattern.replace(UDIM_CONFIG['placeholder'], r'(\d{4})')
    regex_pattern = '^' + re.escape(regex_pattern).replace(r'\\(\\\d\{4\}\\)', r'(\d{4})') + '$'
    
    return {
        'directory': directory,
        'pattern': regex_pattern,
        'placeholder_path': udim_path
    }


def find_udim_tiles_from_pattern(udim_path):
    """
    Находит все UDIM тайлы по паттерну пути
    
    Args:
        udim_path (str): Путь с UDIM плейсхолдером
        
    Returns:
        list: Список найденных файлов UDIM тайлов
    """
    udim_info = get_udim_info_from_path(udim_path)
    if not udim_info:
        return []
    
    directory = udim_info['directory']
    pattern = re.compile(udim_info['pattern'], re.IGNORECASE)
    
    found_tiles = []
    
    try:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                if pattern.match(filename):
                    file_path = os.path.join(directory, filename)
                    if os.path.isfile(file_path):
                        found_tiles.append(file_path)
    except Exception as e:
        print(f"Ошибка поиска UDIM тайлов в {directory}: {e}")
    
    return sorted(found_tiles)


def is_udim_texture(texture_path):
    """
    Проверяет, является ли путь UDIM текстурой
    
    Args:
        texture_path (str): Путь к текстуре
        
    Returns:
        bool: True если это UDIM текстура
    """
    return UDIM_CONFIG['placeholder'] in texture_path


def get_udim_statistics(texture_files):
    """
    Получает статистику по UDIM текстурам
    
    Args:
        texture_files (list): Список файлов текстур
        
    Returns:
        dict: Статистика UDIM
    """
    udim_analysis = detect_udim_sequences(texture_files)
    
    total_udim_sequences = len(udim_analysis['udim_sequences'])
    total_udim_tiles = sum(len(seq['tiles']) for seq in udim_analysis['udim_sequences'].values())
    total_single_textures = len(udim_analysis['single_textures'])
    
    return {
        'udim_sequences': total_udim_sequences,
        'udim_tiles': total_udim_tiles,
        'single_textures': total_single_textures,
        'total_files': len(texture_files),
        'udim_percentage': (total_udim_tiles / len(texture_files) * 100) if texture_files else 0
    }


# Функции для интеграции с существующим кодом

def enhanced_find_matching_textures(material_name, texture_files, texture_keywords, model_basename=""):
    """
    Обертка для обратной совместимости - автоматически использует UDIM если найдены последовательности
    """
    # Быстрая проверка на наличие потенциальных UDIM файлов
    udim_pattern = re.compile(UDIM_CONFIG["pattern"], re.IGNORECASE)
    has_potential_udim = any(udim_pattern.match(os.path.basename(f)) for f in texture_files[:10])  # Проверяем первые 10
    
    if has_potential_udim:
        print("DEBUG: Обнаружены потенциальные UDIM файлы, используем UDIM поиск")
        return find_matching_textures_with_udim(material_name, texture_files, texture_keywords, model_basename)
    else:
        # Используем обычный поиск без UDIM
        from material_utils import find_matching_textures
        return find_matching_textures(material_name, texture_files, texture_keywords, model_basename)


def print_udim_info(texture_files):
    """
    Выводит информацию о найденных UDIM последовательностях
    """
    udim_analysis = detect_udim_sequences(texture_files)
    stats = get_udim_statistics(texture_files)
    
    print("=" * 50)
    print("UDIM АНАЛИЗ")
    print("=" * 50)
    print(f"Всего файлов текстур: {stats['total_files']}")
    print(f"UDIM последовательностей: {stats['udim_sequences']}")
    print(f"UDIM тайлов: {stats['udim_tiles']}")
    print(f"Одиночных текстур: {stats['single_textures']}")
    print(f"UDIM покрытие: {stats['udim_percentage']:.1f}%")
    print("")
    
    if udim_analysis['udim_sequences']:
        print("Найденные UDIM последовательности:")
        for base_name, udim_info in udim_analysis['udim_sequences'].items():
            print(f"  '{base_name}': {udim_info['tile_count']} тайлов ({min(udim_info['tiles'])}-{max(udim_info['tiles'])})")
            print(f"    Паттерн: {udim_info['pattern']}")
    
    print("=" * 50)