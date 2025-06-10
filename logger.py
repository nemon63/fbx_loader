"""
Система логирования и отчетов для импорта моделей - исправленная версия
"""
import os
import time
import logging
import webbrowser
from datetime import datetime

# Импортируем константы, если доступны
try:
    from constants import HTML_TEMPLATES, FILE_PATTERNS, PATHS
except ImportError:
    # Fallback константы
    HTML_TEMPLATES = {"report_css": "body { font-family: Arial, sans-serif; }"}
    FILE_PATTERNS = {
        "log_file": "import_log_{timestamp}.log",
        "report_file": "import_report_{timestamp}.html",
        "backup_file": "{original_name}.backup"
    }
    PATHS = {
        "logs_dir_name": "model_import_logs",
        "cache_dir_name": "model_import_cache"
    }


class ImportLogger:
    """Класс для логирования и создания отчетов об импорте с улучшенной обработкой ошибок"""
    
    def __init__(self, debug_mode=False):
        self.debug_mode = debug_mode
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Инициализируем директории и файлы
        self._init_directories()
        self._init_files()
        
        # Настраиваем логирование
        self._setup_logger()
        
        # Информация для отчета
        self.start_time = time.time()
        self._init_statistics()
        self._init_collections()
        
        # Начинаем сессию логирования
        self._log_session_start()
    
    def _init_directories(self):
        """Инициализирует директории для логов"""
        try:
            self.logs_dir = self._get_logs_dir()
            os.makedirs(self.logs_dir, exist_ok=True)
        except Exception as e:
            # Fallback на временную директорию
            import tempfile
            self.logs_dir = os.path.join(tempfile.gettempdir(), "houdini_model_import_logs")
            try:
                os.makedirs(self.logs_dir, exist_ok=True)
            except Exception as e2:
                print(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось создать директорию для логов: {e2}")
                self.logs_dir = tempfile.gettempdir()
    
    def _init_files(self):
        """Инициализирует файлы логов и отчетов"""
        try:
            log_filename = FILE_PATTERNS["log_file"].format(timestamp=self.timestamp)
            report_filename = FILE_PATTERNS["report_file"].format(timestamp=self.timestamp)
            
            self.log_file = os.path.join(self.logs_dir, log_filename)
            self.report_file = os.path.join(self.logs_dir, report_filename)
        except Exception as e:
            print(f"Ошибка инициализации файлов: {e}")
            # Fallback на простые имена
            self.log_file = os.path.join(self.logs_dir, f"import_log_{self.timestamp}.log")
            self.report_file = os.path.join(self.logs_dir, f"import_report_{self.timestamp}.html")
    
    def _get_logs_dir(self):
        """Получаем директорию для логов"""
        try:
            import hou
            houdini_user_dir = hou.homeHoudiniDirectory()
            logs_dir = os.path.join(houdini_user_dir, PATHS["logs_dir_name"])
        except Exception:
            # Fallback если Houdini недоступен
            import tempfile
            logs_dir = os.path.join(tempfile.gettempdir(), "model_import_logs")
        
        return logs_dir
    
    def _setup_logger(self):
        """Настраиваем систему логирования с обработкой ошибок"""
        try:
            self.logger = logging.getLogger(f'model_import_{self.timestamp}')
            self.logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
            
            # Очищаем существующие обработчики
            if self.logger.handlers:
                self.logger.handlers.clear()
            
            # Добавляем файловый обработчик
            self._add_file_handler()
            
            # Добавляем консольный обработчик
            self._add_console_handler()
            
        except Exception as e:
            print(f"Ошибка настройки логгера: {e}")
            # Создаем минимальный fallback логгер
            self.logger = logging.getLogger('fallback_logger')
            self.logger.setLevel(logging.INFO)
    
    def _add_file_handler(self):
        """Добавляет файловый обработчик логов"""
        try:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"Не удалось создать файловый обработчик: {e}")
    
    def _add_console_handler(self):
        """Добавляет консольный обработчик логов"""
        try:
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter('%(levelname)s: %(message)s')
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        except Exception as e:
            print(f"Не удалось создать консольный обработчик: {e}")
    
    def _init_statistics(self):
        """Инициализирует статистику импорта"""
        self.statistics = {
            "total_models": 0,
            "processed_models": 0,
            "failed_models": 0,
            "created_materials": 0,
            "assigned_textures": 0,
            "warnings": 0,
            "errors": 0
        }
    
    def _init_collections(self):
        """Инициализирует коллекции для деталей импорта"""
        self.model_details = []
        self.material_details = []
        self.error_details = []
    
    def _log_session_start(self):
        """Логирует начало сессии"""
        try:
            self.logger.info("=" * 80)
            self.logger.info(f"Начало импорта моделей: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(f"Режим отладки: {'включен' if self.debug_mode else 'выключен'}")
            self.logger.info(f"Лог файл: {self.log_file}")
            self.logger.info("=" * 80)
        except Exception as e:
            print(f"Ошибка при логировании начала сессии: {e}")
    
    def log_import_start(self, folder_path, settings):
        """Логирует начало импорта с настройками"""
        try:
            self.logger.info(f"Импорт моделей из папки: {folder_path}")
            self.logger.info("Настройки импорта:")
            
            if settings:
                try:
                    for key, value in vars(settings).items():
                        self.logger.info(f"  {key}: {value}")
                except Exception as e:
                    self.logger.warning(f"Не удалось логировать настройки: {e}")
            else:
                self.logger.info("  Настройки по умолчанию")
                
        except Exception as e:
            print(f"Ошибка логирования начала импорта: {e}")
    
    def log_model_found(self, model_path):
        """Логирует обнаружение модели"""
        try:
            self.statistics["total_models"] += 1
            model_name = os.path.basename(model_path) if model_path else "unknown"
            self.logger.debug(f"Найдена модель: {model_name} ({model_path})")
        except Exception as e:
            print(f"Ошибка логирования найденной модели: {e}")
    
    def log_model_processed(self, model_path, node_path, materials=None):
        """Логирует успешную обработку модели"""
        try:
            self.statistics["processed_models"] += 1
            model_name = os.path.basename(model_path) if model_path else "unknown"
            self.logger.info(f"Обработана модель: {model_name} -> {node_path}")
            
            # Добавляем информацию для отчета
            model_info = {
                "name": model_name,
                "path": model_path or "",
                "node": node_path or "",
                "materials": materials if materials else [],
                "status": "success"
            }
            self.model_details.append(model_info)
            
        except Exception as e:
            print(f"Ошибка логирования обработанной модели: {e}")
    
    def log_model_failed(self, model_path, error_message):
        """Логирует ошибку обработки модели"""
        try:
            self.statistics["failed_models"] += 1
            model_name = os.path.basename(model_path) if model_path else "unknown"
            self.logger.error(f"Ошибка при обработке модели {model_name}: {error_message}")
            
            # Добавляем информацию для отчета
            model_info = {
                "name": model_name,
                "path": model_path or "",
                "status": "error",
                "error": str(error_message)
            }
            self.model_details.append(model_info)
            
            self.error_details.append({
                "type": "model",
                "name": model_name,
                "message": str(error_message)
            })
            
        except Exception as e:
            print(f"Ошибка логирования неудачной модели: {e}")
    
    def log_material_created(self, material_name, material_path, textures=None):
        """Логирует создание материала"""
        try:
            self.statistics["created_materials"] += 1
            self.logger.info(f"Создан материал: {material_name} -> {material_path}")
            
            # Считаем текстуры
            if textures and len(textures) > 0:
                self.statistics["assigned_textures"] += len(textures)
            
            # Добавляем информацию для отчета
            material_info = {
                "name": material_name or "unknown",
                "path": material_path or "",
                "textures": textures if textures else {},
                "status": "success"
            }
            self.material_details.append(material_info)
            
        except Exception as e:
            print(f"Ошибка логирования созданного материала: {e}")
    
    def log_material_failed(self, material_name, error_message):
        """Логирует ошибку создания материала"""
        try:
            self.logger.error(f"Ошибка при создании материала {material_name}: {error_message}")
            
            # Добавляем информацию для отчета
            material_info = {
                "name": material_name or "unknown",
                "status": "error",
                "error": str(error_message)
            }
            self.material_details.append(material_info)
            
            self.error_details.append({
                "type": "material",
                "name": material_name or "unknown",
                "message": str(error_message)
            })
            
        except Exception as e:
            print(f"Ошибка логирования неудачного материала: {e}")
    
    def log_warning(self, message):
        """Логирует предупреждение"""
        try:
            self.statistics["warnings"] += 1
            self.logger.warning(str(message))
        except Exception as e:
            print(f"Ошибка логирования предупреждения: {e}")
    
    def log_error(self, message):
        """Логирует ошибку"""
        try:
            self.statistics["errors"] += 1
            self.logger.error(str(message))
            
            # Добавляем в список ошибок для отчета
            self.error_details.append({
                "type": "general",
                "message": str(message)
            })
            
        except Exception as e:
            print(f"Ошибка логирования ошибки: {e}")
    
    def log_debug(self, message):
        """Логирует отладочное сообщение"""
        try:
            self.logger.debug(str(message))
        except Exception as e:
            print(f"Ошибка логирования отладки: {e}")
    
    def log_info(self, message):
        """Логирует информационное сообщение"""
        try:
            self.logger.info(str(message))
        except Exception as e:
            print(f"Ошибка логирования информации: {e}")
    
    def log_import_finished(self):
        """Логирует завершение импорта"""
        try:
            # Вычисляем время выполнения
            elapsed_time = time.time() - self.start_time
            
            self.logger.info("=" * 80)
            self.logger.info(f"Импорт завершен за {elapsed_time:.2f} секунд")
            self.logger.info(f"Всего моделей: {self.statistics['total_models']}")
            self.logger.info(f"Успешно обработано: {self.statistics['processed_models']}")
            self.logger.info(f"Ошибок моделей: {self.statistics['failed_models']}")
            self.logger.info(f"Создано материалов: {self.statistics['created_materials']}")
            self.logger.info(f"Назначено текстур: {self.statistics['assigned_textures']}")
            self.logger.info(f"Предупреждений: {self.statistics['warnings']}")
            self.logger.info(f"Ошибок: {self.statistics['errors']}")
            self.logger.info("=" * 80)
            
        except Exception as e:
            print(f"Ошибка логирования завершения импорта: {e}")
    
    def generate_report(self):
        """Генерирует HTML-отчет о результатах импорта"""
        try:
            elapsed_time = time.time() - self.start_time
            
            # Генерируем HTML
            html_content = self._generate_html_report(elapsed_time)
            
            # Записываем отчет в файл
            with open(self.report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"Отчет сохранен: {self.report_file}")
            return self.report_file
            
        except Exception as e:
            print(f"Ошибка генерации отчета: {e}")
            return None
    
    def _generate_html_report(self, elapsed_time):
        """Генерирует HTML содержимое отчета"""
        try:
            # Заголовок и стили
            html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет по импорту моделей</title>
    <style>
        {HTML_TEMPLATES.get("report_css", self._get_default_css())}
    </style>
</head>
<body>
    <div class="container">
        <h1>Отчет по импорту моделей</h1>
        <p>Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Время выполнения: {elapsed_time:.2f} секунд</p>
        
        <h2>Сводка</h2>
        {self._generate_summary_section()}
        
        {self._generate_errors_section()}
        {self._generate_models_section()}
        {self._generate_materials_section()}
        
        {self._generate_javascript()}
    </div>
</body>
</html>'''
            
            return html
            
        except Exception as e:
            print(f"Ошибка генерации HTML: {e}")
            return self._generate_minimal_report(elapsed_time)
    
    def _get_default_css(self):
        """Возвращает CSS по умолчанию"""
        return """
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
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
        h1 { color: #2c3e50; }
        h2 { color: #3498db; }
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
        .summary-item.success { background-color: #d5f5e3; }
        .summary-item.warning { background-color: #fdebd0; }
        .summary-item.error { background-color: #f5b7b1; }
        .summary-item h3 { margin-top: 0; }
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
        th { background-color: #ecf0f1; }
        tr:hover { background-color: #f9f9f9; }
        .success { color: #27ae60; }
        .warning { color: #e67e22; }
        .error { color: #e74c3c; }
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
        .active, .collapsible:hover { background-color: #ddd; }
        .content {
            padding: 0 18px;
            display: none;
            overflow: hidden;
            background-color: #f9f9f9;
        }
        """
    
    def _generate_summary_section(self):
        """Генерирует секцию сводки"""
        try:
            return f'''
        <div class="summary">
            <div class="summary-item success">
                <h3>Всего моделей</h3>
                <p style="font-size: 24px;">{self.statistics['total_models']}</p>
            </div>
            <div class="summary-item success">
                <h3>Успешно обработано</h3>
                <p style="font-size: 24px;">{self.statistics['processed_models']}</p>
            </div>
            <div class="summary-item {'error' if self.statistics['failed_models'] > 0 else 'success'}">
                <h3>Ошибок обработки</h3>
                <p style="font-size: 24px;">{self.statistics['failed_models']}</p>
            </div>
            <div class="summary-item success">
                <h3>Создано материалов</h3>
                <p style="font-size: 24px;">{self.statistics['created_materials']}</p>
            </div>
            <div class="summary-item success">
                <h3>Назначено текстур</h3>
                <p style="font-size: 24px;">{self.statistics['assigned_textures']}</p>
            </div>
            <div class="summary-item {'warning' if self.statistics['warnings'] > 0 else 'success'}">
                <h3>Предупреждений</h3>
                <p style="font-size: 24px;">{self.statistics['warnings']}</p>
            </div>
            <div class="summary-item {'error' if self.statistics['errors'] > 0 else 'success'}">
                <h3>Ошибок</h3>
                <p style="font-size: 24px;">{self.statistics['errors']}</p>
            </div>
        </div>'''
        except Exception as e:
            print(f"Ошибка генерации сводки: {e}")
            return "<p>Ошибка генерации сводки</p>"
    
    def _generate_errors_section(self):
        """Генерирует секцию ошибок"""
        if not self.error_details:
            return ""
        
        try:
            html = '''
        <h2>Ошибки и предупреждения</h2>
        <table>
            <tr>
                <th>Тип</th>
                <th>Имя</th>
                <th>Сообщение</th>
            </tr>'''
            
            for error in self.error_details[:50]:  # Ограничиваем количество для производительности
                error_type = error.get('type', 'unknown')
                error_name = error.get('name', '-')
                error_message = error.get('message', 'Неизвестная ошибка')
                
                html += f'''
            <tr class="error">
                <td>{self._escape_html(error_type)}</td>
                <td>{self._escape_html(error_name)}</td>
                <td>{self._escape_html(error_message)}</td>
            </tr>'''
            
            if len(self.error_details) > 50:
                html += f'''
            <tr>
                <td colspan="3"><em>... и еще {len(self.error_details) - 50} ошибок</em></td>
            </tr>'''
            
            html += '''
        </table>'''
            
            return html
            
        except Exception as e:
            print(f"Ошибка генерации секции ошибок: {e}")
            return "<p>Ошибка генерации списка ошибок</p>"
    
    def _generate_models_section(self):
        """Генерирует секцию моделей"""
        if not self.model_details:
            return ""
        
        try:
            html = f'''
        <button class="collapsible">Импортированные модели ({len(self.model_details)})</button>
        <div class="content">
            <table>
                <tr>
                    <th>Модель</th>
                    <th>Путь в Houdini</th>
                    <th>Материалы</th>
                    <th>Статус</th>
                </tr>'''
            
            for model in self.model_details[:100]:  # Ограничиваем для производительности
                model_name = self._escape_html(model.get('name', 'unknown'))
                node_path = self._escape_html(model.get('node', '-'))
                
                materials_list = ""
                if model.get('materials') and isinstance(model['materials'], list):
                    materials_names = [m.get('name', 'unknown') for m in model['materials']]
                    materials_list = ", ".join(materials_names[:5])  # Первые 5 материалов
                    if len(model['materials']) > 5:
                        materials_list += f" и еще {len(model['materials']) - 5}"
                else:
                    materials_list = "Нет"
                
                status = model.get('status', 'unknown')
                status_class = "success" if status == 'success' else "error"
                
                html += f'''
                <tr class="{status_class}">
                    <td>{model_name}</td>
                    <td>{node_path}</td>
                    <td>{self._escape_html(materials_list)}</td>
                    <td class="{status_class}">{status}</td>
                </tr>'''
            
            if len(self.model_details) > 100:
                html += f'''
                <tr>
                    <td colspan="4"><em>... и еще {len(self.model_details) - 100} моделей</em></td>
                </tr>'''
            
            html += '''
            </table>
        </div>'''
            
            return html
            
        except Exception as e:
            print(f"Ошибка генерации секции моделей: {e}")
            return "<p>Ошибка генерации списка моделей</p>"
    
    def _generate_materials_section(self):
        """Генерирует секцию материалов"""
        if not self.material_details:
            return ""
        
        try:
            html = f'''
        <button class="collapsible">Созданные материалы ({len(self.material_details)})</button>
        <div class="content">
            <table>
                <tr>
                    <th>Материал</th>
                    <th>Путь в Houdini</th>
                    <th>Текстуры</th>
                    <th>Статус</th>
                </tr>'''
            
            for material in self.material_details[:100]:
                material_name = self._escape_html(material.get('name', 'unknown'))
                material_path = self._escape_html(material.get('path', '-'))
                
                textures_list = ""
                if material.get('textures') and isinstance(material['textures'], dict):
                    textures_info = []
                    for tex_type, tex_path in material['textures'].items():
                        tex_name = os.path.basename(tex_path) if tex_path else 'unknown'
                        textures_info.append(f"{tex_type}: {tex_name}")
                    textures_list = "<br>".join(textures_info[:5])  # Первые 5 текстур
                    if len(material['textures']) > 5:
                        textures_list += f"<br>... и еще {len(material['textures']) - 5}"
                else:
                    textures_list = "Нет"
                
                status = material.get('status', 'unknown')
                status_class = "success" if status == 'success' else "error"
                
                html += f'''
                <tr class="{status_class}">
                    <td>{material_name}</td>
                    <td>{material_path}</td>
                    <td>{textures_list}</td>
                    <td class="{status_class}">{status}</td>
                </tr>'''
            
            if len(self.material_details) > 100:
                html += f'''
                <tr>
                    <td colspan="4"><em>... и еще {len(self.material_details) - 100} материалов</em></td>
                </tr>'''
            
            html += '''
            </table>
        </div>'''
            
            return html
            
        except Exception as e:
            print(f"Ошибка генерации секции материалов: {e}")
            return "<p>Ошибка генерации списка материалов</p>"
    
    def _generate_javascript(self):
        """Генерирует JavaScript для интерактивности"""
        return '''
        <script>
        var coll = document.getElementsByClassName("collapsible");
        var i;

        for (i = 0; i < coll.length; i++) {
            coll[i].addEventListener("click", function() {
                this.classList.toggle("active");
                var content = this.nextElementSibling;
                if (content.style.display === "block") {
                    content.style.display = "none";
                } else {
                    content.style.display = "block";
                }
            });
        }
        </script>'''
    
    def _escape_html(self, text):
        """Экранирует HTML символы"""
        if not isinstance(text, str):
            text = str(text)
        
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#39;'))
    
    def _generate_minimal_report(self, elapsed_time):
        """Генерирует минимальный отчет в случае ошибки"""
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Отчет по импорту моделей</title>
</head>
<body>
    <h1>Отчет по импорту моделей</h1>
    <p>Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>Время выполнения: {elapsed_time:.2f} секунд</p>
    <h2>Статистика</h2>
    <p>Всего моделей: {self.statistics['total_models']}</p>
    <p>Успешно обработано: {self.statistics['processed_models']}</p>
    <p>Ошибок: {self.statistics['failed_models']}</p>
    <p>Создано материалов: {self.statistics['created_materials']}</p>
    <p>Примечание: Полный отчет не может быть сгенерирован из-за ошибки.</p>
</body>
</html>'''
    
    def show_report(self):
        """Показывает отчет в браузере"""
        try:
            report_file = self.generate_report()
            if report_file and os.path.exists(report_file):
                webbrowser.open(f"file://{report_file}")
                print(f"Отчет открыт в браузере: {report_file}")
            else:
                print("Не удалось сгенерировать отчет")
        except Exception as e:
            print(f"Ошибка открытия отчета: {e}")
    
    def show_log(self):
        """Показывает файл лога"""
        try:
            if not os.path.exists(self.log_file):
                print(f"Лог файл не найден: {self.log_file}")
                return
            
            # Пытаемся открыть в текстовом редакторе Houdini
            try:
                import hou
                desktop = hou.ui.curDesktop()
                textport = desktop.findPaneTab("textport")
                
                if textport:
                    with open(self.log_file, 'r', encoding='utf-8') as f:
                        log_content = f.read()
                    textport.setContents(log_content)
                    print("Лог отображен в textport")
                else:
                    self._open_log_external()
            except Exception:
                self._open_log_external()
                
        except Exception as e:
            print(f"Ошибка открытия лога: {e}")
    
    def _open_log_external(self):
        """Открывает лог во внешнем редакторе"""
        try:
            print(f"Лог сохранён в: {self.log_file}")
            
            import subprocess
            import platform
            
            system = platform.system()
            if system == 'Windows':
                subprocess.Popen(['notepad', self.log_file])
            elif system == 'Darwin':  # macOS
                subprocess.Popen(['open', self.log_file])
            else:  # Linux и другие Unix-подобные
                subprocess.Popen(['xdg-open', self.log_file])
                
        except Exception as e:
            print(f"Не удалось открыть лог автоматически: {e}")
            print(f"Откройте файл вручную: {self.log_file}")
    
    def get_statistics(self):
        """Возвращает статистику импорта"""
        return self.statistics.copy()
    
    def get_log_file_path(self):
        """Возвращает путь к файлу лога"""
        return self.log_file
    
    def get_report_file_path(self):
        """Возвращает путь к файлу отчета"""
        return self.report_file
    
    def log_udim_sequence_detected(self, sequence_name, tile_count, udim_range):
        """Логирует обнаружение UDIM последовательности"""
        try:
            message = f"UDIM последовательность '{sequence_name}': {tile_count} тайлов ({udim_range[0]}-{udim_range[1]})"
            self.logger.info(message)
            
            # Добавляем в статистику
            if not hasattr(self, 'udim_statistics'):
                self.udim_statistics = {'sequences': 0, 'total_tiles': 0}
            
            self.udim_statistics['sequences'] += 1
            self.udim_statistics['total_tiles'] += tile_count
            
        except Exception as e:
            print(f"Ошибка логирования UDIM последовательности: {e}")

    def log_udim_statistics(self):
        """Логирует общую статистику UDIM"""
        try:
            if hasattr(self, 'udim_statistics'):
                stats = self.udim_statistics
                self.logger.info("=" * 50)
                self.logger.info("UDIM СТАТИСТИКА")
                self.logger.info("=" * 50)
                self.logger.info(f"Всего UDIM последовательностей: {stats['sequences']}")
                self.logger.info(f"Всего UDIM тайлов: {stats['total_tiles']}")
                if stats['sequences'] > 0:
                    avg_tiles = stats['total_tiles'] / stats['sequences']
                    self.logger.info(f"Среднее количество тайлов на последовательность: {avg_tiles:.1f}")
                self.logger.info("=" * 50)
        except Exception as e:
            print(f"Ошибка логирования UDIM статистики: {e}")