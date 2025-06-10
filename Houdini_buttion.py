"""
ИСПРАВЛЕННЫЙ скрипт для вызова из полки Houdini
"""
import sys
import os
import importlib

# Путь к папке со скриптами
user_dir = os.path.expandvars("$HOUDINI_USER_PREF_DIR")
scripts_path = os.path.join(user_dir, "scripts", "python", "fbx_loader")

# Проверка существования директории
print(f"Путь к скриптам: {scripts_path}")
print(f"Папка существует: {os.path.exists(scripts_path)}")

# Добавляем путь к модулям если еще не добавлен
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)
    print(f"Добавлен путь в sys.path: {scripts_path}")

# ИСПРАВЛЕНИЕ: Импортируем модули правильно (не как пакет)
try:
    # Базовый импорт
    import hou
    
    # ИСПРАВЛЕННЫЙ импорт модулей (как отдельные модули, а не пакет)
    import utils
    import material_utils 
    import model_processor
    import main
    import settings_dialog
    import logger
    import cache_manager
    
    # Перезагружаем модули
    importlib.reload(utils)
    importlib.reload(material_utils)
    importlib.reload(model_processor)
    importlib.reload(main)
    importlib.reload(settings_dialog)
    importlib.reload(logger)
    importlib.reload(cache_manager)
    
    # Проверяем доступность UDIM
    try:
        import udim_utils
        importlib.reload(udim_utils)
        print("✓ UDIM поддержка доступна")
        UDIM_AVAILABLE = True
    except ImportError:
        print("⚠ UDIM поддержка недоступна")
        UDIM_AVAILABLE = False
    
    print("Все модули загружены успешно")
    
    # Показываем диалог с расширенными настройками
    settings = settings_dialog.show_settings_dialog()
    
    # Если пользователь отменил импорт, выходим
    if settings is None:
        print("Импорт отменен пользователем")
    else:
        # Инициализируем логгер
        import_logger = logger.ImportLogger(debug_mode=settings.debug_mode)
        
        # Инициализируем менеджер кэша
        cache_mgr = cache_manager.CacheManager(logger=import_logger, enabled=settings.use_cache)
        
        try:
            # ИСПРАВЛЕНИЕ: Используем правильные функции в зависимости от режима
            if settings.import_mode == "separate":
                # Отдельные геометрии
                result = main.create_multi_material_models_optimized(
                    merge_models=False,
                    settings=settings,
                    logger=import_logger,
                    cache_manager=cache_mgr
                )
            elif settings.import_mode == "grouped":
                # Группировать по папкам
                result = main.create_multi_material_models_optimized(
                    merge_models=True,
                    settings=settings,
                    logger=import_logger,
                    cache_manager=cache_mgr
                )
            elif settings.import_mode == "merged":
                # ИСПРАВЛЕНИЕ: Используем новую исправленную функцию unified импорта
                result = main.create_unified_model_import_with_grid_support_fixed(
                    settings=settings,
                    logger=import_logger,
                    cache_manager=cache_mgr
                )
            
            # Завершаем логирование
            import_logger.log_import_finished()
            
            # Показываем отчет, если это указано в настройках
            if settings.generate_report:
                import_logger.show_report()
            
            # Показываем лог, если это указано в настройках
            if settings.show_import_log:
                import_logger.show_log()
            
            # Выводим статистику кэширования в лог
            if settings.use_cache:
                try:
                    cache_stats = cache_mgr.get_cache_stats()
                    import_logger.log_debug("Статистика кэширования:")
                    for cache_type, stats in cache_stats.items():
                        if isinstance(stats, dict) and 'hits' in stats:
                            import_logger.log_debug(f"  {cache_type}: хиты={stats['hits']}, промахи={stats['misses']}, "
                                                    f"соотношение={stats['hit_ratio']:.2%}, размер={stats['size']}")
                except Exception as e:
                    print(f"Ошибка получения статистики кэша: {e}")
        
        except Exception as e:
            # В случае ошибки, логируем её и показываем сообщение
            import_logger.log_error(f"Критическая ошибка: {e}")
            import traceback
            import_logger.log_error(traceback.format_exc())
            
            # Показываем отчет и лог, если включены
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
            
            # Показываем сообщение об ошибке
            hou.ui.displayMessage(
                f"Произошла ошибка при импорте:\n{e}\n\nПроверьте лог для подробностей.",
                severity=hou.severityType.Error
            )
    
except ImportError as e:
    import hou
    error_msg = f"Не удалось импортировать модули: {e}\n"
    error_msg += f"Убедитесь, что все модули находятся в папке: {scripts_path}\n"
    error_msg += "Требуемые файлы: utils.py, material_utils.py, model_processor.py, main.py, settings_dialog.py, logger.py, cache_manager.py"
    
    print(f"IMPORT ERROR: {error_msg}")
    hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)
    
except Exception as e:
    import hou
    error_msg = f"Произошла критическая ошибка: {e}"
    print(f"CRITICAL ERROR: {error_msg}")
    
    import traceback
    print("Полная трассировка:")
    print(traceback.format_exc())
    
    hou.ui.displayMessage(error_msg, severity=hou.severityType.Error)

# Отладочная информация - только если модули загружены успешно
try:
    if 'model_processor' in locals():
        import inspect
        print(f"Проверка model_processor.py: {inspect.getfile(model_processor)}")
        if hasattr(model_processor, 'process_models_in_single_geo'):
            print(f"Сигнатура функции process_models_in_single_geo: {inspect.signature(model_processor.process_models_in_single_geo)}")
        else:
            print("Функция process_models_in_single_geo не найдена")
    else:
        print("model_processor не загружен")
except Exception as e:
    print(f"Ошибка отладочной информации: {e}")