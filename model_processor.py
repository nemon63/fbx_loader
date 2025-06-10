"""
Оптимизированные функции для обработки моделей - исправленная версия с батчингом
"""
import hou
import os
import time
from utils import clean_node_name, generate_unique_name, get_node_bbox
from material_utils import generate_python_sop_code

# Импорт UDIM поддержки
try:
    from udim_utils import get_udim_statistics
    UDIM_AVAILABLE = True
except ImportError:
    UDIM_AVAILABLE = False


class ModelProcessor:
    """Класс для оптимизированной обработки моделей"""
    
    def __init__(self, logger=None, settings=None):
        self.logger = logger
        self.settings = settings or self._get_default_settings()
        self.processed_count = 0
        self.failed_count = 0
        self.start_time = time.time()
    
    def _get_default_settings(self):
        """Возвращает настройки по умолчанию"""
        class DefaultSettings:
            material_type = "principledshader"
        return DefaultSettings()
    
    def log_debug(self, message):
        """Безопасное логирование"""
        if self.logger:
            self.logger.log_debug(message)
        else:
            print(f"DEBUG: {message}")
    
    def log_error(self, message):
        """Безопасное логирование ошибок"""
        if self.logger:
            self.logger.log_error(message)
        else:
            print(f"ERROR: {message}")
    
    def log_model_processed(self, model_path, node_path):
        """Безопасное логирование обработанной модели"""
        if self.logger:
            self.logger.log_model_processed(model_path, node_path)
    
    def log_model_failed(self, model_path, error):
        """Безопасное логирование неудачной модели"""
        if self.logger:
            self.logger.log_model_failed(model_path, error)


def process_single_model_with_udim_support(model_file, parent_node, matnet, folder_path, 
                                          texture_files, texture_keywords, material_cache, 
                                          models_info, material_type, model_index, logger=None):
    """Обработка одной модели с полной UDIM поддержкой"""
    
    model_basename = os.path.basename(model_file)
    model_name = os.path.splitext(model_basename)[0]
    
    # Создаем уникальное имя для геометрии
    safe_model_name = clean_node_name(model_name)
    if not safe_model_name or safe_model_name.isdigit():
        safe_model_name = f"model_{model_index:03d}"
    else:
        safe_model_name = f"model_{model_index:03d}_{safe_model_name}"
    
    node_name = generate_unique_name(parent_node, "geo", safe_model_name)
    
    try:
        # Создаём geo для модели
        geo_node = parent_node.createNode("geo", node_name)
        geo_node.allowEditingOfContents()
        
        # Создаём ноду File для импорта
        file_node = geo_node.createNode("file", "file_in")
        file_node.parm("file").set(model_file)
        
        # Создаём Python SOP для назначения материалов с полной UDIM поддержкой
        python_node = geo_node.createNode("python", "assign_materials_udim")
        python_node.setInput(0, file_node)
        
        # Генерируем расширенный код для Python SOP с полной UDIM поддержкой
        try:
            python_code = generate_python_sop_code(
                model_file, folder_path, texture_files, 
                matnet.path(), texture_keywords, material_cache, material_type
            )
            python_node.parm("python").set(python_code)
            
            # Добавляем комментарий о UDIM поддержке
            if UDIM_AVAILABLE:
                try:
                    udim_stats = get_udim_statistics(texture_files)
                    if udim_stats['udim_sequences'] > 0:
                        python_node.setComment(f"UDIM: {udim_stats['udim_sequences']} seq, {udim_stats['udim_tiles']} tiles")
                        python_node.setGenericFlag(hou.nodeFlag.DisplayComment, True)
                except:
                    pass
            
        except Exception as e:
            if logger:
                logger.log_error(f"Ошибка генерации Python кода для {model_name}: {e}")
            return False
        
        # Настройка отображения
        python_node.setDisplayFlag(True)
        python_node.setRenderFlag(True)
        
        # Размещаем ноды
        file_node.moveToGoodPosition()
        python_node.moveToGoodPosition()
        
        # Добавляем null для чистоты
        null_node = geo_node.createNode("null", "OUT")
        null_node.setInput(0, python_node)
        null_node.setDisplayFlag(True)
        null_node.setRenderFlag(True)
        null_node.moveToGoodPosition()
        
        # Для расстановки собираем bounding box
        bbox = get_node_bbox(null_node)
        udim_info = None
        if UDIM_AVAILABLE:
            try:
                udim_info = get_udim_statistics(texture_files)
            except:
                pass
        
        models_info.append({
            "node": geo_node,
            "bbox": bbox,
            "udim_info": udim_info
        })
        
        if logger:
            logger.log_model_processed(model_file, geo_node.path())
        
        return True
        
    except Exception as e:
        error_msg = f"Ошибка создания геометрии для модели {model_name}: {e}"
        print(f"ERROR: {error_msg}")
        if logger:
            logger.log_model_failed(model_file, error_msg)
        return False


def process_models_with_single_material_optimized(models, parent_node, material, models_info, settings=None, logger=None):
    """Оптимизированная обработка моделей с одним общим материалом"""
    
    if not models or not parent_node or not material:
        print("ERROR: Некорректные параметры для обработки моделей")
        return
    
    processor = ModelProcessor(logger, settings)
    material_path = ""
    
    try:
        material_path = material.path()
        processor.log_debug(f"Используем общий материал: {material_path}")
    except Exception as e:
        processor.log_error(f"Не удалось получить путь к материалу: {e}")
        return
    
    # Обрабатываем модели батчами для оптимизации
    batch_size = 10
    total_models = len(models)
    
    processor.log_debug(f"Начинаем обработку {total_models} моделей батчами по {batch_size}")
    
    for batch_start in range(0, total_models, batch_size):
        batch_end = min(batch_start + batch_size, total_models)
        batch_models = models[batch_start:batch_end]
        
        processor.log_debug(f"Обработка батча {batch_start//batch_size + 1}: модели {batch_start+1}-{batch_end}")
        
        # Обрабатываем батч
        for model_idx, model_file in enumerate(batch_models):
            global_idx = batch_start + model_idx
            
            try:
                success = _process_single_model_with_material(
                    model_file, parent_node, material_path, global_idx, models_info, processor
                )
                
                if success:
                    processor.processed_count += 1
                else:
                    processor.failed_count += 1
                
                # Показываем прогресс каждые 5 моделей
                if (global_idx + 1) % 5 == 0 or global_idx == total_models - 1:
                    elapsed = time.time() - processor.start_time
                    progress = ((global_idx + 1) / total_models) * 100
                    print(f"Прогресс: {global_idx + 1}/{total_models} ({progress:.1f}%) за {elapsed:.1f}с")
                
            except Exception as e:
                processor.log_error(f"Ошибка обработки модели {model_file}: {e}")
                processor.failed_count += 1
                continue
        
        # Небольшая пауза между батчами для предотвращения зависания UI
        if batch_end < total_models:
            time.sleep(0.01)
    
    # Финальная статистика
    total_time = time.time() - processor.start_time
    processor.log_debug(f"Обработка завершена за {total_time:.2f}с. Успешно: {processor.processed_count}, Ошибок: {processor.failed_count}")


def _process_single_model_with_material(model_file, parent_node, material_path, model_idx, models_info, processor):
    """Обрабатывает одну модель с назначенным материалом"""
    
    model_basename = os.path.basename(model_file)
    model_name = os.path.splitext(model_basename)[0]
    
    # Создаем уникальное имя
    safe_model_name = clean_node_name(model_name)
    if not safe_model_name or safe_model_name.isdigit():
        safe_model_name = f"model_{model_idx:03d}"
    else:
        safe_model_name = f"model_{model_idx:03d}_{safe_model_name}"
    
    node_name = generate_unique_name(parent_node, "geo", safe_model_name)
    
    try:
        # Создаём geo для модели
        geo_node = parent_node.createNode("geo", node_name)
        geo_node.allowEditingOfContents()
        
        # Создаём ноду File для импорта
        file_node = geo_node.createNode("file", "file_in")
        file_node.parm("file").set(model_file)
        
        # Создаём ноду для назначения материала
        material_node = geo_node.createNode("material", "assign_material")
        material_node.setInput(0, file_node)
        
        # Назначаем материал
        success = _assign_material_to_node_enhanced(material_node, material_path, model_name, processor)
        
        if not success:
            # Создаем принудительный Python SOP
            python_node = _create_force_material_python_sop(geo_node, material_node, material_path)
            if python_node:
                output_node = python_node
                processor.log_debug(f"Использован принудительный Python SOP для {model_name}")
            else:
                output_node = material_node
        else:
            output_node = material_node
        
        # Устанавливаем флаги отображения
        output_node.setDisplayFlag(True)
        output_node.setRenderFlag(True)
        
        # Размещаем ноды
        file_node.moveToGoodPosition()
        material_node.moveToGoodPosition()
        if 'python_node' in locals() and python_node:
            python_node.moveToGoodPosition()
        
        # Добавляем null
        null_node = geo_node.createNode("null", "OUT")
        null_node.setInput(0, output_node)
        null_node.setDisplayFlag(True)
        null_node.setRenderFlag(True)
        null_node.moveToGoodPosition()
        
        # Собираем bounding box для расстановки
        bbox = get_node_bbox(null_node)
        models_info.append({
            "node": geo_node,
            "bbox": bbox
        })
        
        processor.log_model_processed(model_file, geo_node.path())
        return True
        
    except Exception as e:
        processor.log_error(f"Ошибка создания геометрии для {model_name}: {e}")
        return False


def _assign_material_to_node_enhanced(material_node, material_path, model_name, processor):
    """Улучшенная функция назначения материала"""
    
    # Расширенный список параметров для попытки назначения
    material_params = [
        "shop_materialpath",
        "material", 
        "mat",
        "materialpath",
        "shop_materialf",
        "path"
    ]
    
    for param_name in material_params:
        param = material_node.parm(param_name)
        if param:
            try:
                processor.log_debug(f"Попытка назначения через параметр {param_name}")
                param.set(material_path)
                
                # Проверяем, что значение установилось
                current_value = param.eval()
                if str(current_value) == str(material_path):
                    processor.log_debug(f"Успешно назначен материал через {param_name}")
                    return True
                else:
                    # Пробуем через выражение
                    try:
                        param.setExpression(f'"{material_path}"')
                        if param.eval() == material_path:
                            processor.log_debug(f"Материал назначен через выражение {param_name}")
                            return True
                    except Exception as e:
                        processor.log_debug(f"Ошибка установки выражения для {param_name}: {e}")
                        
            except Exception as e:
                processor.log_debug(f"Ошибка установки параметра {param_name}: {e}")
                continue
    
    # Если не получилось назначить стандартными способами
    processor.log_debug(f"Не удалось назначить материал стандартными способами для {model_name}")
    
    # Выводим список всех доступных параметров для отладки
    all_parms = material_node.parms()
    processor.log_debug(f"Доступные параметры материала ({len(all_parms)}):")
    for i, parm in enumerate(all_parms[:20]):  # Показываем первые 20
        processor.log_debug(f"  {i+1}. {parm.name()}")
    
    return False


def _create_force_material_python_sop(geo_node, material_node, material_path):
    """Создает принудительный Python SOP для назначения материала"""
    try:
        python_node = geo_node.createNode("python", "force_material")
        python_node.setInput(0, material_node)
        
        # Упрощенный и надежный код для назначения материала
        python_code = f'''
import hou

def main():
    node = hou.pwd()
    geo = node.geometry()
    
    material_path = "{material_path}"
    
    # Добавляем атрибут shop_materialpath, если его нет
    mat_attr = geo.findPrimAttrib("shop_materialpath")
    if not mat_attr:
        geo.addAttrib(hou.attribType.Prim, "shop_materialpath", "")
        mat_attr = geo.findPrimAttrib("shop_materialpath")
    
    # Устанавливаем материал для всех примитивов
    count = 0
    for prim in geo.prims():
        prim.setAttribValue("shop_materialpath", material_path)
        count += 1
    
    print(f"Принудительно назначен материал {{material_path}} для {{count}} примитивов")

main()
'''
        python_node.parm("python").set(python_code)
        return python_node
        
    except Exception as e:
        print(f"Ошибка создания принудительного Python SOP: {e}")
        return None


def process_models_optimized(models, parent_node, matnet, folder_path, texture_files, texture_keywords, material_cache, models_info, settings=None, logger=None):
    """Оптимизированная обработка списка моделей"""
    
    if not models:
        print("Нет моделей для обработки")
        return
    
    processor = ModelProcessor(logger, settings)
    material_type = getattr(settings, 'material_type', "principledshader")
    
    batch_size = 15  # Уменьшаем размер батча для лучшей производительности
    total_models = len(models)
    
    processor.log_debug(f"Начинаем оптимизированную обработку {total_models} моделей")
    
    # Обрабатываем модели батчами
    for batch_start in range(0, total_models, batch_size):
        batch_end = min(batch_start + batch_size, total_models)
        batch_models = models[batch_start:batch_end]
        
        processor.log_debug(f"Обработка батча {batch_start//batch_size + 1}: модели {batch_start+1}-{batch_end}")
        
        # Обрабатываем модели в батче
        for model_idx, model_file in enumerate(batch_models):
            global_idx = batch_start + model_idx
            
            try:
                success = _process_single_model_optimized(
                    model_file, parent_node, matnet, folder_path, texture_files,
                    texture_keywords, material_cache, models_info, material_type,
                    global_idx, processor
                )
                
                if success:
                    processor.processed_count += 1
                else:
                    processor.failed_count += 1
                
                # Показываем прогресс
                if (global_idx + 1) % 5 == 0 or global_idx == total_models - 1:
                    elapsed = time.time() - processor.start_time
                    progress = ((global_idx + 1) / total_models) * 100
                    print(f"Прогресс: {global_idx + 1}/{total_models} ({progress:.1f}%) за {elapsed:.1f}с")
                
            except Exception as e:
                processor.log_error(f"Ошибка обработки модели {model_file}: {e}")
                processor.failed_count += 1
                continue
        
        # Пауза между батчами
        if batch_end < total_models:
            time.sleep(0.02)
    
    # Финальная статистика
    total_time = time.time() - processor.start_time
    processor.log_debug(f"Оптимизированная обработка завершена за {total_time:.2f}с. Успешно: {processor.processed_count}, Ошибок: {processor.failed_count}")


def _process_single_model_optimized(model_file, parent_node, matnet, folder_path, texture_files, 
                                   texture_keywords, material_cache, models_info, material_type, 
                                   model_idx, processor):
    """Оптимизированная обработка одной модели"""
    
    # Валидация файла
    if not os.path.isfile(model_file):
        processor.log_error(f"Файл не существует: {model_file}")
        return False
    
    model_basename = os.path.basename(model_file)
    model_name = os.path.splitext(model_basename)[0]
    
    # Создаем уникальное имя
    safe_model_name = clean_node_name(model_name)
    if not safe_model_name or safe_model_name.isdigit():
        safe_model_name = f"model_{model_idx:03d}"
    else:
        safe_model_name = f"model_{model_idx:03d}_{safe_model_name}"
    
    node_name = generate_unique_name(parent_node, "geo", safe_model_name)
    
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
        
        # Генерируем код для Python SOP
        try:
            python_code = generate_python_sop_code(
                model_file, folder_path, texture_files, 
                matnet.path(), texture_keywords, material_cache, material_type
            )
            python_node.parm("python").set(python_code)
            if processor.logger:
                folder_name = os.path.basename(folder_path)
                material_name = folder_name if folder_name else "unified_material"
                
                processor.logger.log_material_created(
                    material_name=material_name, 
                    material_path=f"{matnet.path()}/{material_name.lower()}", 
                    textures={}
                )
                
                # Обновляем статистику
                processor.logger.statistics["created_materials"] = 1
                if texture_files:
                    estimated_textures = min(len(texture_files), 10)
                    processor.logger.statistics["assigned_textures"] = estimated_textures
            

        except Exception as e:
            processor.log_error(f"Ошибка генерации Python кода для {model_name}: {e}")
            return False
        
        # Настройка отображения
        python_node.setDisplayFlag(True)
        python_node.setRenderFlag(True)
        
        # Размещаем ноды
        file_node.moveToGoodPosition()
        python_node.moveToGoodPosition()
        
        # Добавляем null
        null_node = geo_node.createNode("null", "OUT")
        null_node.setInput(0, python_node)
        null_node.setDisplayFlag(True)
        null_node.setRenderFlag(True)
        null_node.moveToGoodPosition()
        
        # Собираем bounding box
        bbox = get_node_bbox(null_node)
        models_info.append({
            "node": geo_node,
            "bbox": bbox
        })
        
        processor.log_model_processed(model_file, geo_node.path())
        return True
        
    except Exception as e:
        processor.log_error(f"Ошибка создания геометрии для {model_name}: {e}")
        return False


def process_models_in_single_geo_optimized(models, parent_node, matnet, folder_path, texture_files, 
                                          texture_keywords, material_cache, models_info, settings=None, logger=None):
    """Оптимизированная обработка моделей в одной геометрии"""
    
    if not models:
        print("Нет моделей для обработки!")
        return
    
    processor = ModelProcessor(logger, settings)
    material_type = getattr(settings, 'material_type', "principledshader")
    
    # Создаем имя для объединенной геометрии
    first_model = os.path.basename(models[0])
    first_model_name = os.path.splitext(first_model)[0]
    
    if len(models) > 1:
        node_name = generate_unique_name(parent_node, "geo", "combined_models")
    else:
        safe_model_name = clean_node_name(first_model_name)
        node_name = generate_unique_name(parent_node, "geo", safe_model_name)
    
    processor.log_debug(f"Создание объединенной геометрии для {len(models)} моделей: {node_name}")
    
    try:
        # Создаём общую geo-ноду
        geo_node = parent_node.createNode("geo", node_name)
        geo_node.allowEditingOfContents()
        
        # Создаем merge-ноду
        merge_node = geo_node.createNode("merge", "merge_models")
        
        # Добавляем модели батчами для предотвращения зависания
        batch_size = 20
        file_nodes = []
        
        for i in range(0, len(models), batch_size):
            batch_models = models[i:i + batch_size]
            processor.log_debug(f"Добавление батча файлов {i//batch_size + 1}: {len(batch_models)} моделей")
            
            for j, model_file in enumerate(batch_models):
                global_idx = i + j
                model_basename = os.path.basename(model_file)
                model_name = os.path.splitext(model_basename)[0]
                
                # Создаем file ноду
                safe_name = clean_node_name(model_name)
                file_name = f"file_{global_idx:03d}_{safe_name}" if safe_name else f"file_{global_idx:03d}"
                
                try:
                    file_node = geo_node.createNode("file", file_name)
                    file_node.parm("file").set(model_file)
                    
                    # Подключаем к merge
                    merge_node.setNextInput(file_node)
                    file_node.moveToGoodPosition()
                    file_nodes.append(file_node)
                    
                except Exception as e:
                    processor.log_error(f"Ошибка создания file ноды для {model_file}: {e}")
                    continue
            
            # Пауза между батчами
            if i + batch_size < len(models):
                time.sleep(0.01)
        
        processor.log_debug(f"Создано {len(file_nodes)} file нод")
        
        # Создаём Python SOP для назначения материалов
        python_node = geo_node.createNode("python", "assign_materials")
        python_node.setInput(0, merge_node)
        
        # Генерируем код с учетом множества моделей
        try:
            python_code = generate_python_sop_code(
                models[0], folder_path, texture_files, 
                matnet.path(), texture_keywords, material_cache, material_type
            )
            python_node.parm("python").set(python_code)
        except Exception as e:
            processor.log_error(f"Ошибка генерации Python кода для объединенных моделей: {e}")
        
        # Устанавливаем флаги
        python_node.setDisplayFlag(True)
        python_node.setRenderFlag(True)
        
        # Размещаем ноды
        merge_node.moveToGoodPosition()
        python_node.moveToGoodPosition()
        
        # Добавляем null
        null_node = geo_node.createNode("null", "OUT")
        null_node.setInput(0, python_node)
        null_node.setDisplayFlag(True)
        null_node.setRenderFlag(True)
        null_node.moveToGoodPosition()
        
        # Собираем bounding box
        bbox = get_node_bbox(null_node)
        models_info.append({
            "node": geo_node,
            "bbox": bbox
        })
        
        processor.log_debug(f"Объединено {len(models)} моделей в одну геометрию {node_name}")
        
    except Exception as e:
        processor.log_error(f"Ошибка создания объединенной геометрии: {e}")


# Обертки для обратной совместимости
def process_models_with_single_material(models, parent_node, material, models_info, settings=None):
    """Обертка для обратной совместимости"""
    return process_models_with_single_material_optimized(models, parent_node, material, models_info, settings)


def process_models(models, parent_node, matnet, folder_path, texture_files, texture_keywords, material_cache, models_info, settings=None):
    """Обертка для обратной совместимости"""
    return process_models_optimized(models, parent_node, matnet, folder_path, texture_files, texture_keywords, material_cache, models_info, settings)


def process_models_in_single_geo(models, parent_node, matnet, folder_path, texture_files, texture_keywords, material_cache, models_info, settings=None):
    """Обертка для обратной совместимости"""
    return process_models_in_single_geo_optimized(models, parent_node, matnet, folder_path, texture_files, texture_keywords, material_cache, models_info, settings)