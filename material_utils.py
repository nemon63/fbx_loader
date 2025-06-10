"""
Исправленные функции для работы с материалами - с правильной поддержкой MaterialX
"""
import hou
import os
import re
from utils import clean_node_name, generate_unique_name

# Импорт UDIM поддержки
try:
    from udim_utils import is_udim_texture, get_udim_statistics, print_udim_info
    UDIM_SUPPORT = True
except ImportError:
    UDIM_SUPPORT = False
    def is_udim_texture(path):
        return '<UDIM>' in str(path)

# Расширенные ключевые слова для текстур
ENHANCED_TEXTURE_KEYWORDS = {
    "BaseMap": [
        "basemap", "diff", "dif", "diffuse", "albedo", "basecolor", "col", "color", 
        "base", "alb", "bc", "_d", "-d", "_c", "-c", "diffmap", "colormap", "diffusemap",
        "_color", "_base", "_basecolor", "_albedo", "BaseColor", "Albedo", "Base_Color",
        "BaseMap", "DiffuseMap", "ColorMap", "Diffuse", "Color"
    ],
    "Normal": [
        "normal", "norm", "nml", "nrm", "_n", "-n", "nor", "normalmap", "normalmaps",
        "bump", "bumpmap", "_bump", "_b", "-b", "relief", "bumpmaps",
        "Normal", "NormalMap", "Normal_Map", "_normal", "_norm", "_nml"
    ],
    "Roughness": [
        "rough", "roughness", "rgh", "_r", "-r", "roughnessmap", "roughmaps",
        "gloss", "glossmap", "glossiness", "smoothness", "smooth",
        "Roughness", "RoughnessMap", "Rough", "_roughness", "_rough", "_rgh"
    ],
    "Metallic": [
        "metal", "metallic", "met", "metalness", "_m", "-m", "metallicmap", "metallicmaps",
        "spec", "specular", "_s", "-s", "specularmap", "specularmaps",
        "Metallic", "MetallicMap", "Metal", "_metallic", "_metal", "_met"
    ],
    "AO": [
        "ao", "ambient", "occlusion", "ambientocclusion", "_ao", "-ao", 
        "occlusionmap", "ambientocclusionmap", "aomaps",
        "AO", "AmbientOcclusion", "Ambient_Occlusion", "_ambientocclusion"
    ],
    "Emissive": [
        "emissive", "emission", "emit", "glow", "_e", "-e", "emissionmap",
        "emissivemap", "selfillum", "emissivemaps",
        "Emissive", "EmissiveMap", "Emission", "Emit", "_emissive", "_emission"
    ],
    "Height": [
        "height", "heightmap", "displacement", "disp", "_h", "-h", 
        "displacementmap", "parallax", "heightmaps",
        "Height", "HeightMap", "Displacement", "Disp", "_height", "_disp", "_displacement"
    ],
    "Opacity": [
        "opacity", "alpha", "transparent", "transparency", "_a", "-a", 
        "_o", "-o", "opacitymap", "alphamap", "mask", "opacitymaps",
        "Opacity", "OpacityMap", "Alpha", "AlphaMap", "_opacity", "_alpha"
    ],
    "Specular": [
        "specular", "spec", "_s", "-s", "specularmap", "reflection", "refl", "specularmaps",
        "Specular", "SpecularMap", "Reflection", "_specular", "_spec"
    ]
}


def find_matching_textures(material_name, texture_files, texture_keywords=None, model_basename=""):
    """
    Главная функция поиска текстур с автоматической поддержкой UDIM
    """
    if texture_keywords is None:
        texture_keywords = ENHANCED_TEXTURE_KEYWORDS
    
    found_textures = {}
    
    if not material_name or not texture_files:
        print("DEBUG: Пустые входные данные для поиска текстур")
        return found_textures
    
    print(f"DEBUG: Поиск текстур для материала '{material_name}' (файлов: {len(texture_files)})")
    
    # Проверяем на UDIM, если поддержка доступна
    if UDIM_SUPPORT:
        try:
            # Быстрая проверка на потенциальные UDIM файлы
            udim_pattern = re.compile(r'^(.+)[._](\d{4})\.(jpg|jpeg|png|tga|tif|tiff|exr|hdr|pic|rat)$', re.IGNORECASE)
            potential_udim_count = sum(1 for f in texture_files[:50] if udim_pattern.match(os.path.basename(f)))
            
            print(f"DEBUG: Найдено {potential_udim_count} потенциальных UDIM файлов из {min(len(texture_files), 50)} проверенных")
            
            if potential_udim_count >= 2:  # Если найдено хотя бы 2 потенциальных UDIM файла
                print(f"DEBUG: Переключаемся на UDIM анализ")
                
                # Показываем UDIM статистику
                udim_stats = get_udim_statistics(texture_files)
                if udim_stats['udim_sequences'] > 0:
                    print(f"DEBUG: Найдено {udim_stats['udim_sequences']} UDIM последовательностей с {udim_stats['udim_tiles']} тайлами")
                    if udim_stats['udim_sequences'] <= 5:  # Показываем детали только для небольших наборов
                        print_udim_info(texture_files)
                
                from udim_utils import find_matching_textures_with_udim
                return find_matching_textures_with_udim(material_name, texture_files, texture_keywords, model_basename)
            else:
                print("DEBUG: UDIM файлы не обнаружены или их недостаточно, используем обычный поиск")
        except Exception as e:
            print(f"WARNING: Ошибка UDIM анализа: {e}, используем обычный поиск")
    
    # Обычный поиск без UDIM
    return _find_matching_textures_standard(material_name, texture_files, texture_keywords, model_basename)


def _find_matching_textures_standard(material_name, texture_files, texture_keywords, model_basename=""):
    """Улучшенная стандартная функция поиска текстур без UDIM"""
    found_textures = {}
    
    print(f"DEBUG: Стандартный поиск текстур для материала '{material_name}'")
    print(f"DEBUG: Количество доступных текстур: {len(texture_files)}")
    
    # Если только одна текстура, используем как BaseMap
    if len(texture_files) == 1:
        found_textures["BaseMap"] = texture_files[0]
        print(f"DEBUG: Единственная текстура назначена как BaseMap: {os.path.basename(texture_files[0])}")
        return found_textures
    
    # Если текстур нет, возвращаем пустой словарь
    if not texture_files:
        print("DEBUG: Нет доступных текстур")
        return found_textures
    
    # Подготавливаем имена для поиска
    material_name_lower = material_name.lower().replace(" ", "_")
    model_name_lower = os.path.splitext(model_basename)[0].lower() if model_basename else ""
    
    print(f"DEBUG: Ищем по имени материала: '{material_name_lower}'")
    if model_name_lower:
        print(f"DEBUG: Ищем по имени модели: '{model_name_lower}'")
    
    # Создаем список всех возможных базовых имен для поиска
    search_bases = []
    if material_name_lower:
        search_bases.append(material_name_lower)
        # Добавляем части имени материала
        material_parts = re.split(r"[_\-\s.]+", material_name_lower)
        search_bases.extend([part for part in material_parts if len(part) > 2])
    
    if model_name_lower:
        search_bases.append(model_name_lower)
        # Добавляем части имени модели
        model_parts = re.split(r"[_\-\s.]+", model_name_lower)
        search_bases.extend([part for part in model_parts if len(part) > 2])
    
    # Удаляем дубликаты
    search_bases = list(set(search_bases))
    print(f"DEBUG: Базовые имена для поиска: {search_bases}")
    
    # Основной поиск с приоритетом
    for texture_file in texture_files:
        texture_basename = os.path.basename(texture_file).lower()
        texture_name_no_ext = os.path.splitext(texture_basename)[0].lower()
        
        print(f"DEBUG: Анализируем текстуру: {texture_basename}")
        
        # Проверяем соответствие базовым именам
        matches_base = False
        matched_base = ""
        for base in search_bases:
            if base in texture_name_no_ext:
                matches_base = True
                matched_base = base
                print(f"DEBUG: Найдено соответствие базовому имени '{base}' в '{texture_basename}'")
                break
        
        # Определяем тип текстуры по ключевым словам с приоритетом
        texture_type_found = None
        matched_keyword = ""
        keyword_priority = 0
        
        for texture_type, keywords in texture_keywords.items():
            if texture_type in found_textures:
                continue  # Уже найдена текстура этого типа
            
            for i, keyword in enumerate(keywords):
                if keyword in texture_basename:
                    # Более точные совпадения имеют приоритет
                    current_priority = len(keyword)
                    if current_priority > keyword_priority:
                        texture_type_found = texture_type
                        matched_keyword = keyword
                        keyword_priority = current_priority
                        print(f"DEBUG: Найдено ключевое слово '{keyword}' -> тип '{texture_type}' в '{texture_basename}' (приоритет: {current_priority})")
        
        # Добавляем текстуру, если найден тип
        if texture_type_found and texture_type_found not in found_textures:
            if matches_base or len(search_bases) == 0:
                found_textures[texture_type_found] = texture_file
                print(f"DEBUG: ✓ Назначена текстура {texture_type_found}: {texture_basename} (база: {matched_base}, ключевое слово: {matched_keyword})")
            else:
                print(f"DEBUG: Пропущена текстура {texture_basename} (не соответствует базовому имени)")
    
    # Если ничего не найдено, пробуем более агрессивный поиск
    if not found_textures:
        print("DEBUG: Первичный поиск не дал результатов, пробуем агрессивный поиск")
        
        # Ищем текстуры только по ключевым словам, игнорируя базовые имена
        for texture_file in texture_files:
            texture_basename = os.path.basename(texture_file).lower()
            
            for texture_type, keywords in texture_keywords.items():
                if texture_type in found_textures:
                    continue
                    
                for keyword in keywords:
                    if keyword in texture_basename:
                        found_textures[texture_type] = texture_file
                        print(f"DEBUG: Агрессивный поиск - назначена текстура {texture_type}: {texture_basename}")
                        break
                        
                if texture_type in found_textures:
                    break
    
    # Fallback: если ничего не найдено, берем первую текстуру как BaseMap
    if not found_textures and texture_files:
        found_textures["BaseMap"] = texture_files[0]
        print(f"DEBUG: Fallback - используем первую текстуру как BaseMap: {os.path.basename(texture_files[0])}")
    
    print(f"DEBUG: Итого найдено текстур: {len(found_textures)}")
    for tex_type, tex_path in found_textures.items():
        print(f"DEBUG: {tex_type}: {os.path.basename(tex_path)}")
    
    return found_textures


def create_material_universal(matnet_node, material_name, texture_maps, material_type="principledshader", logger=None):
    """
    ИСПРАВЛЕННАЯ универсальная функция создания материалов
    """
    
    if material_type == "materialx":
        return create_materialx_shader_fixed_v2(matnet_node, material_name, texture_maps, logger)
    else:
        return create_principled_shader(matnet_node, material_name, texture_maps, material_type, logger)


def create_materialx_shader_fixed_v2(matnet_node, material_name, texture_maps, logger=None):
    """
    ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ функция создания MaterialX материала
    """
    
    def log_debug(message):
        if logger:
            logger.log_debug(message)
        else:
            print(f"DEBUG MaterialX: {message}")
    
    def log_error(message):
        if logger:
            logger.log_error(message)
        else:
            print(f"ERROR MaterialX: {message}")
    
    if not matnet_node or not material_name:
        log_error("Некорректные параметры для создания MaterialX материала")
        return None
    
    # Очищаем имя материала
    safe_name = clean_node_name(material_name)
    if not safe_name or safe_name.isdigit():
        safe_name = f"mtlx_{hash(material_name) % 10000:04d}"
    
    # Создаем уникальное имя
    safe_name = _ensure_unique_material_name(matnet_node, safe_name)
    
    log_debug(f"Создание MaterialX материала: {safe_name}")
    if texture_maps:
        log_debug(f"С текстурами:")
        udim_count = 0
        for tex_type, tex_path in texture_maps.items():
            if UDIM_SUPPORT and is_udim_texture(tex_path):
                log_debug(f"  {tex_type}: {os.path.basename(tex_path)} (UDIM)")
                udim_count += 1
            else:
                log_debug(f"  {tex_type}: {os.path.basename(tex_path)}")
        
        if udim_count > 0:
            log_debug(f"Всего UDIM текстур: {udim_count} из {len(texture_maps)}")
    
def generate_python_sop_code(model_file, folder_path, texture_files, matnet_path, texture_keywords, material_cache, material_type="principledshader"):
    """Генерирует Python-код для SOP с полной поддержкой UDIM и MaterialX"""
    
    # Проверяем наличие UDIM текстур для добавления в комментарии
    udim_note = ""
    if UDIM_SUPPORT:
        try:
            udim_stats = get_udim_statistics(texture_files)
            if udim_stats['udim_sequences'] > 0:
                udim_note = f"# UDIM поддержка: {udim_stats['udim_sequences']} последовательностей, {udim_stats['udim_tiles']} тайлов\n"
        except:
            pass
    
    # Добавляем поддержку MaterialX
    materialx_note = ""
    if material_type == "materialx":
        materialx_note = "# MaterialX Solaris поддержка включена\n"
    
    # Безопасная нормализация путей
    model_file_fixed = os.path.normpath(model_file).replace(os.sep, "/")
    folder_path_fixed = os.path.normpath(folder_path).replace(os.sep, "/")
    matnet_path_fixed = os.path.normpath(matnet_path).replace(os.sep, "/")
    model_basename = os.path.basename(model_file)
    
    # Исправляем пути в списке текстур
    texture_files_fixed = []
    for path in texture_files:
        try:
            normalized_path = os.path.normpath(path).replace(os.sep, "/")
            texture_files_fixed.append(normalized_path)
        except Exception as e:
            print(f"WARNING: Не удалось нормализовать путь текстуры {path}: {e}")
    
    # Преобразуем данные в строки для вставки в код
    texture_files_str = repr(texture_files_fixed)
    texture_keywords_str = repr(texture_keywords)
    material_cache_str = repr(material_cache)
    material_type_str = repr(material_type)
    
    # Формируем код с полной поддержкой UDIM и MaterialX
    python_code = f'''
{udim_note}{materialx_note}import hou
import os
import re
from collections import defaultdict

def clean_node_name(name):
    """Очищает имя узла от недопустимых символов"""
    if not name:
        return "default_node"
    
    name = str(name).strip()
    cleaned_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    if cleaned_name and cleaned_name[0].isdigit():
        cleaned_name = 'n_' + cleaned_name
    
    if len(cleaned_name) > 30:
        cleaned_name = cleaned_name[:30]
    
    while '__' in cleaned_name:
        cleaned_name = cleaned_name.replace('__', '_')
    
    cleaned_name = cleaned_name.strip('_')
    
    if not cleaned_name or len(cleaned_name) < 2:
        cleaned_name = "default_node"
    
    if cleaned_name.isdigit():
        cleaned_name = f"node_{{cleaned_name}}"
    
    return cleaned_name

def create_materialx_shader_sop(matnet_node, material_name, texture_maps):
    """Создает MaterialX материал в Python SOP"""
    safe_name = clean_node_name(material_name)
    if not safe_name or safe_name.isdigit():
        safe_name = f"mtlx_{{hash(material_name) % 10000:04d}}"
    
    counter = 1
    original_name = safe_name
    while matnet_node.node(safe_name) is not None:
        safe_name = f"{{original_name}}_{{counter}}"
        counter += 1
    
    try:
        # Создаем MaterialX материал
        materialx_types = ["materialx", "usdpreviewsurface", "standardsurface"]
        material = None
        
        for mx_type in materialx_types:
            try:
                material = matnet_node.createNode(mx_type, safe_name)
                if material:
                    print(f"DEBUG SOP: Создан MaterialX материал типа {{mx_type}}")
                    break
            except:
                continue
        
        if not material:
            # Fallback на обычный материал
            material = matnet_node.createNode("material", safe_name)
        
        # Назначаем текстуры для MaterialX
        if material and texture_maps:
            materialx_assignments = {{
                "BaseMap": [("base_color", None), ("diffuse_color", None), ("basecolor", None)],
                "Normal": [("normal", None), ("normalmap", None), ("normal_map", None)],
                "Roughness": [("specular_roughness", None), ("roughness", None)],
                "Metallic": [("metalness", None), ("metallic", None)],
                "AO": [("diffuse_roughness", None), ("ao", None)],
                "Emissive": [("emission_color", None), ("emission", None)],
                "Opacity": [("opacity", None), ("alpha", None)]
            }}
            
            for tex_type, tex_path in texture_maps.items():
                if tex_type in materialx_assignments:
                    for param_name, _ in materialx_assignments[tex_type]:
                        if material.parm(param_name):
                            material.parm(param_name).set(tex_path)
                            print(f"DEBUG SOP: MaterialX {{tex_type}} установлен через {{param_name}}")
                            break
        
        return material
        
    except Exception as e:
        print(f"ERROR SOP: Ошибка создания MaterialX материала: {{e}}")
        return None

def detect_udim_sequences_full(texture_files):
    """Полная UDIM детекция для Python SOP"""
    udim_pattern = re.compile(r'^(.+)[._](\\d{{4}})\\.(jpg|jpeg|png|tga|tif|tiff|exr|hdr|pic|rat)$', re.IGNORECASE)
    udim_groups = defaultdict(list)
    single_textures = []
    
    print(f"DEBUG SOP: Анализируем {{len(texture_files)}} файлов на UDIM")
    
    for texture_file in texture_files:
        filename = os.path.basename(texture_file)
        match = udim_pattern.match(filename)
        
        if match:
            base_name = match.group(1)
            udim_number = int(match.group(2))
            extension = match.group(3)
            
            if 1001 <= udim_number <= 1100:
                udim_groups[base_name].append({{
                    'file': texture_file,
                    'udim': udim_number,
                    'extension': extension
                }})
                print(f"DEBUG SOP: UDIM тайл: {{filename}} -> {{base_name}}.{{udim_number}}")
            else:
                single_textures.append(texture_file)
        else:
            single_textures.append(texture_file)
    
    # Создаем UDIM последовательности
    udim_sequences = {{}}
    for base_name, tiles in udim_groups.items():
        if len(tiles) >= 2:  # Минимум 2 тайла для UDIM
            tiles.sort(key=lambda x: x['udim'])
            first_tile = tiles[0]
            directory = os.path.dirname(first_tile['file'])
            extension = first_tile['extension']
            udim_pattern_path = os.path.join(directory, f"{{base_name}}.<UDIM>.{{extension}}")
            udim_pattern_path = os.path.normpath(udim_pattern_path).replace(os.sep, "/")
            
            udim_sequences[base_name] = {{
                'pattern': udim_pattern_path,
                'tiles': [tile['udim'] for tile in tiles],
                'tile_count': len(tiles)
            }}
            print(f"DEBUG SOP: UDIM последовательность '{{base_name}}': {{len(tiles)}} тайлов ({{min([t['udim'] for t in tiles])}}-{{max([t['udim'] for t in tiles])}})")
        else:
            for tile in tiles:
                single_textures.append(tile['file'])
    
    print(f"DEBUG SOP: Найдено {{len(udim_sequences)}} UDIM последовательностей и {{len(single_textures)}} одиночных текстур")
    return udim_sequences, single_textures

def find_matching_textures_full_udim(material_name, texture_files, texture_keywords, model_basename):
    """Полная функция поиска текстур с расширенной UDIM поддержкой"""
    found_textures = {{}}
    
    if not material_name or not texture_files:
        return found_textures
    
    print(f"DEBUG SOP: Поиск текстур для материала '{{material_name}}' ({{len(texture_files)}} файлов)")
    
    # Проверяем на UDIM
    udim_sequences, single_textures = detect_udim_sequences_full(texture_files)
    
    # Создаем список всех кандидатов
    all_candidates = []
    
    # Добавляем UDIM паттерны
    for base_name, udim_info in udim_sequences.items():
        all_candidates.append({{
            'path': udim_info['pattern'],
            'name': base_name,
            'type': 'udim',
            'tile_count': udim_info['tile_count']
        }})
    
    # Добавляем одиночные текстуры
    for texture_file in single_textures:
        filename = os.path.splitext(os.path.basename(texture_file))[0]
        all_candidates.append({{
            'path': texture_file,
            'name': filename,
            'type': 'single'
        }})
    
    print(f"DEBUG SOP: Всего кандидатов: {{len(all_candidates)}} ({{len(udim_sequences)}} UDIM + {{len(single_textures)}} одиночных)")
    
    # Если только один кандидат, используем как BaseMap
    if len(all_candidates) == 1:
        found_textures["BaseMap"] = all_candidates[0]['path']
        candidate_type = "UDIM" if all_candidates[0]['type'] == 'udim' else "обычная"
        print(f"DEBUG SOP: Единственная {{candidate_type}} текстура назначена как BaseMap")
        return found_textures
    
    # Подготавливаем базовые имена для поиска
    material_name_lower = material_name.lower().replace(" ", "_")
    model_name_lower = os.path.splitext(model_basename)[0].lower() if model_basename else ""
    
    search_bases = []
    if material_name_lower:
        search_bases.append(material_name_lower)
        material_parts = re.split(r"[_\\-\\s.]+", material_name_lower)
        search_bases.extend([part for part in material_parts if len(part) > 2])
    
    if model_name_lower:
        search_bases.append(model_name_lower)
        model_parts = re.split(r"[_\\-\\s.]+", model_name_lower)
        search_bases.extend([part for part in model_parts if len(part) > 2])
    
    # Удаляем дубликаты
    search_bases = list(set(search_bases))
    print(f"DEBUG SOP: Базовые имена для поиска: {{search_bases}}")
    
    # Основной поиск с приоритетом точности
    for candidate in all_candidates:
        candidate_name_lower = candidate['name'].lower()
        candidate_path = candidate['path']
        candidate_type = candidate['type']
        
        print(f"DEBUG SOP: Анализируем кандидата: {{candidate['name']}} ({{candidate_type}})")
        
        # Проверяем соответствие базовым именам
        matches_base = False
        matched_base = ""
        for base in search_bases:
            if base in candidate_name_lower:
                matches_base = True
                matched_base = base
                print(f"DEBUG SOP: Соответствие базовому имени '{{base}}'")
                break
        
        # Определяем тип текстуры по ключевым словам с приоритетом
        texture_type_found = None
        matched_keyword = ""
        keyword_priority = 0
        
        for texture_type, keywords in texture_keywords.items():
            if texture_type in found_textures:
                continue
                
            for keyword in keywords:
                if keyword in candidate_name_lower:
                    # Более точные совпадения имеют приоритет
                    current_priority = len(keyword)
                    if current_priority > keyword_priority:
                        texture_type_found = texture_type
                        matched_keyword = keyword
                        keyword_priority = current_priority
                        print(f"DEBUG SOP: Ключевое слово '{{keyword}}' -> {{texture_type}} (приоритет: {{current_priority}})")
        
        # Добавляем текстуру
        if texture_type_found and texture_type_found not in found_textures:
            if matches_base or len(search_bases) == 0:
                found_textures[texture_type_found] = candidate_path
                udim_label = f" (UDIM, {{candidate.get('tile_count', 0)}} тайлов)" if candidate_type == 'udim' else ""
                print(f"DEBUG SOP: ✓ Назначена {{texture_type_found}}: {{candidate['name']}}{{udim_label}}")
    
    # Агрессивный поиск, если ничего не найдено
    if not found_textures:
        print("DEBUG SOP: Агрессивный поиск по ключевым словам")
        for candidate in all_candidates:
            candidate_name_lower = candidate['name'].lower()
            for texture_type, keywords in texture_keywords.items():
                if texture_type in found_textures:
                    continue
                for keyword in keywords:
                    if keyword in candidate_name_lower:
                        found_textures[texture_type] = candidate['path']
                        udim_label = " (UDIM)" if candidate['type'] == 'udim' else ""
                        print(f"DEBUG SOP: Агрессивный поиск - {{texture_type}}: {{candidate['name']}}{{udim_label}}")
                        break
                if texture_type in found_textures:
                    break
    
    # Fallback
    if not found_textures and all_candidates:
        found_textures["BaseMap"] = all_candidates[0]['path']
        udim_label = " (UDIM)" if all_candidates[0]['type'] == 'udim' else ""
        print(f"DEBUG SOP: Fallback BaseMap: {{all_candidates[0]['name']}}{{udim_label}}")
    
    print(f"DEBUG SOP: Итого найдено {{len(found_textures)}} текстур")
    return found_textures

def create_material_with_type_support_sop(matnet_node, material_name, texture_maps, material_type):
    """Создаёт материал с поддержкой MaterialX в Python SOP"""
    print(f"DEBUG SOP: === СОЗДАНИЕ МАТЕРИАЛА ТИПА {{material_type}} ===")
    print(f"DEBUG SOP: Имя материала: {{material_name}}")
    print(f"DEBUG SOP: Количество текстур: {{len(texture_maps)}}")
    
    if material_type == "materialx":
        return create_materialx_shader_sop(matnet_node, material_name, texture_maps)
    
    # Обычные материалы
    safe_name = clean_node_name(material_name)
    if not safe_name or safe_name.isdigit():
        safe_name = f"mat_{{hash(material_name) % 10000:04d}}"
    
    # Обеспечиваем уникальность имени
    counter = 1
    original_name = safe_name
    while matnet_node.node(safe_name) is not None:
        safe_name = f"{{original_name}}_{{counter}}"
        counter += 1
    
    print(f"DEBUG SOP: Создаем материал: {{safe_name}}")
    
    # Создаём материал
    material = None
    shader_types = []
    if material_type == "principledshader":
        shader_types = ["principledshader", "principledshader::2.0", "material"]
    elif material_type == "redshift::Material":
        shader_types = ["redshift::Material", "principledshader", "material"]
    else:
        shader_types = ["material", "principledshader"]
    
    for shader_type in shader_types:
        try:
            material = matnet_node.createNode(shader_type, safe_name)
            print(f"DEBUG SOP: Создан материал типа {{shader_type}}")
            break
        except:
            continue
    
    if not material:
        try:
            material = matnet_node.createNode("material", f"fallback_{{hash(material_name) % 10000:04d}}")
        except:
            print(f"ERROR SOP: Не удалось создать материал")
            return None
    
    # Устанавливаем базовый цвет
    try:
        if material.parmTuple("basecolor"):
            material.parmTuple("basecolor").set((1.0, 1.0, 1.0))
            print("DEBUG SOP: Установлен базовый цвет (1,1,1)")
    except:
        pass
    
    # Полное назначение текстур с расширенной поддержкой UDIM
    texture_assignments = {{
        "BaseMap": [
            ("basecolor_useTexture", "basecolor_texture"),
            ("diffuse_useTexture", "diffuse_texture"), 
            ("diffuse_texture", None),
            ("tex0", None),
            ("colorMap", None)
        ],
        "Normal": [
            ("baseBumpAndNormal_enable", None),
            ("baseNormal_useTexture", "baseNormal_texture"),
            ("normal_map_enable", "normal_texture"),
            ("normal_texture", None),
            ("normalMap", None)
        ],
        "Roughness": [
            ("rough_useTexture", "rough_texture"),
            ("roughness_map_enable", "roughness_texture"),
            ("roughness_texture", None),
            ("rough_texture", None),
            ("roughnessMap", None)
        ],
        "Metallic": [
            ("metallic_useTexture", "metallic_texture"),
            ("metalness_map_enable", "metalness_texture"),
            ("metallic_texture", None),
            ("metalness_texture", None),
            ("metal_texture", None),
            ("metallicMap", None)
        ],
        "AO": [
            ("baseAO_enable", "baseAO_texture"),
            ("ao_useTexture", "ao_texture"),
            ("occlusion_useTexture", "occlusion_texture"),
            ("ao_texture", None),
            ("occlusion_texture", None),
            ("aoMap", None)
        ],
        "Emissive": [
            ("emissive_useTexture", "emissive_texture"),
            ("emission_texture", None),
            ("emissive_texture", None),
            ("emissionMap", None)
        ],
        "Opacity": [
            ("opac_useTexture", "opac_texture"),
            ("opacity_texture", None),
            ("alpha_texture", None),
            ("alphaMap", None)
        ],
        "Height": [
            ("dispTex_enable", "dispTex_texture"),
            ("displacement_texture", None),
            ("height_texture", None),
            ("heightMap", None)
        ],
        "Bump": [
            ("bump_input", "bump_map"),
            ("bump_texture", None),
            ("bumpmap", None)
        ],
        "Specular": [
            ("reflect_useTexture", "reflect_texture"),
            ("specular_texture", None),
            ("specularMap", None)
        ],
        "Translucency": [
            ("translucent_useTexture", "translucent_texture"),
            ("subsurface_texture", None),
            ("sss_texture", None)
        ]
    }}
    
    successful_textures = 0
    failed_textures = []
    
    for texture_type, texture_path in texture_maps.items():
        if texture_type in texture_assignments:
            success = False
            is_udim = '<UDIM>' in texture_path
            
            for enable_param, texture_param in texture_assignments[texture_type]:
                try:
                    # Специальная обработка для некоторых параметров
                    if enable_param == "baseBumpAndNormal_enable":
                        if material.parm(enable_param):
                            material.parm(enable_param).set(True)
                            print(f"DEBUG SOP: Активирован {{enable_param}}")
                        continue
                    elif enable_param == "bump_input":
                        if material.parm(enable_param):
                            material.parm(enable_param).set(1)
                            print(f"DEBUG SOP: Установлен bump_input = 1")
                        if texture_param and material.parm(texture_param):
                            material.parm(texture_param).set(texture_path)
                            success = True
                            break
                        continue
                    
                    # Активируем параметр включения
                    if enable_param and material.parm(enable_param):
                        try:
                            parm_template = material.parm(enable_param).parmTemplate()
                            if hasattr(parm_template, 'type') and 'Toggle' in str(parm_template.type()):
                                material.parm(enable_param).set(True)
                                print(f"DEBUG SOP: Активирован {{enable_param}}")
                            elif texture_param is None:
                                material.parm(enable_param).set(texture_path)
                                success = True
                                break
                        except:
                            pass
                    
                    # Устанавливаем текстуру
                    if texture_param and material.parm(texture_param):
                        material.parm(texture_param).set(texture_path)
                        success = True
                        print(f"DEBUG SOP: Установлена {{texture_type}} через {{texture_param}}")
                        break
                    elif texture_param is None and enable_param and material.parm(enable_param):
                        material.parm(enable_param).set(texture_path)
                        success = True
                        print(f"DEBUG SOP: Установлена {{texture_type}} через {{enable_param}}")
                        break
                        
                except Exception as e:
                    print(f"DEBUG SOP: Ошибка {{enable_param}}/{{texture_param}}: {{e}}")
                    continue
            
            if success:
                udim_label = " (UDIM)" if is_udim else ""
                print(f"DEBUG SOP: ✓ Успешно назначена {{texture_type}}: {{os.path.basename(texture_path)}}{{udim_label}}")
                successful_textures += 1
            else:
                failed_textures.append((texture_type, texture_path))
                udim_label = " (UDIM)" if is_udim else ""
                print(f"DEBUG SOP: ✗ Не удалось назначить {{texture_type}}: {{os.path.basename(texture_path)}}{{udim_label}}")
        else:
            print(f"DEBUG SOP: Неизвестный тип текстуры: {{texture_type}}")
    
    print(f"DEBUG SOP: Успешно назначено {{successful_textures}} из {{len(texture_maps)}} текстур")
    
    if failed_textures:
        print(f"DEBUG SOP: Не удалось назначить {{len(failed_textures)}} текстур")
    
    try:
        material.moveToGoodPosition()
    except:
        pass
    
    return material

def main():
    node = hou.pwd()
    geo = node.geometry()
    
    # Получаем переданные данные
    model_file = "{model_file_fixed}"
    folder_path = "{folder_path_fixed}"
    model_basename = os.path.basename(model_file)
    
    texture_files = {texture_files_str}
    texture_keywords = {texture_keywords_str}
    material_cache = {material_cache_str}
    material_type = {material_type_str}
    
    matnet_path = "{matnet_path_fixed}"
    matnet_node = hou.node(matnet_path)
    if not matnet_node:
        print("ERROR SOP: Не удалось найти matnet!")
        return
    
    print(f"DEBUG SOP: Обработка модели: {{model_basename}}")
    print(f"DEBUG SOP: Тип материала: {{material_type}}")
    print(f"DEBUG SOP: Доступно текстур: {{len(texture_files)}}")
    
    # Поиск и создание атрибута материала
    mat_attr = None
    for attr_name in ["shop_materialpath", "material", "mat", "materialpath"]:
        mat_attr = geo.findPrimAttrib(attr_name)
        if mat_attr:
            print(f"DEBUG SOP: Найден атрибут материала: {{attr_name}}")
            break
    
    if not mat_attr:
        print("DEBUG SOP: Создаем новый атрибут shop_materialpath")
        geo.addAttrib(hou.attribType.Prim, "shop_materialpath", "")
        mat_attr = geo.findPrimAttrib("shop_materialpath")
    
    # Собираем уникальные материалы
    material_values = set()
    for prim in geo.prims():
        val = prim.attribValue(mat_attr)
        if isinstance(val, str) and val:
            material_values.add(val)
    
    print(f"DEBUG SOP: Найдено {{len(material_values)}} уникальных материалов в геометрии")
    
    # Если нет материалов, создаем по умолчанию
    if not material_values:
        default_mat_name = os.path.splitext(model_basename)[0]
        material_values.add(default_mat_name)
        print(f"DEBUG SOP: Создан материал по умолчанию: {{default_mat_name}}")
    
    material_mapping = {{}}
    
    # Создаём материалы с полным UDIM поиском и поддержкой MaterialX
    for mat_path in material_values:
        mat_name = os.path.basename(mat_path) if "/" in mat_path else mat_path
        
        print(f"DEBUG SOP: Обработка материала: {{mat_name}}")
        
        if mat_name in material_cache:
            material_mapping[mat_path] = material_cache[mat_name]
            print(f"DEBUG SOP: Используем кэшированный материал")
            continue
        
        # Полный поиск текстур с UDIM
        found_textures = find_matching_textures_full_udim(mat_name, texture_files, texture_keywords, model_basename)
        
        # Создаём материал с поддержкой MaterialX
        material = create_material_with_type_support_sop(matnet_node, mat_name, found_textures, material_type)
        if material:
            material_mapping[mat_path] = material.path()
            material_cache[mat_name] = material.path()
            print(f"DEBUG SOP: Создан материал {{material_type}}: {{material.path()}}")
        else:
            print(f"ERROR SOP: Не удалось создать материал для {{mat_name}}")
    
    # Назначаем материалы примитивам
    if material_mapping:
        default_material_path = list(material_mapping.values())[0]
        count = 0
        for prim in geo.prims():
            old_mat_path = prim.attribValue(mat_attr)
            if old_mat_path in material_mapping:
                prim.setAttribValue(mat_attr, material_mapping[old_mat_path])
            else:
                prim.setAttribValue(mat_attr, default_material_path)
            count += 1
        
        print(f"DEBUG SOP: Материалы назначены {{count}} примитивам")
    
    print(f"DEBUG SOP: Обработка завершена. Создано {{len(material_mapping)}} материалов типа {{material_type}}")

main()
'''
        # ИСПРАВЛЕНИЕ: Создаем MaterialX материалы правильно
def _create_materialx_surface(matnet_node, safe_name, log_debug, log_error):
    """Создает MaterialX поверхность"""
    
    # Пробуем разные типы MaterialX поверхностей
    surface_types = [
        "mtlxstandardsurface",
        "usdpreviewsurface", 
        "standardsurface",
        "principled_bsdf"
    ]
    
    surface_name = f"{safe_name}_surface"
    
    for surface_type in surface_types:
        try:
            surface = matnet_node.createNode(surface_type, surface_name)
            if surface:
                log_debug(f"Создана MaterialX поверхность типа: {surface_type}")
                return surface
        except Exception as e:
            log_debug(f"Не удалось создать {surface_type}: {e}")
            continue
    
    log_error("Не удалось создать MaterialX поверхность любого типа")
    return None


def _create_materialx_image_node(matnet_node, safe_name, tex_type, tex_path, log_debug, log_error):
    """Создает MaterialX image ноду"""
    
    try:
        # Создаем уникальное имя для image ноды
        safe_texture_type = clean_node_name(tex_type.lower())
        image_name = f"{safe_name}_{safe_texture_type}_img"
        
        # Создаем mtlximage ноду
        image_node = matnet_node.createNode("mtlximage", image_name)
        if not image_node:
            log_error(f"Не удалось создать mtlximage для {tex_type}")
            return None
        
        # Настраиваем image ноду
        if image_node.parm("file"):
            image_node.parm("file").set(tex_path)
        
        # Специальные настройки для разных типов текстур
        if tex_type == "Normal":
            # Для нормалей устанавливаем правильный signature
            if image_node.parm("signature"):
                try:
                    image_node.parm("signature").set("vector3")
                except:
                    pass
        elif tex_type in ["Roughness", "Metallic", "AO", "Height", "Opacity"]:
            # Для односложных текстур устанавливаем float signature
            if image_node.parm("signature"):
                try:
                    image_node.parm("signature").set("float")
                except:
                    pass
        elif tex_type in ["BaseMap", "Emissive"]:
            # Для цветных текстур
            if image_node.parm("signature"):
                try:
                    image_node.parm("signature").set("color3")
                except:
                    pass
        
        is_udim = UDIM_SUPPORT and is_udim_texture(tex_path)
        udim_label = " (UDIM)" if is_udim else ""
        log_debug(f"Создана MaterialX image нода для {tex_type}: {image_name}{udim_label}")
        
        return image_node
        
    except Exception as e:
        log_error(f"Ошибка создания MaterialX image ноды для {tex_type}: {e}")
def _arrange_materialx_nodes(created_nodes, log_debug):
    """Размещает MaterialX ноды в network editor"""
    try:
        if 'surface' not in created_nodes:
            return
        
        surface_node = created_nodes['surface']
        surface_node.moveToGoodPosition()
        surface_pos = surface_node.position()
        
        # Размещаем image ноды слева от поверхности
        image_nodes = [node for key, node in created_nodes.items() if key.startswith('image_')]
        
        for i, image_node in enumerate(image_nodes):
            try:
                # Размещаем image ноды в колонку слева
                new_pos = hou.Vector2(surface_pos.x() - 3, surface_pos.y() + (i - len(image_nodes)/2) * 1.5)
                image_node.setPosition(new_pos)
            except Exception as e:
                log_debug(f"Не удалось разместить {image_node.name()}: {e}")
                image_node.moveToGoodPosition()
        
        # Размещаем material wrapper справа
        if 'material' in created_nodes:
            material_wrapper = created_nodes['material']
            wrapper_pos = hou.Vector2(surface_pos.x() + 3, surface_pos.y())
            material_wrapper.setPosition(wrapper_pos)
        
        log_debug("MaterialX ноды размещены в network editor")
        
    except Exception as e:
        log_debug(f"Ошибка размещения MaterialX нод: {e}")


def create_principled_shader(matnet_node, material_name, texture_maps, material_type="principledshader", logger=None):
    """Создаёт Principled материал с полной поддержкой UDIM текстур"""
    
    def log_debug(message):
        if logger:
            logger.log_debug(message)
        else:
            print(f"DEBUG Principled: {message}")
    
    def log_error(message):
        if logger:
            logger.log_error(message)
        else:
            print(f"ERROR Principled: {message}")
    
    if not matnet_node or not material_name:
        log_error("Некорректные параметры для создания материала")
        return None
    
    # Очищаем имя материала
    safe_name = clean_node_name(material_name)
    if not safe_name or safe_name.isdigit():
        safe_name = f"mat_{hash(material_name) % 10000:04d}"
    
    # Создаем уникальное имя
    safe_name = _ensure_unique_material_name(matnet_node, safe_name)
    
    log_debug(f"Создаем Principled материал: {safe_name}")
    if texture_maps:
        log_debug(f"С текстурами:")
        udim_count = 0
        for tex_type, tex_path in texture_maps.items():
            if UDIM_SUPPORT and is_udim_texture(tex_path):
                log_debug(f"  {tex_type}: {os.path.basename(tex_path)} (UDIM)")
                udim_count += 1
            else:
                log_debug(f"  {tex_type}: {os.path.basename(tex_path)}")
        
        if udim_count > 0:
            log_debug(f"Всего UDIM текстур: {udim_count} из {len(texture_maps)}")
    
    # Создаём материал
    material = _create_material_node(matnet_node, safe_name, material_type, log_debug, log_error)
    if not material:
        log_error(f"Не удалось создать материал {safe_name}")
        return None
    
    # Настраиваем материал с полной поддержкой UDIM
    _configure_principled_material(material, texture_maps, log_debug, log_error)
    
    try:
        material.moveToGoodPosition()
    except Exception as e:
        log_debug(f"Не удалось переместить материал: {e}")
    
    return material


def _create_material_node(matnet_node, safe_name, material_type, log_debug, log_error):
    """Создает узел материала с поддержкой различных типов"""
    shader_types = []
    
    if material_type == "principledshader":
        shader_types = ["principledshader", "principledshader::2.0", "material"]
    elif material_type == "redshift::Material":
        shader_types = ["redshift::Material", "principledshader", "material"]
    else:
        shader_types = ["material", "principledshader"]
    
    for shader_type in shader_types:
        try:
            material = matnet_node.createNode(shader_type, safe_name)
            log_debug(f"Создан материал типа {shader_type}: {material.path()}")
            return material
        except Exception as e:
            log_debug(f"Не удалось создать материал типа {shader_type}: {e}")
            continue
    
    log_error("Не удалось создать материал любого типа")
    return None


def _configure_principled_material(material, texture_maps, log_debug, log_error):
    """Полная настройка Principled материала"""
    if not material or not texture_maps:
        return
    
    log_debug(f"Настройка Principled материала {material.name()} с {len(texture_maps)} текстурами")
    
    # Устанавливаем базовый цвет белый для корректной работы с текстурами
    try:
        if material.parmTuple("basecolor"):
            material.parmTuple("basecolor").set((1.0, 1.0, 1.0))
            log_debug("Установлен базовый цвет (1,1,1)")
    except Exception as e:
        log_debug(f"Не удалось установить базовый цвет: {e}")
    
    # Назначаем текстуры
    texture_assignments = {
        "BaseMap": [
            ("basecolor_useTexture", "basecolor_texture"),
            ("diffuse_useTexture", "diffuse_texture"), 
            ("diffuse_texture", None),
            ("tex0", None),
            ("colorMap", None)
        ],
        "Normal": [
            ("baseBumpAndNormal_enable", None),
            ("baseNormal_useTexture", "baseNormal_texture"),
            ("normal_map_enable", "normal_texture"),
            ("normal_texture", None),
            ("normalMap", None)
        ],
        "Roughness": [
            ("rough_useTexture", "rough_texture"),
            ("roughness_map_enable", "roughness_texture"),
            ("roughness_texture", None),
            ("rough_texture", None),
            ("roughnessMap", None)
        ],
        "Metallic": [
            ("metallic_useTexture", "metallic_texture"),
            ("metalness_map_enable", "metalness_texture"),
            ("metallic_texture", None),
            ("metalness_texture", None),
            ("metal_texture", None),
            ("metallicMap", None)
        ],
        "AO": [
            ("baseAO_enable", "baseAO_texture"),
            ("ao_useTexture", "ao_texture"),
            ("occlusion_useTexture", "occlusion_texture"),
            ("ao_texture", None),
            ("occlusion_texture", None),
            ("aoMap", None)
        ],
        "Emissive": [
            ("emissive_useTexture", "emissive_texture"),
            ("emission_texture", None),
            ("emissive_texture", None),
            ("emissionMap", None)
        ],
        "Opacity": [
            ("opac_useTexture", "opac_texture"),
            ("opacity_texture", None),
            ("alpha_texture", None),
            ("alphaMap", None)
        ],
        "Height": [
            ("dispTex_enable", "dispTex_texture"),
            ("displacement_texture", None),
            ("height_texture", None),
            ("heightMap", None)
        ],
        "Specular": [
            ("reflect_useTexture", "reflect_texture"),
            ("specular_texture", None),
            ("specularMap", None)
        ]
    }
    
    successful_textures = 0
    failed_textures = []
    
    for texture_type, texture_path in texture_maps.items():
        if texture_type in texture_assignments:
            success = False
            is_udim = UDIM_SUPPORT and is_udim_texture(texture_path)
            
            for enable_param, texture_param in texture_assignments[texture_type]:
                try:
                    # Специальная обработка для некоторых параметров
                    if enable_param == "baseBumpAndNormal_enable":
                        if material.parm(enable_param):
                            material.parm(enable_param).set(True)
                            log_debug(f"Активирован {enable_param}")
                        continue
                    
                    # Активируем параметр включения
                    if enable_param and material.parm(enable_param):
                        try:
                            parm_template = material.parm(enable_param).parmTemplate()
                            if hasattr(parm_template, 'type') and 'Toggle' in str(parm_template.type()):
                                material.parm(enable_param).set(True)
                                log_debug(f"Активирован {enable_param}")
                            elif texture_param is None:
                                material.parm(enable_param).set(texture_path)
                                success = True
                                break
                        except:
                            pass
                    
                    # Устанавливаем текстуру
                    if texture_param and material.parm(texture_param):
                        material.parm(texture_param).set(texture_path)
                        success = True
                        log_debug(f"Установлена {texture_type} через {texture_param}")
                        break
                    elif texture_param is None and enable_param and material.parm(enable_param):
                        material.parm(enable_param).set(texture_path)
                        success = True
                        log_debug(f"Установлена {texture_type} через {enable_param}")
                        break
                        
                except Exception as e:
                    log_debug(f"Ошибка {enable_param}/{texture_param}: {e}")
                    continue
            
            if success:
                udim_label = " (UDIM)" if is_udim else ""
                log_debug(f"✓ Успешно назначена {texture_type}: {os.path.basename(texture_path)}{udim_label}")
                successful_textures += 1
            else:
                failed_textures.append((texture_type, texture_path))
                udim_label = " (UDIM)" if is_udim else ""
                log_debug(f"✗ Не удалось назначить {texture_type}: {os.path.basename(texture_path)}{udim_label}")
        else:
            log_debug(f"Неизвестный тип текстуры: {texture_type}")
    
    log_debug(f"Успешно назначено {successful_textures} из {len(texture_maps)} текстур")
    
    if failed_textures:
        log_debug(f"Не удалось назначить {len(failed_textures)} текстур")


def _ensure_unique_material_name(matnet_node, base_name):
    """Обеспечивает уникальность имени материала"""
    counter = 1
    original_name = base_name
    current_name = base_name
    
    while matnet_node.node(current_name) is not None:
        current_name = f"{original_name}_{counter}"
        counter += 1
        if counter > 1000:  # Защита от бесконечного цикла
            import time
            current_name = f"{original_name}_{int(time.time() % 10000)}"
            break
    
    return current_name


def get_texture_keywords():
    """Возвращает расширенный словарь ключевых слов для текстур"""
    return ENHANCED_TEXTURE_KEYWORDS.copy()


def validate_texture_path(texture_path):
    """Валидирует путь к текстуре, включая UDIM"""
    if not texture_path:
        return False, "Пустой путь к текстуре"
    
    # Проверяем UDIM
    if UDIM_SUPPORT and is_udim_texture(texture_path):
        try:
            from udim_utils import find_udim_tiles_from_pattern
            tiles = find_udim_tiles_from_pattern(texture_path)
            if not tiles:
                return False, f"UDIM паттерн указан, но тайлы не найдены: {texture_path}"
            return True, f"UDIM текстура с {len(tiles)} тайлами"
        except Exception as e:
            return False, f"Ошибка валидации UDIM: {e}"
    
    # Обычная валидация
    if not os.path.exists(texture_path):
        return False, f"Файл текстуры не существует: {texture_path}"
    
    if not os.path.isfile(texture_path):
        return False, f"Путь не указывает на файл: {texture_path}"
    
    return True, "Текстура валидна"


def get_material_stats(texture_maps):
    """Возвращает статистику по материалу"""
    if not texture_maps:
        return {"total": 0, "udim": 0, "regular": 0}
    
    udim_count = 0
    if UDIM_SUPPORT:
        udim_count = sum(1 for path in texture_maps.values() if is_udim_texture(path))
    
    return {
        "total": len(texture_maps),
        "udim": udim_count,
        "regular": len(texture_maps) - udim_count
    }


def print_material_info(material_name, texture_maps):
    """Выводит подробную информацию о материале"""
    stats = get_material_stats(texture_maps)
    
    print("=" * 50)
    print(f"ИНФОРМАЦИЯ О МАТЕРИАЛЕ: {material_name}")
    print("=" * 50)
    print(f"Всего текстур: {stats['total']}")
    print(f"UDIM текстур: {stats['udim']}")
    print(f"Обычных текстур: {stats['regular']}")
    print("")
    
    if texture_maps:
        print("Назначенные текстуры:")
        for tex_type, tex_path in texture_maps.items():
            if UDIM_SUPPORT and is_udim_texture(tex_path):
                try:
                    from udim_utils import find_udim_tiles_from_pattern
                    tiles = find_udim_tiles_from_pattern(tex_path)
                    tile_info = f" ({len(tiles)} тайлов)" if tiles else " (тайлы не найдены)"
                except:
                    tile_info = " (UDIM)"
                print(f"  {tex_type}: {os.path.basename(tex_path)}{tile_info}")
            else:
                print(f"  {tex_type}: {os.path.basename(tex_path)}")
    
    print("=" * 50)


# ========== ИСПРАВЛЕННЫЕ ФУНКЦИИ MATERIALX ==========

def _connect_materialx_nodes_fixed(surface_node, image_nodes, texture_maps, log_debug, log_error):
    """
    ИСПРАВЛЕННАЯ функция подключения MaterialX нод
    """
    
    log_debug(f"MaterialX: подключение {len(image_nodes)} image нод")
    
    # ИСПРАВЛЕНИЕ: Правильные карты подключений с учетом регистра и пробелов
    connection_maps = {
        "usdpreviewsurface": {
            "BaseMap": "Diffuse Color",      # ИСПРАВЛЕНО: с заглавными буквами и пробелом
            "Normal": "Normal", 
            "Roughness": "Roughness",
            "Metallic": "Metallic",
            "AO": "Occlusion",               # ИСПРАВЛЕНО: правильное имя параметра
            "Emissive": "Emissive Color",
            "Opacity": "Opacity"
        },
        "mtlxstandardsurface": {
            "BaseMap": "base_color",
            "Normal": "normal", 
            "Roughness": "specular_roughness",
            "Metallic": "metalness",
            "AO": "diffuse_roughness",
            "Emissive": "emission_color",
            "Opacity": "opacity",
            "Height": "displacement",
            "Specular": "specular"
        },
        # ДОБАВЛЕНО: Поддержка Karma Material
        "karmamaterial": {
            "BaseMap": "basecolor",
            "Normal": "baseNormal", 
            "Roughness": "rough",
            "Metallic": "metallic",
            "AO": "baseAO",
            "Emissive": "emitcolor",
            "Opacity": "opac",
            "Height": "dispTex",
            "Specular": "reflect"
        }
    }
    
    # Определяем тип поверхности
    surface_type = surface_node.type().name().lower()
    log_debug(f"Тип MaterialX поверхности: {surface_type}")
    
    # ИСПРАВЛЕНИЕ: Более точное определение типа материала
    if "usdpreview" in surface_type:
        connection_map = connection_maps["usdpreviewsurface"]
        log_debug("Используем карту подключений USD Preview Surface")
    elif "standardsurface" in surface_type or "mtlx" in surface_type:
        connection_map = connection_maps["mtlxstandardsurface"]
        log_debug("Используем карту подключений MaterialX Standard Surface")
    elif "karmamaterial" in surface_type:
        connection_map = connection_maps["karmamaterial"]
        log_debug("Используем карту подключений Karma Material")
    else:
        # Fallback на USD Preview Surface
        connection_map = connection_maps["usdpreviewsurface"]
        log_debug(f"Неизвестный тип поверхности {surface_type}, используем USD Preview Surface карту")
    
    connected_count = 0
    
    for texture_type, image_node in image_nodes.items():
        if texture_type in connection_map:
            surface_input = connection_map[texture_type]
            
            try:
                # ИСПРАВЛЕНИЕ: Используем улучшенный метод подключения
                success = _connect_materialx_nodes_properly_improved(image_node, surface_node, surface_input, log_debug, log_error)
                
                if success:
                    connected_count += 1
                    is_udim = '<UDIM>' in texture_maps.get(texture_type, '')
                    udim_label = " (UDIM)" if is_udim else ""
                    log_debug(f"✓ MaterialX подключено {texture_type} -> {surface_input}{udim_label}")
                else:
                    log_debug(f"✗ MaterialX не удалось подключить {texture_type}")
                    
            except Exception as e:
                log_error(f"Ошибка подключения MaterialX {texture_type}: {e}")
        else:
            log_debug(f"Тип текстуры {texture_type} не поддерживается для {surface_type}")
    
    log_debug(f"MaterialX подключено {connected_count} из {len(image_nodes)} image нод")


def _connect_materialx_nodes_properly_improved(source_node, target_node, target_input, log_debug, log_error):
    """
    УЛУЧШЕННОЕ подключение MaterialX нод с поддержкой разных типов
    """
    try:
        # СПОСОБ 1: Поиск параметра по точному имени
        target_parm = target_node.parm(target_input)
        if target_parm:
            try:
                # Для USD Preview Surface используем path к выходу
                source_output_path = f"{source_node.path()}/out"
                target_parm.set(source_output_path)
                log_debug(f"MaterialX подключено через параметр: {source_node.name()} -> {target_node.name()}.{target_input}")
                return True
            except Exception as e:
                log_debug(f"Подключение через параметр не сработало: {e}")
        
        # СПОСОБ 2: Поиск по индексу входа
        try:
            input_labels = target_node.inputLabels()
            log_debug(f"Доступные входы {target_node.name()}: {input_labels}")
            
            # Поиск точного совпадения
            target_input_index = -1
            for i, label in enumerate(input_labels):
                if label == target_input:  # Точное совпадение
                    target_input_index = i
                    break
            
            # Если не найдено точное совпадение, ищем по нижнему регистру
            if target_input_index == -1:
                target_input_lower = target_input.lower()
                for i, label in enumerate(input_labels):
                    if label.lower() == target_input_lower:
                        target_input_index = i
                        break
            
            if target_input_index >= 0:
                # Подключаем через setInput
                target_node.setInput(target_input_index, source_node, 0)
                log_debug(f"MaterialX подключено через setInput: {source_node.name()}[0] -> {target_node.name()}[{target_input_index}]")
                return True
            else:
                log_debug(f"Не найден вход '{target_input}' в доступных входах: {input_labels}")
        
        except Exception as e:
            log_debug(f"Подключение через setInput не сработало: {e}")
        
        # СПОСОБ 3: Прямое подключение через коннекторы (для новых версий Houdini)
        try:
            # Получаем output connector
            source_connectors = source_node.outputConnectors()
            if source_connectors:
                source_connector = source_connectors[0]  # Первый выход
                
                # Получаем input connector
                target_connectors = target_node.inputConnectors()
                for i, target_connector in enumerate(target_connectors):
                    # Проверяем совпадение по имени
                    connector_name = getattr(target_connector, 'name', lambda: f"input_{i}")()
                    if (connector_name.lower() == target_input.lower() or 
                        connector_name == target_input):
                        # Выполняем подключение
                        target_connector.connect(source_connector)
                        log_debug(f"MaterialX подключено через connectors: {source_node.name()} -> {target_node.name()}[{i}]")
                        return True
        
        except Exception as e:
            log_debug(f"Подключение через connectors не сработало: {e}")
        
        log_error(f"Все способы подключения не сработали для {target_input}")
        return False
            
    except Exception as e:
        log_error(f"Критическая ошибка MaterialX подключения: {e}")
        return False

def _create_materialx_surface_improved(matnet_node, safe_name, log_debug, log_error):
    """
    УЛУЧШЕННАЯ функция создания MaterialX поверхности с поддержкой Karma
    """
    
    # ИСПРАВЛЕНИЕ: Правильный порядок приоритетов для MaterialX
    surface_types = [
        # Приоритет 1: Karma Material (самый современный)
        "karmamaterial",
        # Приоритет 2: MaterialX Standard Surface  
        "mtlxstandardsurface",
        # Приоритет 3: USD Preview Surface (fallback)
        "usdpreviewsurface", 
        # Приоритет 4: Классические ноды
        "standardsurface",
        "principled_bsdf"
    ]
    
    surface_name = f"{safe_name}_surface"
    
    for surface_type in surface_types:
        try:
            # Специальная обработка для Karma Material
            if surface_type == "karmamaterial":
                # Karma Material создается как Subnet с внутренней структурой
                surface = _create_karma_material_network(matnet_node, surface_name, log_debug, log_error)
                if surface:
                    log_debug(f"Создана Karma Material сеть: {surface_type}")
                    return surface
            else:
                # Обычные MaterialX ноды
                surface = matnet_node.createNode(surface_type, surface_name)
                if surface:
                    log_debug(f"Создана MaterialX поверхность типа: {surface_type}")
                    return surface
        except Exception as e:
            log_debug(f"Не удалось создать {surface_type}: {e}")
            continue
    
    log_error("Не удалось создать MaterialX поверхность любого типа")
    return None

def _create_karma_material_network(matnet_node, surface_name, log_debug, log_error):
    """
    Создает полную Karma Material сеть (современный подход)
    """
    try:
        # Создаем Subnet для Karma Material
        karma_subnet = matnet_node.createNode("subnet", surface_name)
        if not karma_subnet:
            return None
        
        karma_subnet.allowEditingOfContents()
        
        # Создаем внутренние ноды Karma Material
        # 1. Material Builder
        material_builder = karma_subnet.createNode("material_builder", "material_builder")
        
        # 2. Standard Surface или другой surface shader
        try:
            surface_shader = karma_subnet.createNode("mtlxstandardsurface", "standard_surface")
        except:
            try:
                surface_shader = karma_subnet.createNode("principled_bsdf", "surface_shader")
            except:
                surface_shader = None
        
        if surface_shader and material_builder:
            # Подключаем surface к material builder
            try:
                material_builder.setInput(0, surface_shader)  # Surface input
            except Exception as e:
                log_debug(f"Не удалось подключить surface к material builder: {e}")
        
        # 3. Создаем Output
        output_node = karma_subnet.createNode("output", "material_output")
        if output_node and material_builder:
            try:
                output_node.setInput(0, material_builder)
            except Exception as e:
                log_debug(f"Не удалось подключить к output: {e}")
        
        # 4. Настраиваем параметры subnet
        karma_subnet.setName(surface_name)
        karma_subnet.setComment("Karma Material Network")
        
        # Размещаем ноды
        try:
            if surface_shader:
                surface_shader.moveToGoodPosition()
            if material_builder:
                material_builder.moveToGoodPosition()
            if output_node:
                output_node.moveToGoodPosition()
        except:
            pass
        
        log_debug(f"Создана Karma Material сеть с внутренними нодами")
        return karma_subnet
        
    except Exception as e:
        log_error(f"Ошибка создания Karma Material сети: {e}")
        return None


def create_materialx_shader_improved(matnet_node, material_name, texture_maps, logger=None):
    """
    УЛУЧШЕННАЯ функция создания MaterialX материала с поддержкой Karma
    """
    
    def log_debug(message):
        if logger:
            logger.log_debug(message)
        else:
            print(f"DEBUG MaterialX: {message}")
    
    def log_error(message):
        if logger:
            logger.log_error(message)
        else:
            print(f"ERROR MaterialX: {message}")
    
    if not matnet_node or not material_name:
        log_error("Некорректные параметры для создания MaterialX материала")
        return None
    
    # Очищаем имя материала
    safe_name = clean_node_name(material_name)
    if not safe_name or safe_name.isdigit():
        safe_name = f"mtlx_{hash(material_name) % 10000:04d}"
    
    # Создаем уникальное имя
    safe_name = _ensure_unique_material_name(matnet_node, safe_name)
    
    log_debug(f"Создание УЛУЧШЕННОГО MaterialX материала: {safe_name}")
    
    try:
        created_nodes = {}
        
        # 1. Создаем основную поверхность (с поддержкой Karma)
        surface_node = _create_materialx_surface_improved(matnet_node, safe_name, log_debug, log_error)
        if not surface_node:
            return None
        
        created_nodes['surface'] = surface_node
        
        # 2. Создаем image ноды для текстур
        image_nodes = {}
        if texture_maps:
            for tex_type, tex_path in texture_maps.items():
                image_node = _create_materialx_image_node(matnet_node, safe_name, tex_type, tex_path, log_debug, log_error)
                if image_node:
                    image_nodes[tex_type] = image_node
                    created_nodes[f'image_{tex_type}'] = image_node
        
        # 3. УЛУЧШЕННОЕ подключение image нод к поверхности
        _connect_materialx_nodes_fixed(surface_node, image_nodes, texture_maps, log_debug, log_error)
        
        # 4. Размещаем ноды
        _arrange_materialx_nodes(created_nodes, log_debug)
        
        log_debug(f"УЛУЧШЕННЫЙ MaterialX материал создан успешно: {safe_name}")
        return surface_node
        
    except Exception as e:
        log_error(f"Ошибка создания УЛУЧШЕННОГО MaterialX материала: {e}")
        return None

def _connect_materialx_nodes_properly_fixed(source_node, target_node, target_input, log_debug, log_error):
    """
    ИСПРАВЛЕННОЕ подключение MaterialX нод - использует правильные методы Houdini
    """
    try:
        # ИСПРАВЛЕНИЕ 1: Используем parm() вместо коннекторов для некоторых случаев
        target_parm = target_node.parm(target_input)
        if target_parm:
            try:
                # Способ 1: Прямое подключение через parm
                target_parm.set(source_node.path() + "/out")
                log_debug(f"MaterialX подключено через parm: {source_node.name()} -> {target_node.name()}.{target_input}")
                return True
            except Exception as e:
                log_debug(f"Подключение через parm не сработало: {e}")
        
        # ИСПРАВЛЕНИЕ 2: Используем setInput() с правильными индексами
        try:
            # Получаем список входов ноды
            input_labels = target_node.inputLabels()
            log_debug(f"Доступные входы {target_node.name()}: {input_labels}")
            
            # Ищем нужный вход по имени
            target_input_index = -1
            for i, label in enumerate(input_labels):
                if label.lower() == target_input.lower():
                    target_input_index = i
                    break
            
            if target_input_index >= 0:
                # Подключаем через setInput
                target_node.setInput(target_input_index, source_node, 0)
                log_debug(f"MaterialX подключено через setInput: {source_node.name()}[0] -> {target_node.name()}[{target_input_index}]")
                return True
            else:
                log_debug(f"Не найден вход '{target_input}' в доступных входах: {input_labels}")
        
        except Exception as e:
            log_debug(f"Подключение через setInput не сработало: {e}")
        
        # ИСПРАВЛЕНИЕ 3: Альтернативный способ через outputConnections
        try:
            # Получаем выходные коннекторы source ноды
            source_outputs = source_node.outputConnections()
            source_output_names = [conn.outputName() for conn in source_outputs] if source_outputs else []
            log_debug(f"Выходы {source_node.name()}: {source_output_names}")
            
            # Пытаемся подключить к первому выходу
            if len(source_outputs) > 0:
                source_output = source_outputs[0]
                
                # Получаем входные коннекторы target ноды
                target_inputs = target_node.inputConnections()
                for i, input_conn in enumerate(target_inputs):
                    input_name = getattr(input_conn, 'inputName', lambda: f"input_{i}")()
                    if input_name.lower() == target_input.lower():
                        # Выполняем подключение
                        target_node.setInput(i, source_node)
                        log_debug(f"MaterialX подключено через connections: {source_node.name()} -> {target_node.name()}[{i}]")
                        return True
        
        except Exception as e:
            log_debug(f"Подключение через connections не сработало: {e}")
        
        # ИСПРАВЛЕНИЕ 4: Последний способ - через expression
        try:
            if target_parm:
                # Устанавливаем expression
                expr = f'op("{source_node.path()}")'
                target_parm.setExpression(expr)
                log_debug(f"MaterialX подключено через expression: {expr} -> {target_node.name()}.{target_input}")
                return True
        
        except Exception as e:
            log_debug(f"Подключение через expression не сработало: {e}")
        
        log_error(f"Все способы подключения не сработали для {target_input}")
        return False
            
    except Exception as e:
        log_error(f"Критическая ошибка MaterialX подключения: {e}")
        return False


def _create_materialx_wrapper_fixed(matnet_node, safe_name, surface_node, log_debug, log_error):
    """
    ИСПРАВЛЕННОЕ создание material wrapper для MaterialX
    """
    try:
        material_name = f"{safe_name}_material"
        
        # ИСПРАВЛЕНИЕ: Пробуем разные типы material нод
        material_types = ["material", "principledshader", "subnet"]
        material_node = None
        
        for mat_type in material_types:
            try:
                material_node = matnet_node.createNode(mat_type, material_name)
                if material_node:
                    log_debug(f"Создан MaterialX wrapper типа: {mat_type}")
                    break
            except Exception as e:
                log_debug(f"Не удалось создать wrapper типа {mat_type}: {e}")
                continue
        
        if not material_node:
            log_error("Не удалось создать MaterialX wrapper любого типа")
            return None
        
        if surface_node:
            # ИСПРАВЛЕНИЕ: Правильное подключение поверхности к материалу
            try:
                # Способ 1: Через параметр surface
                if material_node.parm("surface"):
                    material_node.parm("surface").set(surface_node.path())
                    log_debug("Surface подключен через параметр 'surface'")
                elif material_node.parm("shop_surfacepath"):
                    material_node.parm("shop_surfacepath").set(surface_node.path())
                    log_debug("Surface подключен через параметр 'shop_surfacepath'")
                else:
                    # Способ 2: Через setInput если есть входы
                    input_labels = material_node.inputLabels()
                    if input_labels:
                        for i, label in enumerate(input_labels):
                            if "surface" in label.lower():
                                material_node.setInput(i, surface_node)
                                log_debug(f"Surface подключен через вход {i}: {label}")
                                break
                        else:
                            # Подключаем к первому входу
                            material_node.setInput(0, surface_node)
                            log_debug("Surface подключен к первому входу")
                    else:
                        log_debug("Material wrapper не имеет входов для подключения")
                
                log_debug(f"Создан MaterialX wrapper: {material_node.path()}")
                return material_node
                
            except Exception as e:
                log_error(f"Ошибка подключения поверхности к wrapper: {e}")
                return material_node
        
        return material_node
        
    except Exception as e:
        log_error(f"Ошибка создания MaterialX wrapper: {e}")
        return None


def debug_materialx_node_info(node, log_debug):
    """
    Отладочная функция для анализа MaterialX ноды
    """
    try:
        log_debug(f"=== ОТЛАДКА MATERIALX НОДЫ: {node.name()} ===")
        log_debug(f"Тип: {node.type().name()}")
        
        # Параметры
        parms = [p.name() for p in node.parms()]
        log_debug(f"Параметры ({len(parms)}): {parms}")
        
        # Входы
        input_labels = node.inputLabels()
        log_debug(f"Входы ({len(input_labels)}): {input_labels}")
        
        # Выходы
        output_labels = node.outputLabels() if hasattr(node, 'outputLabels') else []
        log_debug(f"Выходы ({len(output_labels)}): {output_labels}")
        
        # Коннекторы
        try:
            input_connectors = node.inputConnectors()
            log_debug(f"Input connectors: {len(input_connectors)}")
            for i, conn in enumerate(input_connectors):
                log_debug(f"  Input {i}: {type(conn)} - {conn}")
        except Exception as e:
            log_debug(f"Ошибка получения input connectors: {e}")
        
        try:
            output_connectors = node.outputConnectors()
            log_debug(f"Output connectors: {len(output_connectors)}")
            for i, conn in enumerate(output_connectors):
                log_debug(f"  Output {i}: {type(conn)} - {conn}")
        except Exception as e:
            log_debug(f"Ошибка получения output connectors: {e}")
        
        log_debug("=== КОНЕЦ ОТЛАДКИ ===")
        
    except Exception as e:
        log_debug(f"Ошибка отладки ноды: {e}")


def create_materialx_shader_fixed_v2(matnet_node, material_name, texture_maps, logger=None):
    """
    ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ функция создания MaterialX материала
    """
    
    def log_debug(message):
        if logger:
            logger.log_debug(message)
        else:
            print(f"DEBUG MaterialX: {message}")
    
    def log_error(message):
        if logger:
            logger.log_error(message)
        else:
            print(f"ERROR MaterialX: {message}")
    
    if not matnet_node or not material_name:
        log_error("Некорректные параметры для создания MaterialX материала")
        return None
    
    # Очищаем имя материала
    safe_name = clean_node_name(material_name)
    if not safe_name or safe_name.isdigit():
        safe_name = f"mtlx_{hash(material_name) % 10000:04d}"
    
    # Создаем уникальное имя
    safe_name = _ensure_unique_material_name(matnet_node, safe_name)
    
    log_debug(f"Создание MaterialX материала: {safe_name}")
    if texture_maps:
        log_debug(f"С текстурами:")
        for tex_type, tex_path in texture_maps.items():
            udim_label = " (UDIM)" if '<UDIM>' in tex_path else ""
            log_debug(f"  {tex_type}: {os.path.basename(tex_path)}{udim_label}")
    
    try:
        created_nodes = {}
        
        # 1. Создаем основную поверхность
        surface_node = _create_materialx_surface(matnet_node, safe_name, log_debug, log_error)
        if not surface_node:
            return None
        
        created_nodes['surface'] = surface_node
        
        # ОТЛАДКА: Анализируем созданную поверхность
        debug_materialx_node_info(surface_node, log_debug)
        
        # 2. Создаем image ноды для текстур
        image_nodes = {}
        if texture_maps:
            for tex_type, tex_path in texture_maps.items():
                image_node = _create_materialx_image_node(matnet_node, safe_name, tex_type, tex_path, log_debug, log_error)
                if image_node:
                    image_nodes[tex_type] = image_node
                    created_nodes[f'image_{tex_type}'] = image_node
                    
                    # ОТЛАДКА: Анализируем созданную image ноду
                    debug_materialx_node_info(image_node, log_debug)
        
        # 3. ИСПРАВЛЕННОЕ подключение image нод к поверхности
        _connect_materialx_nodes_fixed(surface_node, image_nodes, texture_maps, log_debug, log_error)
        
        # 4. Создаем material wrapper (ИСПРАВЛЕННАЯ версия)
        material_wrapper = _create_materialx_wrapper_fixed(matnet_node, safe_name, surface_node, log_debug, log_error)
        if material_wrapper:
            created_nodes['material'] = material_wrapper
        
        # 5. Размещаем ноды
        _arrange_materialx_nodes(created_nodes, log_debug)
        
        log_debug(f"MaterialX материал создан успешно: {safe_name}")
        return material_wrapper if material_wrapper else surface_node
        
    except Exception as e:
        log_error(f"Ошибка создания MaterialX материала: {e}")
        import traceback
        log_error(traceback.format_exc())
        return None