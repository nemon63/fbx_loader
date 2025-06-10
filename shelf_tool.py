"""
Обновленный скрипт для вызова из полки Houdini с поддержкой новой системы MaterialX
"""
import sys
import os
import importlib
import hou
import time


def setup_module_paths():
    """Настраивает пути к модулям с проверкой новых компонентов"""
    houdini_user_dir = hou.homeHoudiniDirectory()
    scripts_path = os.path.join(houdini_user_dir, "scripts", "python", "fbx_loader")
    
    # Альтернативные пути
    possible_paths = [
        scripts_path,
        os.path.join(houdini_user_dir, "python_modules", "fbx_loader"),
        os.path.join(houdini_user_dir, "scripts", "fbx_loader"),
    ]
    
    scripts_path = None
    for path in possible_paths:
        if os.path.exists(path) and os.path.isdir(path):
            # Проверяем наличие основных модулей
            required_modules = ['main.py', 'utils.py', 'material_utils.py']
            if all(os.path.exists(os.path.join(path, module)) for module in required_modules):
                scripts_path = path
                break
    
    if not scripts_path:
        raise ImportError(f"Не удалось найти модули fbx_loader в путях: {possible_paths}")
    
    print(f"Найдены модули в: {scripts_path}")
    
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
        print(f"Добавлен путь в sys.path: {scripts_path}")
    
    return scripts_path


def import_and_reload_modules():
    """Импортирует и перезагружает модули с поддержкой новой системы MaterialX"""
    
    # Основные модули (обязательные)
    core_modules = [
        'constants',
        'utils', 
        'material_utils', 
        'model_processor', 
        'main', 
        'settings_dialog', 
        'logger', 
        'cache_manager'
    ]
    
    # Новые модули MaterialX системы (опциональные)
    materialx_modules = [
        'materialx_builder',
        'principled_builder', 
        'material_builder_manager'
    ]
    
    # Опциональные модули
    optional_modules = [
        'udim_utils'
    ]
    
    modules = {}
    
    # Импорт основных модулей
    for module_name in core_modules:
        try:
            if module_name in sys.modules:
                modules[module_name] = importlib.reload(sys.modules[module_name])
                print(f"✓ Перезагружен основной модуль: {module_name}")
            else:
                modules[module_name] = importlib.import_module(module_name)
                print(f"✓ Импортирован основной модуль: {module_name}")
                
        except ImportError as e:
            print(f"✗ Ошибка импорта основного модуля {module_name}: {e}")
            if module_name in ['constants']:
                print(f"⚠ Модуль {module_name} не критичен, продолжаем")
                modules[module_name] = None
                continue
            raise
        except Exception as e:
            print(f"✗ Неожиданная ошибка при загрузке основного модуля {module_name}: {e}")
            raise
    
    # Импорт MaterialX модулей (не критичные)
    materialx_available = True
    for module_name in materialx_modules:
        try:
            if module_name in sys.modules:
                modules[module_name] = importlib.reload(sys.modules[module_name])
                print(f"✓ Перезагружен MaterialX модуль: {module_name}")
            else:
                modules[module_name] = importlib.import_module(module_name)
                print(f"✓ Импортирован MaterialX модуль: {module_name}")
                
        except ImportError as e:
            print(f"⚠ MaterialX модуль {module_name} недоступен: {e}")
            modules[module_name] = None
            materialx_available = False
        except Exception as e:
            print(f"⚠ Ошибка загрузки MaterialX модуля {module_name}: {e}")
            modules[module_name] = None
            materialx_available = False
    
    # Импорт опциональных модулей
    for module_name in optional_modules:
        try:
            if module_name in sys.modules:
                modules[module_name] = importlib.reload(sys.modules[module_name])
                print(f"✓ Перезагружен опциональный модуль: {module_name}")
            else:
                modules[module_name] = importlib.import_module(module_name)
                print(f"✓ Импортирован опциональный модуль: {module_name}")
                
        except ImportError as e:
            print(f"⚠ Опциональный модуль {module_name} недоступен: {e}")
            modules[module_name] = None
        except Exception as e:
            print(f"⚠ Ошибка загрузки опционального модуля {module_name}: {e}")
            modules[module_name] = None
    
    # Статус системы MaterialX
    if materialx_available:
        print("🎉 Новая система MaterialX полностью загружена!")
    else:
        print("⚠ Новая система MaterialX недоступна, используется legacy режим")
    
    return modules, materialx_available


def check_materialx_capabilities():
    """Проверяет возможности MaterialX системы"""
    try:
        from material_builder_manager import get_material_manager
        
        manager = get_material_manager()
        capabilities = manager.get_capabilities_info()
        
        print("=" * 50)
        print("ПРОВЕРКА ВОЗМОЖНОСТЕЙ MATERIALX")
        print("=" * 50)
        print(f"MaterialX поддержка: {'✓' if capabilities['capabilities']['materialx'] else '✗'}")
        print(f"Principled Shader: {'✓' if capabilities['capabilities']['principled'] else '✗'}")
        print(f"Redshift материалы: {'✓' if capabilities['capabilities']['redshift'] else '✗'}")
        print(f"UDIM поддержка: {'✓' if capabilities['udim_support'] else '✗'}")
        print(f"Доступные типы: {', '.join(capabilities['available_types'])}")
        print(f"Рекомендуемый тип: {capabilities['recommended_type']}")
        print("=" * 50)
        
        return capabilities
        
    except ImportError:
        print("⚠ MaterialBuilderManager недоступен, возможности недоступны")
        return None
    except Exception as e:
        print(f"⚠ Ошибка проверки возможностей: {e}")
        return None


def run_import_process_enhanced():
    """Выполняет улучшенный процесс импорта с поддержкой MaterialX"""
    try:
        print("=" * 80)
        print("ЗАПУСК УЛУЧШЕННОГО ЗАГРУЗЧИКА МОДЕЛЕЙ С MATERIALX")
        print("=" * 80)
        
        # Настраиваем пути и импортируем модули
        scripts_path = setup_module_paths()
        modules, materialx_available = import_and_reload_modules()
        
        # Проверяем возможности MaterialX
        if materialx_available:
            materialx_capabilities = check_materialx_capabilities()
        else:
            materialx_capabilities = None
        
        # Получаем необходимые модули
        settings_dialog = modules['settings_dialog']
        logger = modules['logger']
        cache_manager = modules['cache_manager']
        main = modules['main']
        
        if not settings_dialog or not logger or not cache_manager or not main:
            raise ImportError("Критические модули не загружены")
        
        # Показываем диалог настроек
        print("Показываем диалог настроек...")
        start_dialog_time = time.time()
        
        settings = settings_dialog.show_settings_dialog()
        
        dialog_time = time.time() - start_dialog_time
        print(f"Диалог настроек завершен за {dialog_time:.2f}с")
        
        if settings is None:
            print("Импорт отменен пользователем")
            return
        
        # Валидация типа материала с новой системой
        if materialx_available and materialx_capabilities:
            try:
                from material_builder_manager import get_material_manager
                manager = get_material_manager()
                
                # Валидируем и возможно корректируем тип материала
                original_type = settings.material_type
                validated_type = manager.validate_material_type(settings.material_type)
                
                if original_type != validated_type:
                    print(f"Тип материала изменен с '{original_type}' на '{validated_type}'")
                    settings.material_type = validated_type
                
            except Exception as e:
                print(f"Ошибка валидации типа материала: {e}")
        
        print(f"Выбранные настройки:")
        print(f"  Режим: {settings.import_mode}")
        print(f"  Материал: {settings.material_type}")
        print(f"  MaterialX система: {'активна' if materialx_available else 'недоступна'}")
        print(f"  Кэширование: {'включено' if settings.use_cache else 'выключено'}")
        print(f"  Отладка: {'включена' if settings.debug_mode else 'выключена'}")
        
        # Инициализируем компоненты
        print("Инициализация компонентов...")
        init_start_time = time.time()
        
        import_logger = logger.ImportLogger(debug_mode=settings.debug_mode)
        import_logger.log_debug("Инициализирован логгер")
        
        if materialx_available:
            import_logger.log_debug("Новая система MaterialX активна")
        else:
            import_logger.log_debug("Используется legacy система материалов")
        
        cache_mgr = cache_manager.CacheManager(logger=import_logger, enabled=settings.use_cache)
        
        init_time = time.time() - init_start_time
        print(f"Компоненты инициализированы за {init_time:.2f}с")
        
        # Выполняем импорт с улучшенной функцией
        print("Начинаем импорт...")
        import_start_time = time.time()
        
        try:
            result = None
            
            if settings.import_mode == "separate":
                import_logger.log_debug("Запуск режима: отдельные геометрии")
                # Используем обновленную функцию если доступна
                if hasattr(main, 'create_multi_material_models_optimized'):
                    result = main.create_multi_material_models_optimized(
                        merge_models=False,
                        settings=settings,
                        logger=import_logger,
                        cache_manager=cache_mgr
                    )
                else:
                    # Fallback на старую функцию
                    result = main.create_multi_material_models(
                        merge_models=False,
                        settings=settings,
                        logger=import_logger,
                        cache_manager=cache_mgr
                    )
                    
            elif settings.import_mode == "grouped":
                import_logger.log_debug("Запуск режима: группировка по папкам")
                if hasattr(main, 'create_multi_material_models_optimized'):
                    result = main.create_multi_material_models_optimized(
                        merge_models=True,
                        settings=settings,
                        logger=import_logger,
                        cache_manager=cache_mgr
                    )
                else:
                    result = main.create_multi_material_models(
                        merge_models=True,
                        settings=settings,
                        logger=import_logger,
                        cache_manager=cache_mgr
                    )
                    
            elif settings.import_mode == "merged":
                import_logger.log_debug("Запуск режима: объединение в один узел")
                # Используем улучшенную функцию если доступна
                if hasattr(main, 'create_unified_model_import_enhanced'):
                    result = main.create_unified_model_import_enhanced(
                        settings=settings,
                        logger=import_logger,
                        cache_manager=cache_mgr
                    )
                elif hasattr(main, 'create_unified_model_import_optimized'):
                    result = main.create_unified_model_import_optimized(
                        settings=settings,
                        logger=import_logger,
                        cache_manager=cache_mgr
                    )
                else:
                    result = main.create_unified_model_import(
                        settings=settings,
                        logger=import_logger,
                        cache_manager=cache_mgr
                    )
            else:
                raise ValueError(f"Неизвестный режим импорта: {settings.import_mode}")
            
            import_time = time.time() - import_start_time
            print(f"Импорт завершен за {import_time:.2f}с")
            
            # Завершаем логирование
            import_logger.log_import_finished()
            
            # Показываем статистику MaterialX если доступна
            if materialx_available and result:
                try:
                    from material_builder_manager import get_material_manager
                    manager = get_material_manager()
                    print("MaterialX статистика:")
                    manager.print_capabilities_info()
                except Exception as e:
                    print(f"Ошибка получения MaterialX статистики: {e}")
            
            # Показываем статистику кэша
            if settings.use_cache and cache_mgr:
                try:
                    cache_stats = cache_mgr.get_cache_stats()
                    print("Статистика кэширования:")
                    for cache_type, stats in cache_stats.items():
                        if isinstance(stats, dict) and 'hits' in stats:
                            hit_ratio = stats.get('hit_ratio', 0) * 100
                            print(f"  {cache_type}: хиты={stats['hits']}, промахи={stats['misses']}, соотношение={hit_ratio:.1f}%")
                    
                    import_logger.log_debug("Статистика кэша выведена")
                except Exception as e:
                    print(f"Ошибка получения статистики кэша: {e}")
            
            # Показываем отчеты
            if settings.generate_report:
                try:
                    print("Генерация отчета...")
                    import_logger.show_report()
                except Exception as e:
                    print(f"Ошибка генерации отчета: {e}")
            
            if settings.show_import_log:
                try:
                    print("Показ лога...")
                    import_logger.show_log()
                except Exception as e:
                    print(f"Ошибка показа лога: {e}")
            
            # Итоговое сообщение
            if result:
                total_time = time.time() - import_start_time
                success_msg = f"Импорт моделей завершен успешно за {total_time:.2f} секунд!"
                
                # Дополнительная информация о системе MaterialX
                if materialx_available:
                    success_msg += f"\n✓ Использована новая система MaterialX"
                    success_msg += f"\n✓ Тип материала: {settings.material_type}"
                else:
                    success_msg += f"\n⚠ Использована legacy система материалов"
                
                print("=" * 80)
                print("ИМПОРТ ЗАВЕРШЕН УСПЕШНО")
                print("=" * 80)
                print(success_msg)
                import_logger.log_debug(success_msg)
                
                # Показываем сообщение пользователю
                hou.ui.displayMessage(success_msg, severity=hou.severityType.Message)
            else:
                print("Импорт завершен с ошибками")
                
        except Exception as e:
            import_time = time.time() - import_start_time
            error_msg = f"Критическая ошибка импорта после {import_time:.2f}с: {e}"
            print(f"ERROR: {error_msg}")
            import_logger.log_error(error_msg)
            
            import traceback
            traceback_str = traceback.format_exc()
            print("Подробная информация об ошибке:")
            print(traceback_str)
            import_logger.log_error(traceback_str)
            
            # Показываем отчет об ошибках
            if settings.generate_report:
                try:
                    import_logger.show_report()
                except:
                    pass
            if settings.show_import_log:
                try:
                    import_logger.show_log()
                except:
                    pass
            
            hou.ui.displayMessage(
                f"Произошла ошибка при импорте:\n{e}\n\nПроверьте лог для подробностей.",
                severity=hou.severityType.Error
            )
            
    except ImportError as e:
        error_msg = f"Не удалось импортировать модули: {e}\nУбедитесь, что все файлы находятся в правильной директории"
        print(f"CRITICAL ERROR: {error_msg}")
        hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
        
    except Exception as e:
        error_msg = f"Фатальная ошибка: {e}"
        print(f"FATAL ERROR: {error_msg}")
        
        import traceback
        traceback_str = traceback.format_exc()
        print("Полная информация об ошибке:")
        print(traceback_str)
        
        try:
            hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
        except:
            pass


def main():
    """Главная функция для запуска из полки с проверками MaterialX системы"""
    overall_start_time = time.time()
    
    try:
        # Проверяем среду
        if not hasattr(hou, 'ui'):
            raise RuntimeError("Скрипт должен запускаться в Houdini")
        
        print("Проверка системы...")
        print(f"Версия Houdini: {hou.applicationVersion()}")
        print(f"Пользовательская директория: {hou.homeHoudiniDirectory()}")
        
        # Запускаем улучшенный процесс импорта
        run_import_process_enhanced()
        
    except KeyboardInterrupt:
        print("Импорт прерван пользователем")
        
    except Exception as e:
        error_msg = f"Системная ошибка: {e}"
        print(f"SYSTEM ERROR: {error_msg}")
        
        import traceback
        print("Системная трассировка:")
        print(traceback.format_exc())
        
        try:
            hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
        except:
            pass
    
    finally:
        total_time = time.time() - overall_start_time
        print("=" * 80)
        print(f"ОБЩЕЕ ВРЕМЯ РАБОТЫ СКРИПТА: {total_time:.2f} секунд")
        print("ЗАВЕРШЕНИЕ РАБОТЫ ЗАГРУЗЧИКА МОДЕЛЕЙ С MATERIALX")
        print("=" * 80)


# Проверяем контекст выполнения
if __name__ == "__main__":
    main()
else:
    # Если выполняется через exec(), запускаем main()
    main()