"""
Безопасная диагностическая версия загрузчика с защитой от зависания
Запустите этот код вместо основного для диагностики проблем
"""
import sys
import os
import time
import signal
import hou

class TimeoutException(Exception):
    """Исключение для таймаута"""
    pass

def timeout_handler(signum, frame):
    """Обработчик таймаута"""
    raise TimeoutException("Операция превысила лимит времени")

def safe_walk_directory(directory, max_files=1000, timeout_seconds=30):
    """Безопасный обход директории с ограничениями"""
    print(f"🔍 Начинаем безопасный поиск файлов в: {directory}")
    print(f"   Лимиты: {max_files} файлов, {timeout_seconds} секунд")
    
    start_time = time.time()
    found_files = []
    processed_dirs = 0
    total_files = 0
    
    try:
        # Устанавливаем таймаут (только на Unix/Linux)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)
        
        for root, dirs, files in os.walk(directory):
            # Проверяем время выполнения
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                print(f"⏰ Превышен лимит времени ({timeout_seconds}s)")
                break
            
            processed_dirs += 1
            total_files += len(files)
            
            print(f"   📁 Обрабатываем: {root} ({len(files)} файлов)")
            
            # Ограничиваем количество обрабатываемых файлов
            if total_files > max_files:
                print(f"📊 Превышен лимит файлов ({max_files})")
                break
            
            # Обрабатываем файлы в текущей директории
            for file in files[:50]:  # Не более 50 файлов за раз
                found_files.append(os.path.join(root, file))
                
                if len(found_files) >= max_files:
                    break
            
            # Ограничиваем глубину рекурсии
            if processed_dirs > 100:
                print("📊 Превышен лимит директорий (100)")
                break
                
            # Даем UI возможность обновиться
            if processed_dirs % 10 == 0:
                hou.ui.updateProgressAndCheckForInterrupt()
                time.sleep(0.01)  # Короткая пауза
    
    except TimeoutException:
        print("⏰ Операция прервана по таймауту")
    except KeyboardInterrupt:
        print("⏹️ Операция прервана пользователем")
    except Exception as e:
        print(f"❌ Ошибка при обходе директории: {e}")
    finally:
        # Отключаем таймаут
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)
    
    elapsed = time.time() - start_time
    print(f"✅ Обработано за {elapsed:.1f}s: {processed_dirs} папок, найдено {len(found_files)} файлов")
    
    return found_files

def filter_model_files(files, max_models=50):
    """Фильтрует файлы моделей с ограничением"""
    print(f"🎯 Фильтрация файлов моделей (лимит: {max_models})")
    
    model_extensions = ['.fbx', '.obj', '.abc', '.bgeo', '.ply']
    model_files = []
    
    for file_path in files:
        if any(file_path.lower().endswith(ext) for ext in model_extensions):
            model_files.append(file_path)
            print(f"   ✅ Модель: {os.path.basename(file_path)}")
            
            if len(model_files) >= max_models:
                print(f"📊 Достигнут лимит моделей ({max_models})")
                break
    
    print(f"📈 Найдено моделей: {len(model_files)}")
    return model_files

def filter_texture_files(files, max_textures=100):
    """Фильтрует файлы текстур с ограничением"""
    print(f"🖼️ Фильтрация файлов текстур (лимит: {max_textures})")
    
    texture_extensions = ['.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff', '.exr', '.hdr']
    texture_files = []
    
    for file_path in files:
        if any(file_path.lower().endswith(ext) for ext in texture_extensions):
            texture_files.append(file_path)
            if len(texture_files) <= 10:  # Показываем только первые 10
                print(f"   ✅ Текстура: {os.path.basename(file_path)}")
            
            if len(texture_files) >= max_textures:
                print(f"📊 Достигнут лимит текстур ({max_textures})")
                break
    
    if len(texture_files) > 10:
        print(f"   ... и еще {len(texture_files) - 10} текстур")
    
    print(f"📈 Найдено текстур: {len(texture_files)}")
    return texture_files

def safe_create_node(parent, node_type, name):
    """Безопасное создание ноды с обработкой ошибок"""
    try:
        print(f"🔧 Создание ноды: {node_type} '{name}'")
        node = parent.createNode(node_type, name)
        print(f"   ✅ Создана: {node.path()}")
        return node
    except Exception as e:
        print(f"   ❌ Ошибка создания ноды: {e}")
        return None

def diagnostic_import():
    """Диагностический импорт с детальным логированием"""
    print("🚀 ДИАГНОСТИЧЕСКИЙ ИМПОРТ МОДЕЛЕЙ")
    print("=" * 60)
    
    try:
        # 1. Получение папки
        print("📁 1. Выбор папки...")
        folder_path = hou.ui.selectFile(
            title="Выберите папку с моделями (ДИАГНОСТИКА)",
            file_type=hou.fileType.Directory
        )
        
        if not folder_path:
            print("❌ Папка не выбрана")
            return
        
        folder_path = folder_path.rstrip("/\\")
        print(f"   ✅ Выбрана папка: {folder_path}")
        
        # 2. Проверка существования папки
        print("\n📋 2. Проверка папки...")
        if not os.path.exists(folder_path):
            print(f"❌ Папка не существует: {folder_path}")
            return
        
        if not os.path.isdir(folder_path):
            print(f"❌ Путь не является папкой: {folder_path}")
            return
        
        print(f"   ✅ Папка существует и доступна")
        
        # 3. Быстрый подсчет файлов
        print("\n📊 3. Быстрая оценка размера...")
        try:
            immediate_files = os.listdir(folder_path)
            print(f"   📄 Файлов в корне: {len(immediate_files)}")
            
            # Подсчет подпапок
            subdirs = [d for d in immediate_files if os.path.isdir(os.path.join(folder_path, d))]
            print(f"   📁 Подпапок: {len(subdirs)}")
            
            if len(subdirs) > 20:
                print("   ⚠️ Много подпапок - может потребоваться время")
            
        except Exception as e:
            print(f"   ❌ Ошибка доступа к папке: {e}")
            return
        
        # 4. Безопасный поиск файлов
        print("\n🔍 4. Безопасный поиск файлов...")
        all_files = safe_walk_directory(folder_path, max_files=500, timeout_seconds=20)
        
        if not all_files:
            print("❌ Файлы не найдены или операция прервана")
            return
        
        print(f"   ✅ Найдено файлов: {len(all_files)}")
        
        # 5. Фильтрация моделей
        print("\n🎯 5. Поиск моделей...")
        model_files = filter_model_files(all_files, max_models=20)
        
        if not model_files:
            print("❌ Модели не найдены")
            hou.ui.displayMessage("Модели не найдены в выбранной папке", severity=hou.severityType.Warning)
            return
        
        # 6. Фильтрация текстур
        print("\n🖼️ 6. Поиск текстур...")
        texture_files = filter_texture_files(all_files, max_textures=50)
        
        # 7. Создание узлов
        print("\n🔧 7. Создание узлов...")
        
        obj_node = hou.node("/obj")
        if not obj_node:
            print("❌ Контекст /obj не найден")
            return
        
        # Создаем простую геометрию для тестирования
        geo_name = f"diagnostic_import_{int(time.time())}"
        geo_node = safe_create_node(obj_node, "geo", geo_name)
        
        if not geo_node:
            print("❌ Не удалось создать geo-ноду")
            return
        
        geo_node.allowEditingOfContents()
        
        # 8. Импорт первой модели для теста
        print("\n📦 8. Тестовый импорт первой модели...")
        if model_files:
            first_model = model_files[0]
            print(f"   🎯 Импортируем: {os.path.basename(first_model)}")
            
            try:
                file_node = geo_node.createNode("file", "test_import")
                file_node.parm("file").set(first_model)
                file_node.setDisplayFlag(True)
                file_node.setRenderFlag(True)
                
                print(f"   ✅ Модель импортирована успешно: {file_node.path()}")
                
                # Проверяем геометрию
                try:
                    geo = file_node.geometry()
                    if geo:
                        point_count = len(geo.points())
                        prim_count = len(geo.prims())
                        print(f"   📊 Геометрия: {point_count} точек, {prim_count} примитивов")
                    else:
                        print("   ⚠️ Геометрия пуста")
                except Exception as e:
                    print(f"   ⚠️ Ошибка анализа геометрии: {e}")
                
            except Exception as e:
                print(f"   ❌ Ошибка импорта модели: {e}")
        
        # 9. Создание простого материала для теста
        print("\n🎨 9. Тест создания материала...")
        try:
            matnet = safe_create_node(obj_node, "matnet", "test_materials")
            if matnet:
                matnet.allowEditingOfContents()
                
                # Создаем простой материал
                material = matnet.createNode("principledshader", "test_material")
                if material:
                    print(f"   ✅ Материал создан: {material.path()}")
                    
                    # Тест назначения текстуры
                    if texture_files:
                        first_texture = texture_files[0]
                        print(f"   🖼️ Тест текстуры: {os.path.basename(first_texture)}")
                        
                        try:
                            material.parm("basecolor_useTexture").set(True)
                            material.parm("basecolor_texture").set(first_texture)
                            print("   ✅ Текстура назначена успешно")
                        except Exception as e:
                            print(f"   ⚠️ Ошибка назначения текстуры: {e}")
                else:
                    print("   ❌ Не удалось создать материал")
        except Exception as e:
            print(f"   ❌ Ошибка создания matnet: {e}")
        
        # 10. Финальная сводка
        print("\n📋 10. ИТОГОВАЯ СВОДКА:")
        print(f"   📁 Папка: {folder_path}")
        print(f"   📄 Всего файлов: {len(all_files)}")
        print(f"   🎯 Моделей: {len(model_files)}")
        print(f"   🖼️ Текстур: {len(texture_files)}")
        print(f"   🔧 Geo-нода: {geo_node.path() if 'geo_node' in locals() and geo_node else 'Не создана'}")
        
        # Показываем первые несколько моделей
        if model_files:
            print("\n   📋 Найденные модели:")
            for i, model in enumerate(model_files[:5]):
                size = os.path.getsize(model) / (1024*1024)  # MB
                print(f"      {i+1}. {os.path.basename(model)} ({size:.1f}MB)")
            if len(model_files) > 5:
                print(f"      ... и еще {len(model_files) - 5} моделей")
        
        print("\n✅ ДИАГНОСТИКА ЗАВЕРШЕНА")
        
        # Предлагаем продолжить с полным импортом
        if len(model_files) <= 10:
            reply = hou.ui.displayMessage(
                f"Диагностика завершена успешно!\n\n"
                f"Найдено: {len(model_files)} моделей, {len(texture_files)} текстур\n\n"
                f"Запустить полный импорт?",
                buttons=("Да", "Нет"),
                severity=hou.severityType.Message
            )
            
            if reply == 0:  # Да
                print("\n🚀 Запуск полного импорта...")
                run_full_import_safe(model_files, texture_files, folder_path)
        else:
            hou.ui.displayMessage(
                f"Диагностика завершена!\n\n"
                f"Найдено: {len(model_files)} моделей (много!)\n"
                f"Рекомендуется уменьшить количество файлов\n"
                f"или использовать режим 'grouped'",
                severity=hou.severityType.Warning
            )
    
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА ДИАГНОСТИКИ: {e}")
        import traceback
        print("Детали ошибки:")
        print(traceback.format_exc())
        
        hou.ui.displayMessage(
            f"Ошибка диагностики: {e}\n\nСмотрите консоль для подробностей",
            severity=hou.severityType.Error
        )

def run_full_import_safe(model_files, texture_files, folder_path):
    """Запуск полного импорта с безопасными настройками"""
    try:
        print("🚀 ЗАПУСК ПОЛНОГО ИМПОРТА (БЕЗОПАСНЫЙ РЕЖИМ)")
        
        # Импортируем модули
        import settings_dialog
        import main
        import logger
        import cache_manager
        
        # Создаем безопасные настройки
        settings = settings_dialog.ImportSettings()
        settings.import_mode = "separate"  # Безопасный режим
        settings.debug_mode = True
        settings.use_cache = True
        
        # Создаем логгер
        import_logger = logger.ImportLogger(debug_mode=True)
        cache_mgr = cache_manager.CacheManager(logger=import_logger, enabled=True)
        
        # Ограничиваем количество моделей для безопасности
        safe_model_files = model_files[:5]  # Только первые 5 моделей
        
        print(f"Импортируем {len(safe_model_files)} моделей в безопасном режиме...")
        
        # Запускаем импорт
        result = main.create_multi_material_models(
            merge_models=False,
            settings=settings,
            logger=import_logger,
            cache_manager=cache_mgr
        )
        
        if result:
            print("✅ Безопасный импорт завершен успешно!")
            import_logger.log_import_finished()
            
            if settings.generate_report:
                import_logger.show_report()
        
    except Exception as e:
        print(f"❌ Ошибка полного импорта: {e}")
        import traceback
        print(traceback.format_exc())

# Главная функция
def main():
    """Главная функция диагностического режима"""
    print("🔬 ДИАГНОСТИЧЕСКИЙ ЗАГРУЗЧИК FBX МОДЕЛЕЙ")
    print("=" * 60)
    print("Этот режим поможет выявить проблемы с зависанием")
    print("=" * 60)
    
    try:
        diagnostic_import()
    except KeyboardInterrupt:
        print("\n⏹️ Диагностика прервана пользователем")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        print("\n🏁 Диагностика завершена")

# Автоматический запуск
main()