"""
Диалог с расширенными настройками импорта моделей - с поддержкой MaterialX и сетки
"""
import hou
import os
import json
from PySide2 import QtWidgets, QtCore

# Импортируем константы, если доступны
try:
    from constants import DEFAULT_SETTINGS, VALIDATION_RULES, PATHS, validate_settings
except ImportError:
    # Fallback константы
    DEFAULT_SETTINGS = {
        "import_mode": "separate",
        "material_type": "principledshader",
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
        "enable_udim": True,
        "udim_auto_detect": True,
        "udim_min_tiles": 2,
        "udim_validate_sequence": True,
        "udim_show_statistics": True,
        # Настройки сетки
        "enable_grid_layout": True,
        "grid_spacing": 10.0,
        "auto_calculate_grid": True,
        "grid_columns": 0  # 0 = автоматически
    }
    
    VALIDATION_RULES = {
        "import_mode": ["separate", "grouped", "merged"],
        "material_type": ["principledshader", "materialx", "redshift::Material", "material"],
        "texture_resolution": ["original", "1K", "2K", "4K"],
        "scale_factor_min": 0.01,
        "scale_factor_max": 100.0,
        "weld_threshold_min": 0.0001,
        "weld_threshold_max": 0.1,
        "grid_spacing_min": 1.0,
        "grid_spacing_max": 100.0
    }
    
    PATHS = {"settings_filename": "import_settings.json"}
    
    def validate_settings(settings_dict):
        return []


class ImportSettings:
    """Класс для хранения настроек импорта с валидацией, UDIM и MaterialX поддержкой"""
    
    def __init__(self):
        # Инициализируем настройки значениями по умолчанию
        self._init_default_settings()
    
    def _init_default_settings(self):
        """Инициализирует настройки значениями по умолчанию"""
        for key, value in DEFAULT_SETTINGS.items():
            setattr(self, key, value)
    
    def validate(self):
        """Валидирует текущие настройки"""
        errors = []
        
        # Проверяем UDIM настройки
        if hasattr(self, 'udim_min_tiles'):
            if not isinstance(self.udim_min_tiles, int) or self.udim_min_tiles < 2 or self.udim_min_tiles > 20:
                errors.append("udim_min_tiles должен быть между 2 и 20")
        
        # Проверяем настройки сетки
        if hasattr(self, 'grid_spacing'):
            if not isinstance(self.grid_spacing, (int, float)) or self.grid_spacing < 1.0 or self.grid_spacing > 100.0:
                errors.append("grid_spacing должен быть между 1.0 и 100.0")
        
        if hasattr(self, 'grid_columns'):
            if not isinstance(self.grid_columns, int) or self.grid_columns < 0 or self.grid_columns > 50:
                errors.append("grid_columns должен быть между 0 и 50")
        
        # Проверяем булевы значения
        bool_settings = [
            'enable_udim', 'udim_auto_detect', 'udim_validate_sequence', 'udim_show_statistics',
            'use_cache', 'auto_assign_textures', 'create_missing_uvs', 'remove_namespaces', 
            'create_lods', 'triangulate', 'weld_vertices', 'generate_report', 'show_import_log', 
            'debug_mode', 'organize_nodes', 'center_pivots', 'convert_to_assets',
            'enable_grid_layout', 'auto_calculate_grid'
        ]
        
        for setting in bool_settings:
            if hasattr(self, setting):
                value = getattr(self, setting)
                if not isinstance(value, bool):
                    errors.append(f"{setting} должен быть логическим значением (True/False)")
        
        # Проверяем режим импорта
        if hasattr(self, 'import_mode') and self.import_mode not in ["separate", "grouped", "merged"]:
            errors.append(f"Некорректный режим импорта: {self.import_mode}")
        
        # Проверяем тип материала (теперь включая MaterialX)
        valid_materials = ["principledshader", "materialx", "redshift::Material", "material"]
        if hasattr(self, 'material_type') and self.material_type not in valid_materials:
            errors.append(f"Некорректный тип материала: {self.material_type}. Допустимые: {valid_materials}")
        
        # Проверяем масштаб
        if hasattr(self, 'scale_factor'):
            if not isinstance(self.scale_factor, (int, float)) or self.scale_factor <= 0:
                errors.append("scale_factor должен быть положительным числом")
        
        return errors
    
    def to_dict(self):
        """Преобразует настройки в словарь"""
        return {key: getattr(self, key, None) for key in DEFAULT_SETTINGS.keys()}
    
    def from_dict(self, settings_dict):
        """Загружает настройки из словаря"""
        if not isinstance(settings_dict, dict):
            return
        
        for key, value in settings_dict.items():
            if key in DEFAULT_SETTINGS:
                # Проверяем тип значения
                default_value = DEFAULT_SETTINGS[key]
                try:
                    # Приводим к правильному типу
                    if isinstance(default_value, bool):
                        setattr(self, key, bool(value))
                    elif isinstance(default_value, (int, float)):
                        setattr(self, key, type(default_value)(value))
                    else:
                        setattr(self, key, value)
                except (ValueError, TypeError):
                    # Если не удалось преобразовать, оставляем значение по умолчанию
                    print(f"Предупреждение: Некорректное значение для {key}: {value}")
    
    def copy(self):
        """Создает копию настроек"""
        new_settings = ImportSettings()
        new_settings.from_dict(self.to_dict())
        return new_settings
    

class SettingsDialog(QtWidgets.QDialog):
    """Диалог настроек на базе PyQt с поддержкой MaterialX и сетки"""
    
    def __init__(self, settings, parent=None):
        super(SettingsDialog, self).__init__(parent)
        
        # Проверяем и подготавливаем настройки
        self.settings = self._prepare_settings(settings)
        
        # Инициализируем UI
        self._init_ui()
        
        # Применяем настройки к виджетам
        self._apply_settings_to_widgets()
    
    def _prepare_settings(self, settings):
        """Подготавливает и валидирует настройки"""
        if settings is None:
            settings = ImportSettings()
        elif not isinstance(settings, ImportSettings):
            # Пытаемся преобразовать из словаря
            new_settings = ImportSettings()
            if isinstance(settings, dict):
                new_settings.from_dict(settings)
            settings = new_settings
        
        # Валидируем настройки
        errors = settings.validate()
        if errors:
            print("Предупреждения в настройках:")
            for error in errors:
                print(f"  - {error}")
        
        return settings
    
    def _init_ui(self):
        """Инициализация интерфейса с обработкой ошибок"""
        try:
            self.setWindowTitle("Настройки импорта моделей")
            self.setMinimumWidth(650)
            self.setMinimumHeight(600)
            
            # Создаем основной layout
            main_layout = QtWidgets.QVBoxLayout(self)
            
            # Создаем вкладки
            self.tabs = QtWidgets.QTabWidget()
            
            # Заполняем вкладки
            self._create_tabs()
            
            # Добавляем кнопки
            buttons_layout = self._create_buttons()
            
            # Собираем layout
            main_layout.addWidget(self.tabs)
            main_layout.addLayout(buttons_layout)
            
        except Exception as e:
            print(f"Ошибка инициализации UI: {e}")
            self._create_minimal_ui()
    
    def _create_tabs(self):
        """Создает все вкладки"""
        try:
            self.tabs.addTab(self._create_main_tab(), "Основные")
            self.tabs.addTab(self._create_material_tab(), "Материалы")
            self.tabs.addTab(self._create_texture_tab(), "Текстуры")
            self.tabs.addTab(self._create_geometry_tab(), "Геометрия")
            self.tabs.addTab(self._create_layout_tab(), "Размещение")
            self.tabs.addTab(self._create_report_tab(), "Отчеты")
        except Exception as e:
            print(f"Ошибка создания вкладок: {e}")
    
    def _create_main_tab(self):
        """Создание вкладки основных настроек"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        
        try:
            # Группа режима импорта
            import_group = self._create_import_mode_group()
            layout.addWidget(import_group)
            
            # Масштаб
            scale_group = self._create_scale_group()
            layout.addWidget(scale_group)
            
            # Кэширование
            cache_group = self._create_cache_group()
            layout.addWidget(cache_group)
            
            layout.addStretch(1)
            
        except Exception as e:
            print(f"Ошибка создания основной вкладки: {e}")
            layout.addWidget(QtWidgets.QLabel("Ошибка загрузки основных настроек"))
        
        tab.setLayout(layout)
        return tab
    
    def _create_material_tab(self):
        """Создание отдельной вкладки для материалов с поддержкой MaterialX"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        
        try:
            # Группа типа материала с поддержкой MaterialX
            material_group = self._create_material_type_group()
            layout.addWidget(material_group)
            
            # Информация о MaterialX
            materialx_info = self._create_materialx_info_group()
            layout.addWidget(materialx_info)
            
            layout.addStretch(1)
            
        except Exception as e:
            print(f"Ошибка создания вкладки материалов: {e}")
            layout.addWidget(QtWidgets.QLabel("Ошибка загрузки настроек материалов"))
        
        tab.setLayout(layout)
        return tab
    
    def _create_layout_tab(self):
        """Создание новой вкладки для настроек размещения"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        
        try:
            # Настройки сетки
            grid_group = self._create_grid_settings_group()
            layout.addWidget(grid_group)
            
            # Дополнительные настройки размещения
            additional_group = self._create_additional_layout_settings_group()
            layout.addWidget(additional_group)
            
            layout.addStretch(1)
            
        except Exception as e:
            print(f"Ошибка создания вкладки размещения: {e}")
            layout.addWidget(QtWidgets.QLabel("Ошибка загрузки настроек размещения"))
        
        tab.setLayout(layout)
        return tab
    
    def _create_import_mode_group(self):
        """Создает группу режима импорта"""
        group = QtWidgets.QGroupBox("Режим импорта")
        layout = QtWidgets.QVBoxLayout()
        
        self.radio_separate = QtWidgets.QRadioButton("Отдельные геометрии")
        self.radio_separate.setToolTip("Создает отдельную geo-ноду для каждой модели")
        
        self.radio_grouped = QtWidgets.QRadioButton("Группировать по папкам")
        self.radio_grouped.setToolTip("Группирует модели по папкам в подсети")
        
        self.radio_merged = QtWidgets.QRadioButton("Все в один узел")
        self.radio_merged.setToolTip("Импортирует все модели в одну geo-ноду с контроллером сетки")
        
        layout.addWidget(self.radio_separate)
        layout.addWidget(self.radio_grouped)
        layout.addWidget(self.radio_merged)
        
        group.setLayout(layout)
        return group
    
    def _create_material_type_group(self):
        """Создает группу типа материала с поддержкой MaterialX"""
        group = QtWidgets.QGroupBox("Тип материала")
        layout = QtWidgets.QVBoxLayout()
        
        self.radio_principled = QtWidgets.QRadioButton("Principled Shader")
        self.radio_principled.setToolTip("Использует стандартный Principled Shader")
        
        self.radio_materialx = QtWidgets.QRadioButton("MaterialX Solaris")
        self.radio_materialx.setToolTip("Использует MaterialX материалы для Solaris рендеринга")
        
        self.radio_redshift = QtWidgets.QRadioButton("Redshift Material")
        self.radio_redshift.setToolTip("Использует материалы Redshift")
        
        self.radio_standard = QtWidgets.QRadioButton("Standard Material")
        self.radio_standard.setToolTip("Использует стандартные материалы Houdini")
        
        layout.addWidget(self.radio_principled)
        layout.addWidget(self.radio_materialx)
        layout.addWidget(self.radio_redshift)
        layout.addWidget(self.radio_standard)
        
        group.setLayout(layout)
        return group
    
    def _create_materialx_info_group(self):
        """Создает информационную группу о MaterialX"""
        group = QtWidgets.QGroupBox("Информация о MaterialX")
        layout = QtWidgets.QVBoxLayout()
        
        info_text = QtWidgets.QLabel(
            "MaterialX Solaris материалы предназначены для использования с:\n"
            "• USD рендерингом\n"
            "• Karma рендерингом\n"
            "• Solaris workflow\n"
            "• Современными PBR пайплайнами\n\n"
            "Поддерживаются все современные текстурные карты включая UDIM."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
        
        layout.addWidget(info_text)
        
        group.setLayout(layout)
        return group
    
    def _create_grid_settings_group(self):
        """Создает группу настроек сетки"""
        group = QtWidgets.QGroupBox("Настройки сетки (для режима 'Все в один узел')")
        layout = QtWidgets.QVBoxLayout()
        
        self.enable_grid_checkbox = QtWidgets.QCheckBox("Включить размещение по сетке")
        self.enable_grid_checkbox.setToolTip("Автоматически размещает модели в сетке")
        
        self.auto_grid_checkbox = QtWidgets.QCheckBox("Автоматически вычислять сетку")
        self.auto_grid_checkbox.setToolTip("Автоматически определяет оптимальное количество колонок")
        
        # Расстояние между моделями
        spacing_layout = QtWidgets.QHBoxLayout()
        spacing_label = QtWidgets.QLabel("Расстояние между моделями:")
        self.grid_spacing_spinner = QtWidgets.QDoubleSpinBox()
        self.grid_spacing_spinner.setRange(1.0, 100.0)
        self.grid_spacing_spinner.setValue(10.0)
        self.grid_spacing_spinner.setSingleStep(1.0)
        self.grid_spacing_spinner.setDecimals(1)
        self.grid_spacing_spinner.setSuffix(" единиц")
        self.grid_spacing_spinner.setToolTip("Расстояние между центрами моделей в сетке")
        
        spacing_layout.addWidget(spacing_label)
        spacing_layout.addWidget(self.grid_spacing_spinner)
        spacing_layout.addStretch()
        
        # Количество колонок
        columns_layout = QtWidgets.QHBoxLayout()
        columns_label = QtWidgets.QLabel("Колонок в сетке:")
        self.grid_columns_spinner = QtWidgets.QSpinBox()
        self.grid_columns_spinner.setRange(0, 50)
        self.grid_columns_spinner.setValue(0)
        self.grid_columns_spinner.setSpecialValueText("Авто")
        self.grid_columns_spinner.setToolTip("Количество колонок в сетке (0 = автоматически)")
        
        columns_layout.addWidget(columns_label)
        columns_layout.addWidget(self.grid_columns_spinner)
        columns_layout.addStretch()
        
        # Связываем автоматический режим с доступностью спиннера колонок
        def toggle_columns_spinner(enabled):
            self.grid_columns_spinner.setEnabled(not enabled)
        
        self.auto_grid_checkbox.toggled.connect(toggle_columns_spinner)
        
        layout.addWidget(self.enable_grid_checkbox)
        layout.addWidget(self.auto_grid_checkbox)
        layout.addLayout(spacing_layout)
        layout.addLayout(columns_layout)
        
        group.setLayout(layout)
        return group

    def _create_materialx_workflow_group(self):
        """Создает группу настроек MaterialX workflow"""
        group = QtWidgets.QGroupBox("MaterialX Workflow (расширенные настройки)")
        layout = QtWidgets.QVBoxLayout()
        
        # Тип MaterialX workflow
        workflow_layout = QtWidgets.QHBoxLayout()
        workflow_label = QtWidgets.QLabel("MaterialX тип:")
        self.materialx_workflow_combo = QtWidgets.QComboBox()
        self.materialx_workflow_combo.addItems([
            "Karma Material (рекомендуется)", 
            "MaterialX Standard", 
            "USD Preview", 
            "Автоматический выбор"
        ])
        self.materialx_workflow_combo.setCurrentIndex(3)  # Автоматический
        
        workflow_layout.addWidget(workflow_label)
        workflow_layout.addWidget(self.materialx_workflow_combo)
        workflow_layout.addStretch()
        
        # Дополнительные опции
        self.materialx_force_karma = QtWidgets.QCheckBox("Принудительно использовать Karma Material")
        self.materialx_force_karma.setToolTip("Создает Karma Material даже если Standard Surface доступен")
        
        self.materialx_advanced_nodes = QtWidgets.QCheckBox("Использовать расширенные MaterialX ноды")
        self.materialx_advanced_nodes.setToolTip("Включает дополнительные MaterialX ноды для сложных материалов")
        
        layout.addLayout(workflow_layout)
        layout.addWidget(self.materialx_force_karma)
        layout.addWidget(self.materialx_advanced_nodes)
        
        group.setLayout(layout)
        return group

    
    def _create_additional_layout_settings_group(self):
        """Создает группу дополнительных настроек размещения"""
        group = QtWidgets.QGroupBox("Дополнительные настройки размещения")
        layout = QtWidgets.QVBoxLayout()
        
        self.organize_checkbox = QtWidgets.QCheckBox("Организовывать ноды в network view")
        self.organize_checkbox.setToolTip("Автоматически размещает созданные ноды в network editor")
        
        self.pivot_checkbox = QtWidgets.QCheckBox("Центрировать опорные точки")
        self.pivot_checkbox.setToolTip("Перемещает опорные точки в центр объектов")
        
        layout.addWidget(self.organize_checkbox)
        layout.addWidget(self.pivot_checkbox)
        
        group.setLayout(layout)
        return group
    
    def _create_scale_group(self):
        """Создает группу масштаба"""
        group = QtWidgets.QGroupBox("Масштаб импорта")
        layout = QtWidgets.QHBoxLayout()
        
        label = QtWidgets.QLabel("Коэффициент:")
        self.scale_spinner = QtWidgets.QDoubleSpinBox()
        self.scale_spinner.setRange(
            VALIDATION_RULES.get("scale_factor_min", 0.01), 
            VALIDATION_RULES.get("scale_factor_max", 100.0)
        )
        self.scale_spinner.setSingleStep(0.1)
        self.scale_spinner.setDecimals(3)
        self.scale_spinner.setToolTip("Масштабирующий коэффициент для импортируемых моделей")
        
        layout.addWidget(label)
        layout.addWidget(self.scale_spinner)
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    def _create_cache_group(self):
        """Создает группу кэширования"""
        group = QtWidgets.QGroupBox("Кэширование")
        layout = QtWidgets.QVBoxLayout()
        
        self.cache_checkbox = QtWidgets.QCheckBox("Использовать кэширование")
        self.cache_checkbox.setToolTip("Кэширование ускоряет повторные импорты")
        
        layout.addWidget(self.cache_checkbox)
        
        group.setLayout(layout)
        return group
    
    def _create_texture_tab(self):
        """Создание вкладки настроек текстур с UDIM поддержкой"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        
        try:
            # Разрешение текстур
            resolution_group = self._create_texture_resolution_group()
            layout.addWidget(resolution_group)
            
            # Настройки текстур
            textures_group = self._create_texture_settings_group()
            layout.addWidget(textures_group)
            
            # UDIM настройки
            udim_group = self._create_udim_settings_group()
            layout.addWidget(udim_group)
            
            layout.addStretch(1)
            
        except Exception as e:
            print(f"Ошибка создания вкладки текстур: {e}")
            layout.addWidget(QtWidgets.QLabel("Ошибка загрузки настроек текстур"))
        
        tab.setLayout(layout)
        return tab
    
    def _create_texture_resolution_group(self):
        """Создает группу разрешения текстур"""
        group = QtWidgets.QGroupBox("Разрешение текстур")
        layout = QtWidgets.QHBoxLayout()
        
        label = QtWidgets.QLabel("Целевое разрешение:")
        self.combo_resolution = QtWidgets.QComboBox()
        self.combo_resolution.addItems(["Оригинальное", "1K", "2K", "4K"])
        self.combo_resolution.setToolTip("Целевое разрешение для текстур")
        
        layout.addWidget(label)
        layout.addWidget(self.combo_resolution)
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    def _create_texture_settings_group(self):
        """Создает группу настроек текстур"""
        group = QtWidgets.QGroupBox("Настройки текстур")
        layout = QtWidgets.QVBoxLayout()
        
        self.auto_texture_checkbox = QtWidgets.QCheckBox("Автоматически назначать текстуры")
        self.auto_texture_checkbox.setToolTip("Автоматический поиск и назначение текстур по ключевым словам")
        
        self.create_uv_checkbox = QtWidgets.QCheckBox("Создавать UV если отсутствуют")
        self.create_uv_checkbox.setToolTip("Создает UV-развертку для геометрии без UV")
        
        layout.addWidget(self.auto_texture_checkbox)
        layout.addWidget(self.create_uv_checkbox)
        
        group.setLayout(layout)
        return group

    def _create_udim_settings_group(self):
        """Создает группу настроек UDIM"""
        group = QtWidgets.QGroupBox("UDIM Настройки")
        layout = QtWidgets.QVBoxLayout()
        
        self.enable_udim_checkbox = QtWidgets.QCheckBox("Включить поддержку UDIM")
        self.enable_udim_checkbox.setToolTip("Автоматически обнаруживает и обрабатывает UDIM текстуры")
        
        self.udim_auto_detect_checkbox = QtWidgets.QCheckBox("Автоматическое обнаружение UDIM")
        self.udim_auto_detect_checkbox.setToolTip("Автоматически определяет UDIM последовательности")
        
        self.udim_validate_checkbox = QtWidgets.QCheckBox("Валидировать UDIM последовательности")
        self.udim_validate_checkbox.setToolTip("Проверяет корректность UDIM тайлов")
        
        self.udim_show_stats_checkbox = QtWidgets.QCheckBox("Показывать статистику UDIM")
        self.udim_show_stats_checkbox.setToolTip("Выводит подробную информацию о найденных UDIM")
        
        # Минимальное количество тайлов
        min_tiles_layout = QtWidgets.QHBoxLayout()
        min_tiles_label = QtWidgets.QLabel("Минимум тайлов для UDIM:")
        self.udim_min_tiles_spinner = QtWidgets.QSpinBox()
        self.udim_min_tiles_spinner.setRange(2, 20)
        self.udim_min_tiles_spinner.setValue(2)
        self.udim_min_tiles_spinner.setToolTip("Минимальное количество тайлов для определения как UDIM")
        
        min_tiles_layout.addWidget(min_tiles_label)
        min_tiles_layout.addWidget(self.udim_min_tiles_spinner)
        min_tiles_layout.addStretch()
        
        layout.addWidget(self.enable_udim_checkbox)
        layout.addWidget(self.udim_auto_detect_checkbox)
        layout.addWidget(self.udim_validate_checkbox)
        layout.addWidget(self.udim_show_stats_checkbox)
        layout.addLayout(min_tiles_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_geometry_tab(self):
        """Создание вкладки настроек геометрии"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        
        try:
            # Общие настройки геометрии
            geo_group = self._create_geometry_settings_group()
            layout.addWidget(geo_group)
            
            # Сварка вершин
            weld_group = self._create_weld_settings_group()
            layout.addWidget(weld_group)
            
            layout.addStretch(1)
            
        except Exception as e:
            print(f"Ошибка создания вкладки геометрии: {e}")
            layout.addWidget(QtWidgets.QLabel("Ошибка загрузки настроек геометрии"))
        
        tab.setLayout(layout)
        return tab
    
    def _create_geometry_settings_group(self):
        """Создает группу настроек геометрии"""
        group = QtWidgets.QGroupBox("Настройки геометрии")
        layout = QtWidgets.QVBoxLayout()
        
        self.remove_namespace_checkbox = QtWidgets.QCheckBox("Удалять пространства имен")
        self.remove_namespace_checkbox.setToolTip("Убирает namespace из имен объектов")
        
        self.create_lod_checkbox = QtWidgets.QCheckBox("Создавать LOD-уровни")
        self.create_lod_checkbox.setToolTip("Автоматически создает уровни детализации")
        
        self.triangulate_checkbox = QtWidgets.QCheckBox("Триангулировать геометрию")
        self.triangulate_checkbox.setToolTip("Преобразует всю геометрию в треугольники")
        
        layout.addWidget(self.remove_namespace_checkbox)
        layout.addWidget(self.create_lod_checkbox)
        layout.addWidget(self.triangulate_checkbox)
        
        group.setLayout(layout)
        return group
    
    def _create_weld_settings_group(self):
        """Создает группу настроек сварки вершин"""
        group = QtWidgets.QGroupBox("Сварка вершин")
        layout = QtWidgets.QVBoxLayout()
        
        self.weld_checkbox = QtWidgets.QCheckBox("Сваривать вершины")
        self.weld_checkbox.setToolTip("Объединяет близко расположенные вершины")
        
        # Порог сварки
        threshold_layout = QtWidgets.QHBoxLayout()
        threshold_label = QtWidgets.QLabel("Порог сварки:")
        self.threshold_spinner = QtWidgets.QDoubleSpinBox()
        self.threshold_spinner.setRange(
            VALIDATION_RULES.get("weld_threshold_min", 0.0001),
            VALIDATION_RULES.get("weld_threshold_max", 0.1)
        )
        self.threshold_spinner.setSingleStep(0.001)
        self.threshold_spinner.setDecimals(4)
        self.threshold_spinner.setToolTip("Максимальное расстояние для объединения вершин")
        
        threshold_layout.addWidget(threshold_label)
        threshold_layout.addWidget(self.threshold_spinner)
        threshold_layout.addStretch()
        
        # Связываем активацию чекбокса с доступностью спиннера
        self.weld_checkbox.toggled.connect(self.threshold_spinner.setEnabled)
        
        layout.addWidget(self.weld_checkbox)
        layout.addLayout(threshold_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_report_tab(self):
        """Создание вкладки настроек отчетов"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        
        try:
            # Настройки отчетов
            report_group = self._create_report_settings_group()
            layout.addWidget(report_group)
            
            # Дополнительные настройки
            additional_group = self._create_additional_settings_group()
            layout.addWidget(additional_group)
            
            layout.addStretch(1)
            
        except Exception as e:
            print(f"Ошибка создания вкладки отчетов: {e}")
            layout.addWidget(QtWidgets.QLabel("Ошибка загрузки настроек отчетов"))
        
        tab.setLayout(layout)
        return tab
    
    def _create_report_settings_group(self):
        """Создает группу настроек отчетов"""
        group = QtWidgets.QGroupBox("Настройки отчетов")
        layout = QtWidgets.QVBoxLayout()
        
        self.generate_report_checkbox = QtWidgets.QCheckBox("Генерировать отчет об импорте")
        self.generate_report_checkbox.setToolTip("Создает HTML-отчет с результатами импорта")
        
        self.show_log_checkbox = QtWidgets.QCheckBox("Показывать лог импорта")
        self.show_log_checkbox.setToolTip("Отображает подробный лог процесса импорта")
        
        self.debug_checkbox = QtWidgets.QCheckBox("Режим отладки")
        self.debug_checkbox.setToolTip("Включает подробное логирование для отладки")
        
        layout.addWidget(self.generate_report_checkbox)
        layout.addWidget(self.show_log_checkbox)
        layout.addWidget(self.debug_checkbox)
        
        group.setLayout(layout)
        return group
    
    def _create_additional_settings_group(self):
        """Создает группу дополнительных настроек"""
        group = QtWidgets.QGroupBox("Дополнительные настройки")
        layout = QtWidgets.QVBoxLayout()
        
        self.asset_checkbox = QtWidgets.QCheckBox("Конвертировать в ассеты")
        self.asset_checkbox.setToolTip("Преобразует импортированные модели в цифровые ассеты")
        
        layout.addWidget(self.asset_checkbox)
        
        group.setLayout(layout)
        return group
    
    def _create_buttons(self):
        """Создает кнопки диалога"""
        layout = QtWidgets.QHBoxLayout()
        
        # Кнопка сброса настроек
        reset_button = QtWidgets.QPushButton("Сброс")
        reset_button.setToolTip("Сбрасывает все настройки к значениям по умолчанию")
        reset_button.clicked.connect(self._reset_settings)
        
        # Основные кнопки
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self
        )
        buttons.accepted.connect(self._accept_with_validation)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(reset_button)
        layout.addStretch()
        layout.addWidget(buttons)
        
        return layout
    
    def _create_minimal_ui(self):
        """Создает минимальный UI в случае ошибки"""
        layout = QtWidgets.QVBoxLayout(self)
        
        label = QtWidgets.QLabel("Ошибка загрузки диалога настроек.\nИспользуются настройки по умолчанию.")
        layout.addWidget(label)
        
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(buttons)
    
    def _apply_settings_to_widgets(self):
        """Применяет текущие настройки к виджетам"""
        try:
            # Режим импорта
            if hasattr(self, 'radio_separate'):
                if self.settings.import_mode == "separate":
                    self.radio_separate.setChecked(True)
                elif self.settings.import_mode == "grouped":
                    self.radio_grouped.setChecked(True)
                else:
                    self.radio_merged.setChecked(True)
            
            # Тип материала (включая MaterialX)
            if hasattr(self, 'radio_principled'):
                if self.settings.material_type == "principledshader":
                    self.radio_principled.setChecked(True)
                elif self.settings.material_type == "materialx":
                    self.radio_materialx.setChecked(True)
                elif self.settings.material_type == "redshift::Material":
                    self.radio_redshift.setChecked(True)
                else:
                    self.radio_standard.setChecked(True)
            
            # Масштаб
            if hasattr(self, 'scale_spinner'):
                self.scale_spinner.setValue(self.settings.scale_factor)
            
            # Кэширование
            if hasattr(self, 'cache_checkbox'):
                self.cache_checkbox.setChecked(self.settings.use_cache)
            
            # Разрешение текстур
            if hasattr(self, 'combo_resolution'):
                resolution_map = {"original": 0, "1K": 1, "2K": 2, "4K": 3}
                index = resolution_map.get(self.settings.texture_resolution, 0)
                self.combo_resolution.setCurrentIndex(index)
            
            # Настройки текстур
            if hasattr(self, 'auto_texture_checkbox'):
                self.auto_texture_checkbox.setChecked(self.settings.auto_assign_textures)
            if hasattr(self, 'create_uv_checkbox'):
                self.create_uv_checkbox.setChecked(self.settings.create_missing_uvs)
            
            # Настройки геометрии
            if hasattr(self, 'remove_namespace_checkbox'):
                self.remove_namespace_checkbox.setChecked(self.settings.remove_namespaces)
            if hasattr(self, 'create_lod_checkbox'):
                self.create_lod_checkbox.setChecked(self.settings.create_lods)
            if hasattr(self, 'triangulate_checkbox'):
                self.triangulate_checkbox.setChecked(self.settings.triangulate)
            
            # Сварка вершин
            if hasattr(self, 'weld_checkbox'):
                self.weld_checkbox.setChecked(self.settings.weld_vertices)
            if hasattr(self, 'threshold_spinner'):
                self.threshold_spinner.setValue(self.settings.weld_threshold)
                self.threshold_spinner.setEnabled(self.settings.weld_vertices)
            
            # Настройки отчетов
            if hasattr(self, 'generate_report_checkbox'):
                self.generate_report_checkbox.setChecked(self.settings.generate_report)
            if hasattr(self, 'show_log_checkbox'):
                self.show_log_checkbox.setChecked(self.settings.show_import_log)
            if hasattr(self, 'debug_checkbox'):
                self.debug_checkbox.setChecked(self.settings.debug_mode)
            
            # Дополнительные настройки
            if hasattr(self, 'organize_checkbox'):
                self.organize_checkbox.setChecked(self.settings.organize_nodes)
            if hasattr(self, 'pivot_checkbox'):
                self.pivot_checkbox.setChecked(self.settings.center_pivots)
            if hasattr(self, 'asset_checkbox'):
                self.asset_checkbox.setChecked(self.settings.convert_to_assets)
            
            # UDIM настройки
            if hasattr(self, 'enable_udim_checkbox'):
                self.enable_udim_checkbox.setChecked(getattr(self.settings, 'enable_udim', True))
            if hasattr(self, 'udim_auto_detect_checkbox'):
                self.udim_auto_detect_checkbox.setChecked(getattr(self.settings, 'udim_auto_detect', True))
            if hasattr(self, 'udim_validate_checkbox'):
                self.udim_validate_checkbox.setChecked(getattr(self.settings, 'udim_validate_sequence', True))
            if hasattr(self, 'udim_show_stats_checkbox'):
                self.udim_show_stats_checkbox.setChecked(getattr(self.settings, 'udim_show_statistics', True))
            if hasattr(self, 'udim_min_tiles_spinner'):
                self.udim_min_tiles_spinner.setValue(getattr(self.settings, 'udim_min_tiles', 2))
            
            # Настройки сетки
            if hasattr(self, 'enable_grid_checkbox'):
                self.enable_grid_checkbox.setChecked(getattr(self.settings, 'enable_grid_layout', True))
            if hasattr(self, 'auto_grid_checkbox'):
                auto_calc = getattr(self.settings, 'auto_calculate_grid', True)
                self.auto_grid_checkbox.setChecked(auto_calc)
                if hasattr(self, 'grid_columns_spinner'):
                    self.grid_columns_spinner.setEnabled(not auto_calc)
            if hasattr(self, 'grid_spacing_spinner'):
                self.grid_spacing_spinner.setValue(getattr(self.settings, 'grid_spacing', 10.0))
            if hasattr(self, 'grid_columns_spinner'):
                self.grid_columns_spinner.setValue(getattr(self.settings, 'grid_columns', 0))
                
        except Exception as e:
            print(f"Ошибка применения настроек к виджетам: {e}")
    
    def _reset_settings(self):
        """Сбрасывает настройки к значениям по умолчанию"""
        try:
            # Создаем новый объект настроек с дефолтными значениями
            self.settings = ImportSettings()
            
            # Применяем к виджетам
            self._apply_settings_to_widgets()
            
            print("Настройки сброшены к значениям по умолчанию")
            
        except Exception as e:
            print(f"Ошибка сброса настроек: {e}")
    
    def _accept_with_validation(self):
        """Принимает настройки с валидацией"""
        try:
            # Получаем настройки из виджетов
            self._collect_settings_from_widgets()
            
            # Валидируем настройки
            errors = self.settings.validate()
            
            if errors:
                # Показываем ошибки пользователю
                error_text = "Обнаружены проблемы с настройками:\n\n" + "\n".join(errors)
                error_text += "\n\nПродолжить с этими настройками?"
                
                reply = QtWidgets.QMessageBox.question(
                    self, "Проблемы с настройками", error_text,
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No
                )
                
                if reply != QtWidgets.QMessageBox.Yes:
                    return
            
            # Принимаем диалог
            self.accept()
            
        except Exception as e:
            print(f"Ошибка при принятии настроек: {e}")
            # В случае ошибки все равно принимаем
            self.accept()
    
    def _collect_settings_from_widgets(self):
        """Собирает настройки из виджетов"""
        try:
            # Режим импорта
            if hasattr(self, 'radio_separate'):
                if self.radio_separate.isChecked():
                    self.settings.import_mode = "separate"
                elif self.radio_grouped.isChecked():
                    self.settings.import_mode = "grouped"
                else:
                    self.settings.import_mode = "merged"
            
            # Тип материала (включая MaterialX)
            if hasattr(self, 'radio_principled'):
                if self.radio_principled.isChecked():
                    self.settings.material_type = "principledshader"
                elif self.radio_materialx.isChecked():
                    self.settings.material_type = "materialx"
                elif self.radio_redshift.isChecked():
                    self.settings.material_type = "redshift::Material"
                else:
                    self.settings.material_type = "material"
            
            # Масштаб
            if hasattr(self, 'scale_spinner'):
                self.settings.scale_factor = self.scale_spinner.value()
            
            # Кэширование
            if hasattr(self, 'cache_checkbox'):
                self.settings.use_cache = self.cache_checkbox.isChecked()
            
            # Разрешение текстур
            if hasattr(self, 'combo_resolution'):
                resolution_values = ["original", "1K", "2K", "4K"]
                index = self.combo_resolution.currentIndex()
                if 0 <= index < len(resolution_values):
                    self.settings.texture_resolution = resolution_values[index]
            
            # Настройки текстур
            if hasattr(self, 'auto_texture_checkbox'):
                self.settings.auto_assign_textures = self.auto_texture_checkbox.isChecked()
            if hasattr(self, 'create_uv_checkbox'):
                self.settings.create_missing_uvs = self.create_uv_checkbox.isChecked()
            
            # Настройки геометрии
            if hasattr(self, 'remove_namespace_checkbox'):
                self.settings.remove_namespaces = self.remove_namespace_checkbox.isChecked()
            if hasattr(self, 'create_lod_checkbox'):
                self.settings.create_lods = self.create_lod_checkbox.isChecked()
            if hasattr(self, 'triangulate_checkbox'):
                self.settings.triangulate = self.triangulate_checkbox.isChecked()
            
            # Сварка вершин
            if hasattr(self, 'weld_checkbox'):
                self.settings.weld_vertices = self.weld_checkbox.isChecked()
            if hasattr(self, 'threshold_spinner'):
                self.settings.weld_threshold = self.threshold_spinner.value()
            
            # Настройки отчетов
            if hasattr(self, 'generate_report_checkbox'):
                self.settings.generate_report = self.generate_report_checkbox.isChecked()
            if hasattr(self, 'show_log_checkbox'):
                self.settings.show_import_log = self.show_log_checkbox.isChecked()
            if hasattr(self, 'debug_checkbox'):
                self.settings.debug_mode = self.debug_checkbox.isChecked()
            
            # Дополнительные настройки
            if hasattr(self, 'organize_checkbox'):
                self.settings.organize_nodes = self.organize_checkbox.isChecked()
            if hasattr(self, 'pivot_checkbox'):
                self.settings.center_pivots = self.pivot_checkbox.isChecked()
            if hasattr(self, 'asset_checkbox'):
                self.settings.convert_to_assets = self.asset_checkbox.isChecked()
            
            # UDIM настройки
            if hasattr(self, 'enable_udim_checkbox'):
                self.settings.enable_udim = self.enable_udim_checkbox.isChecked()
            if hasattr(self, 'udim_auto_detect_checkbox'):
                self.settings.udim_auto_detect = self.udim_auto_detect_checkbox.isChecked()
            if hasattr(self, 'udim_validate_checkbox'):
                self.settings.udim_validate_sequence = self.udim_validate_checkbox.isChecked()
            if hasattr(self, 'udim_show_stats_checkbox'):
                self.settings.udim_show_statistics = self.udim_show_stats_checkbox.isChecked()
            if hasattr(self, 'udim_min_tiles_spinner'):
                self.settings.udim_min_tiles = self.udim_min_tiles_spinner.value()
            
            # Настройки сетки
            if hasattr(self, 'enable_grid_checkbox'):
                self.settings.enable_grid_layout = self.enable_grid_checkbox.isChecked()
            if hasattr(self, 'auto_grid_checkbox'):
                self.settings.auto_calculate_grid = self.auto_grid_checkbox.isChecked()
            if hasattr(self, 'grid_spacing_spinner'):
                self.settings.grid_spacing = self.grid_spacing_spinner.value()
            if hasattr(self, 'grid_columns_spinner'):
                self.settings.grid_columns = self.grid_columns_spinner.value()
                
        except Exception as e:
            print(f"Ошибка сбора настроек из виджетов: {e}")


def get_settings_file_path():
    """Возвращает путь к файлу настроек"""
    try:
        import hou
        houdini_user_dir = hou.homeHoudiniDirectory()
        settings_dir = os.path.join(houdini_user_dir, "scripts", "python")
        os.makedirs(settings_dir, exist_ok=True)
        return os.path.join(settings_dir, PATHS["settings_filename"])
    except Exception:
        # Fallback
        import tempfile
        return os.path.join(tempfile.gettempdir(), "houdini_import_settings.json")


def load_saved_settings():
    """Загружает сохраненные настройки"""
    settings = ImportSettings()
    
    try:
        settings_file = get_settings_file_path()
        
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                saved_settings = json.load(f)
                settings.from_dict(saved_settings)
                print(f"Настройки загружены из: {settings_file}")
        else:
            print("Файл настроек не найден, используются значения по умолчанию")
            
    except Exception as e:
        print(f"Не удалось загрузить настройки: {e}")
    
    return settings


def save_settings(settings):
    """Сохраняет настройки в файл"""
    try:
        settings_file = get_settings_file_path()
        settings_dict = settings.to_dict()
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, indent=4, ensure_ascii=False)
        
        print(f"Настройки сохранены в: {settings_file}")
        return True
        
    except Exception as e:
        print(f"Не удалось сохранить настройки: {e}")
        return False


def show_settings_dialog():
    """Показывает диалог настроек и возвращает объект с настройками"""
    try:
        # Загружаем сохраненные настройки
        settings = load_saved_settings()
        
        # Создаем и показываем диалог
        dialog = SettingsDialog(settings)
        result = dialog.exec_()
        
        if result == QtWidgets.QDialog.Accepted:
            # Сохраняем настройки для будущего использования
            save_settings(settings)
            return settings
        else:
            print("Диалог настроек отменен пользователем")
            return None
            
    except Exception as e:
        print(f"Критическая ошибка в диалоге настроек: {e}")
        
        # Возвращаем настройки по умолчанию в случае ошибки
        try:
            default_settings = ImportSettings()
            print("Используются настройки по умолчанию из-за ошибки диалога")
            return default_settings
        except Exception as e2:
            print(f"Не удалось создать даже настройки по умолчанию: {e2}")
            return None