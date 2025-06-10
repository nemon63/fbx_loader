"""
Система кэширования для ускорения работы с моделями и текстурами - исправленная версия
"""
import os
import json
import time
import hashlib
from functools import lru_cache
import threading

# Импортируем константы, если доступны
try:
    from constants import PATHS, LIMITS
except ImportError:
    # Fallback константы
    PATHS = {
        "cache_dir_name": "model_import_cache",
        "material_cache_filename": "material_cache.json",
        "node_names_cache_filename": "node_names_cache.json", 
        "textures_cache_filename": "textures_cache.json"
    }
    LIMITS = {"max_cache_size": 1000}


class CacheManager:
    """Класс для управления кэшированием данных при импорте моделей с улучшенной обработкой ошибок"""
    
    def __init__(self, logger=None, enabled=True):
        self.logger = logger
        self.enabled = enabled
        self._lock = threading.Lock()  # Для thread-safety
        
        # Инициализация директорий и файлов
        self._init_cache_structure()
        
        # Загружаем кэшированные данные
        self._load_all_caches()
        
        # Создаем счетчики статистики
        self._init_statistics()
        
        # Логируем инициализацию
        self._log_initialization()
    
    def _init_cache_structure(self):
        """Инициализирует структуру кэша"""
        try:
            self.cache_dir = self._get_cache_dir()
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Пути к файлам кэша
            self.materials_cache_file = os.path.join(self.cache_dir, PATHS["material_cache_filename"])
            self.node_names_cache_file = os.path.join(self.cache_dir, PATHS["node_names_cache_filename"])
            self.textures_cache_file = os.path.join(self.cache_dir, PATHS["textures_cache_filename"])
            
        except Exception as e:
            self._handle_cache_error(f"Ошибка инициализации структуры кэша: {e}")
            # Fallback на временную директорию
            import tempfile
            self.cache_dir = os.path.join(tempfile.gettempdir(), "houdini_model_cache")
            try:
                os.makedirs(self.cache_dir, exist_ok=True)
            except Exception:
                self.enabled = False
                self.cache_dir = None
    
    def _get_cache_dir(self):
        """Получаем директорию для кэша"""
        try:
            import hou
            houdini_user_dir = hou.homeHoudiniDirectory()
            cache_dir = os.path.join(houdini_user_dir, PATHS["cache_dir_name"])
        except Exception:
            # Fallback если Houdini недоступен
            import tempfile
            user_home = os.path.expanduser("~")
            cache_dir = os.path.join(user_home, ".houdini_model_cache")
        
        return cache_dir
    
    def _load_all_caches(self):
        """Загружает все кэшированные данные"""
        self.materials_cache = self._load_cache(self.materials_cache_file, {})
        self.node_names_cache = self._load_cache(self.node_names_cache_file, {})
        self.textures_cache = self._load_cache(self.textures_cache_file, {})
    
    def _init_statistics(self):
        """Инициализирует счетчики статистики"""
        self.stats = {
            "material_hits": 0,
            "material_misses": 0,
            "texture_hits": 0,
            "texture_misses": 0,
            "name_hits": 0,
            "name_misses": 0
        }
    
    def _log_initialization(self):
        """Логирует информацию об инициализации"""
        if not self.logger:
            return
        
        if self.enabled:
            self.logger.log_debug(f"Кэширование включено. Директория кэша: {self.cache_dir}")
            self.logger.log_debug(f"Кэш материалов: {len(self.materials_cache)} записей")
            self.logger.log_debug(f"Кэш имен: {len(self.node_names_cache)} записей")
            self.logger.log_debug(f"Кэш текстур: {len(self.textures_cache)} записей")
        else:
            self.logger.log_debug("Кэширование отключено")
    
    def _load_cache(self, cache_file, default_value=None):
        """Загружает данные из кэш-файла с восстановлением при ошибке"""
        if not self.enabled or not cache_file:
            return default_value if default_value is not None else {}
        
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Валидация загруженных данных
                    if not isinstance(data, dict):
                        raise ValueError("Кэш должен содержать словарь")
                    
                    return data
            else:
                return default_value if default_value is not None else {}
                
        except json.JSONDecodeError as e:
            self._handle_json_error(cache_file, e)
            return default_value if default_value is not None else {}
        except Exception as e:
            self._handle_cache_error(f"Ошибка загрузки кэша из {cache_file}: {e}")
            return default_value if default_value is not None else {}
    
    def _handle_json_error(self, cache_file, error):
        """Обрабатывает ошибки JSON декодирования"""
        self._handle_cache_error(f"Ошибка декодирования JSON в файле {cache_file}: {error}")
        
        # Создаем резервную копию поврежденного файла
        try:
            backup_file = f"{cache_file}.backup_{int(time.time())}"
            import shutil
            shutil.copy(cache_file, backup_file)
            if self.logger:
                self.logger.log_warning(f"Создана резервная копия поврежденного кэша: {backup_file}")
        except Exception as e:
            self._handle_cache_error(f"Не удалось создать резервную копию: {e}")
    
    def _handle_cache_error(self, message):
        """Универсальный обработчик ошибок кэша"""
        if self.logger:
            self.logger.log_warning(message)
        else:
            print(f"WARNING: {message}")
    
    def _save_cache(self, cache_file, data):
        """Сохраняет данные в кэш-файл с блокировкой"""
        if not self.enabled or not cache_file:
            return
        
        with self._lock:
            try:
                # Проверяем размер кэша
                max_size = LIMITS.get("max_cache_size", 1000)
                if isinstance(data, dict) and len(data) > max_size:
                    # Оставляем только последние записи
                    items = list(data.items())
                    data = dict(items[-max_size:])
                    self._handle_cache_error(f"Кэш обрезан до {max_size} записей")
                
                # Создаем временный файл для атомарной записи
                temp_file = f"{cache_file}.tmp"
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # Атомарно заменяем основной файл
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                os.rename(temp_file, cache_file)
                
            except Exception as e:
                self._handle_cache_error(f"Ошибка сохранения кэша в {cache_file}: {e}")
                
                # Удаляем временный файл в случае ошибки
                temp_file = f"{cache_file}.tmp"
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
    
    def get_material_path(self, material_name):
        """Получает путь к материалу из кэша"""
        if not self.enabled or not material_name:
            return None
        
        try:
            with self._lock:
                if material_name in self.materials_cache:
                    self.stats["material_hits"] += 1
                    return self.materials_cache[material_name]
                else:
                    self.stats["material_misses"] += 1
                    return None
        except Exception as e:
            self._handle_cache_error(f"Ошибка получения материала из кэша: {e}")
            return None
    
    def set_material_path(self, material_name, material_path):
        """Сохраняет путь к материалу в кэш"""
        if not self.enabled or not material_name or not material_path:
            return
        
        try:
            with self._lock:
                self.materials_cache[material_name] = material_path
                self._save_cache(self.materials_cache_file, self.materials_cache)
        except Exception as e:
            self._handle_cache_error(f"Ошибка сохранения материала в кэш: {e}")
    
    @lru_cache(maxsize=1024)
    def get_clean_node_name(self, name):
        """Получает очищенное имя узла из кэша с LRU декорированием"""
        if not self.enabled or not name:
            return self._clean_node_name_fallback(name)
        
        try:
            cache_key = str(name)
            
            with self._lock:
                if cache_key in self.node_names_cache:
                    self.stats["name_hits"] += 1
                    return self.node_names_cache[cache_key]
                else:
                    # Очищаем имя
                    cleaned_name = self._clean_node_name_fallback(name)
                    
                    # Сохраняем в кэш
                    self.node_names_cache[cache_key] = cleaned_name
                    self._save_cache(self.node_names_cache_file, self.node_names_cache)
                    
                    self.stats["name_misses"] += 1
                    return cleaned_name
                    
        except Exception as e:
            self._handle_cache_error(f"Ошибка обработки имени узла: {e}")
            return self._clean_node_name_fallback(name)
    
    def _clean_node_name_fallback(self, name):
        """Fallback функция для очистки имени узла"""
        try:
            from utils import clean_node_name
            return clean_node_name(name)
        except ImportError:
            # Простая очистка имени, если utils недоступен
            if not name:
                return "default_node"
            
            import re
            cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', str(name))
            if cleaned and cleaned[0].isdigit():
                cleaned = 'n_' + cleaned
            return cleaned[:30] if len(cleaned) > 30 else cleaned
    
    def find_matching_textures(self, material_name, model_basename, texture_files, texture_keywords):
        """Ищет текстуры с использованием кэша"""
        if not self.enabled:
            return self._find_textures_fallback(material_name, model_basename, texture_files, texture_keywords)
        
        try:
            # Создаем ключ кэша
            texture_files_hash = self._create_texture_hash(texture_files)
            cache_key = f"{material_name}_{model_basename}_{texture_files_hash}"
            
            with self._lock:
                if cache_key in self.textures_cache:
                    cached_textures = self.textures_cache[cache_key]
                    
                    # Проверяем актуальность кэша
                    if self._validate_cached_textures(cached_textures):
                        self.stats["texture_hits"] += 1
                        if self.logger:
                            self.logger.log_debug(f"Найдено в кэше текстур: {material_name} ({len(cached_textures)} текстур)")
                        return cached_textures
                    else:
                        # Удаляем неактуальную запись
                        del self.textures_cache[cache_key]
            
            # Если кэша нет или он неактуален, выполняем поиск
            found_textures = self._find_textures_fallback(material_name, model_basename, texture_files, texture_keywords)
            
            # Сохраняем результат в кэш
            with self._lock:
                self.textures_cache[cache_key] = found_textures
                self._save_cache(self.textures_cache_file, self.textures_cache)
            
            self.stats["texture_misses"] += 1
            return found_textures
            
        except Exception as e:
            self._handle_cache_error(f"Ошибка поиска текстур в кэше: {e}")
            return self._find_textures_fallback(material_name, model_basename, texture_files, texture_keywords)
    
    def _create_texture_hash(self, texture_files):
        """Создает хеш для списка файлов текстур"""
        try:
            if not texture_files:
                return "empty"
            
            # Сортируем файлы для консистентности
            sorted_files = sorted(texture_files)
            combined_string = "".join(sorted_files)
            
            return hashlib.md5(combined_string.encode('utf-8')).hexdigest()[:16]
        except Exception:
            return f"fallback_{len(texture_files)}"
    
    def _validate_cached_textures(self, cached_textures):
        """Проверяет актуальность кэшированных текстур"""
        if not isinstance(cached_textures, dict):
            return False
        
        try:
            # Проверяем, что все файлы существуют
            for tex_type, tex_path in cached_textures.items():
                if tex_path and not os.path.exists(tex_path):
                    return False
            return True
        except Exception:
            return False
    
    def _find_textures_fallback(self, material_name, model_basename, texture_files, texture_keywords):
        """Fallback функция для поиска текстур"""
        try:
            from material_utils import find_matching_textures
            return find_matching_textures(material_name, texture_files, texture_keywords, model_basename)
        except ImportError:
            # Очень простой fallback поиск
            found_textures = {}
            if texture_files:
                found_textures["BaseMap"] = texture_files[0]
            return found_textures
    
    def get_cache_stats(self):
        """Возвращает статистику кэширования"""
        try:
            return {
                "materials": {
                    "hits": self.stats["material_hits"],
                    "misses": self.stats["material_misses"],
                    "hit_ratio": self._calculate_hit_ratio(self.stats["material_hits"], self.stats["material_misses"]),
                    "size": len(self.materials_cache)
                },
                "textures": {
                    "hits": self.stats["texture_hits"],
                    "misses": self.stats["texture_misses"],
                    "hit_ratio": self._calculate_hit_ratio(self.stats["texture_hits"], self.stats["texture_misses"]),
                    "size": len(self.textures_cache)
                },
                "names": {
                    "hits": self.stats["name_hits"],
                    "misses": self.stats["name_misses"],
                    "hit_ratio": self._calculate_hit_ratio(self.stats["name_hits"], self.stats["name_misses"]),
                    "size": len(self.node_names_cache)
                }
            }
        except Exception as e:
            self._handle_cache_error(f"Ошибка получения статистики кэша: {e}")
            return {"error": str(e)}
    
    def _calculate_hit_ratio(self, hits, misses):
        """Вычисляет соотношение хитов к общему числу обращений"""
        try:
            total = hits + misses
            if total == 0:
                return 0.0
            return hits / total
        except Exception:
            return 0.0
    
    def clear_cache(self):
        """Очищает все кэши"""
        if not self.enabled:
            return
        
        try:
            with self._lock:
                self.materials_cache = {}
                self.node_names_cache = {}
                self.textures_cache = {}
                
                # Сохраняем пустые кэши
                self._save_cache(self.materials_cache_file, self.materials_cache)
                self._save_cache(self.node_names_cache_file, self.node_names_cache)
                self._save_cache(self.textures_cache_file, self.textures_cache)
                
                # Очищаем LRU кэш
                self.get_clean_node_name.cache_clear()
                
                # Сбрасываем статистику
                self._init_statistics()
                
            if self.logger:
                self.logger.log_info("Все кэши очищены")
            else:
                print("Все кэши очищены")
                
        except Exception as e:
            self._handle_cache_error(f"Ошибка очистки кэша: {e}")
    
    def update_material_cache(self, material_cache):
        """Обновляет кэш материалов из словаря"""
        if not self.enabled or not isinstance(material_cache, dict):
            return
        
        try:
            with self._lock:
                old_size = len(self.materials_cache)
                self.materials_cache.update(material_cache)
                self._save_cache(self.materials_cache_file, self.materials_cache)
                
                new_entries = len(self.materials_cache) - old_size
                if self.logger:
                    self.logger.log_debug(f"Кэш материалов обновлен: {new_entries} новых записей")
                    
        except Exception as e:
            self._handle_cache_error(f"Ошибка обновления кэша материалов: {e}")
    
    def cleanup_old_cache_files(self, max_age_days=30):
        """Очищает старые файлы кэша"""
        if not self.enabled or not self.cache_dir:
            return
        
        try:
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    
                    if file_age > max_age_seconds:
                        try:
                            os.remove(file_path)
                            if self.logger:
                                self.logger.log_debug(f"Удален старый файл кэша: {filename}")
                        except Exception as e:
                            self._handle_cache_error(f"Не удалось удалить файл {filename}: {e}")
                            
        except Exception as e:
            self._handle_cache_error(f"Ошибка очистки старых файлов кэша: {e}")
    
    def get_cache_size_info(self):
        """Возвращает информацию о размере кэша"""
        if not self.enabled or not self.cache_dir:
            return {"error": "Кэш отключен"}
        
        try:
            total_size = 0
            file_count = 0
            
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
                    file_count += 1
            
            return {
                "directory": self.cache_dir,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count,
                "materials_count": len(self.materials_cache),
                "textures_count": len(self.textures_cache),
                "names_count": len(self.node_names_cache)
            }
            
        except Exception as e:
            self._handle_cache_error(f"Ошибка получения информации о размере кэша: {e}")
            return {"error": str(e)}
    
    def is_enabled(self):
        """Проверяет, включен ли кэш"""
        return self.enabled
    
    def disable_cache(self):
        """Отключает кэширование"""
        self.enabled = False
        if self.logger:
            self.logger.log_info("Кэширование отключено")
    
    def enable_cache(self):
        """Включает кэширование"""
        if self.cache_dir and os.path.exists(self.cache_dir):
            self.enabled = True
            if self.logger:
                self.logger.log_info("Кэширование включено")
        else:
            self._handle_cache_error("Не удалось включить кэширование: директория недоступна")
    
    def export_cache(self, export_path):
        """Экспортирует кэш в указанную директорию"""
        if not self.enabled or not self.cache_dir:
            return False
        
        try:
            import shutil
            
            os.makedirs(export_path, exist_ok=True)
            
            # Копируем файлы кэша
            cache_files = [
                self.materials_cache_file,
                self.node_names_cache_file,
                self.textures_cache_file
            ]
            
            for cache_file in cache_files:
                if os.path.exists(cache_file):
                    filename = os.path.basename(cache_file)
                    dest_path = os.path.join(export_path, filename)
                    shutil.copy2(cache_file, dest_path)
            
            if self.logger:
                self.logger.log_info(f"Кэш экспортирован в: {export_path}")
            
            return True
            
        except Exception as e:
            self._handle_cache_error(f"Ошибка экспорта кэша: {e}")
            return False
    
    def import_cache(self, import_path):
        """Импортирует кэш из указанной директории"""
        if not self.enabled:
            return False
        
        try:
            import shutil
            
            # Файлы для импорта
            import_files = {
                "material_cache.json": self.materials_cache_file,
                "node_names_cache.json": self.node_names_cache_file,
                "textures_cache.json": self.textures_cache_file
            }
            
            imported_count = 0
            
            for filename, dest_path in import_files.items():
                src_path = os.path.join(import_path, filename)
                
                if os.path.exists(src_path):
                    # Создаем резервную копию существующего файла
                    if os.path.exists(dest_path):
                        backup_path = f"{dest_path}.backup_{int(time.time())}"
                        shutil.copy2(dest_path, backup_path)
                    
                    # Копируем импортируемый файл
                    shutil.copy2(src_path, dest_path)
                    imported_count += 1
            
            if imported_count > 0:
                # Перезагружаем кэши
                self._load_all_caches()
                
                if self.logger:
                    self.logger.log_info(f"Импортировано {imported_count} файлов кэша из: {import_path}")
                
                return True
            else:
                self._handle_cache_error(f"Не найдено файлов кэша для импорта в: {import_path}")
                return False
                
        except Exception as e:
            self._handle_cache_error(f"Ошибка импорта кэша: {e}")
            return False