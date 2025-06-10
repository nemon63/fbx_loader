"""
Скрипт для тестирования новой системы MaterialX в Houdini
Запустить в Python Shell Houdini для проверки работоспособности
"""

import hou
import sys
import os

def setup_test_environment():
    """Настраивает тестовое окружение"""
    # Добавляем путь к модулям (замените на ваш путь)
    houdini_user_dir = hou.homeHoudiniDirectory()
    scripts_path = os.path.join(houdini_user_dir, "scripts", "python", "fbx_loader")
    
    if scripts_path not in sys.path:
        sys.path.append(scripts_path)
        print(f"Добавлен путь: {scripts_path}")
    
    return scripts_path

def test_imports():
    """Тестирует импорт всех модулей"""
    print("=" * 60)
    print("ТЕСТ ИМПОРТА МОДУЛЕЙ")
    print("=" * 60)
    
    modules_to_test = [
        "utils",
        "material_utils", 
        "materialx_builder",
        "principled_builder",
        "material_builder_manager"
    ]
    
    imported_modules = {}
    
    for module_name in modules_to_test:
        try:
            module = __import__(module_name)
            imported_modules[module_name] = module
            print(f"✓ {module_name} импортирован успешно")
        except ImportError as e:
            print(f"✗ {module_name} ошибка импорта: {e}")
            imported_modules[module_name] = None
        except Exception as e:
            print(f"✗ {module_name} неожиданная ошибка: {e}")
            imported_modules[module_name] = None
    
    return imported_modules

def test_material_manager():
    """Тестирует MaterialBuilderManager"""
    print("\n" + "=" * 60)
    print("ТЕСТ MATERIAL BUILDER MANAGER")
    print("=" * 60)
    
    try:
        from material_builder_manager import MaterialBuilderManager, get_material_manager
        
        # Создаем менеджер
        manager = get_material_manager()
        print("✓ MaterialBuilderManager создан")
        
        # Проверяем возможности
        capabilities = manager.get_capabilities_info()
        print(f"✓ MaterialX доступен: {capabilities['capabilities']['materialx']}")
        print(f"✓ Principled доступен: {capabilities['capabilities']['principled']}")
        print(f"✓ Redshift доступен: {capabilities['capabilities']['redshift']}")
        print(f"✓ UDIM поддержка: {capabilities['udim_support']}")
        
        # Выводим подробную информацию
        manager.print_capabilities_info()
        
        return True
        
    except Exception as e:
        print(f"✗ Ошибка тестирования MaterialBuilderManager: {e}")
        return False

def create_test_matnet():
    """Создает тестовый matnet"""
    try:
        obj_node = hou.node("/obj")
        if not obj_node:
            print("✗ Не найден /obj контекст")
            return None
        
        # Создаем matnet для тестирования
        matnet = obj_node.createNode("matnet", "test_materials")
        print(f"✓ Создан тестовый matnet: {matnet.path()}")
        return matnet
        
    except Exception as e:
        print(f"✗ Ошибка создания matnet: {e}")
        return None

def test_materialx_creation(matnet):
    """Тестирует создание MaterialX материала"""
    print("\n" + "=" * 60)
    print("ТЕСТ СОЗДАНИЯ MATERIALX МАТЕРИАЛА")
    print("=" * 60)
    
    if not matnet:
        print("✗ Matnet недоступен для тестирования")
        return False
    
    # Тестовые текстуры (пути могут не существовать, это нормально для теста)
    test_textures = {
        "BaseMap": "/tmp/test_basecolor.1001.jpg",
        "Normal": "/tmp/test_normal.<UDIM>.png",
        "Roughness": "/tmp/test_roughness.1001.exr",
        "Metallic": "/tmp/test_metallic.1001.tga",
        "AO": "/tmp/test_ao.1001.jpg"
    }
    
    try:
        from material_builder_manager import create_material_universal
        
        # Создаем MaterialX материал
        print("Создание MaterialX материала...")
        materialx_material = create_material_universal(
            matnet,
            "test_materialx_shader",
            test_textures,
            "materialx"
        )
        
        if materialx_material:
            print(f"✓ MaterialX материал создан: {materialx_material.path()}")
            print(f"✓ Тип ноды: {materialx_material.type().name()}")
            
            # Проверяем созданные ноды
            child_nodes = matnet.children()
            print(f"✓ Всего нод в matnet: {len(child_nodes)}")
            
            for child in child_nodes:
                print(f"  - {child.name()} ({child.type().name()})")
            
            return True
        else:
            print("✗ MaterialX материал не создан")
            return False
            
    except Exception as e:
        print(f"✗ Ошибка создания MaterialX материала: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_principled_creation(matnet):
    """Тестирует создание Principled материала"""
    print("\n" + "=" * 60)
    print("ТЕСТ СОЗДАНИЯ PRINCIPLED МАТЕРИАЛА")
    print("=" * 60)
    
    if not matnet:
        print("✗ Matnet недоступен для тестирования")
        return False
    
    # Тестовые текстуры
    test_textures = {
        "BaseMap": "/tmp/test_basecolor.jpg",
        "Normal": "/tmp/test_normal.png",
        "Roughness": "/tmp/test_roughness.jpg",
        "Metallic": "/tmp/test_metallic.jpg"
    }
    
    try:
        from material_builder_manager import create_material_universal
        
        # Создаем Principled материал
        print("Создание Principled материала...")
        principled_material = create_material_universal(
            matnet,
            "test_principled_shader", 
            test_textures,
            "principledshader"
        )
        
        if principled_material:
            print(f"✓ Principled материал создан: {principled_material.path()}")
            print(f"✓ Тип ноды: {principled_material.type().name()}")
            return True
        else:
            print("✗ Principled материал не создан")
            return False
            
    except Exception as e:
        print(f"✗ Ошибка создания Principled материала: {e}")
        return False

def test_udim_support():
    """Тестирует поддержку UDIM"""
    print("\n" + "=" * 60)
    print("ТЕСТ UDIM ПОДДЕРЖКИ")
    print("=" * 60)
    
    try:
        from udim_utils import is_udim_texture, detect_udim_sequences
        
        # Тестовые UDIM пути
        test_paths = [
            "/tmp/texture.1001.jpg",
            "/tmp/texture.1002.jpg", 
            "/tmp/texture.1003.jpg",
            "/tmp/texture.<UDIM>.jpg",
            "/tmp/regular_texture.jpg"
        ]
        
        print("Тестирование UDIM детекции...")
        for path in test_paths:
            is_udim = is_udim_texture(path)
            print(f"  {path} -> UDIM: {is_udim}")
        
        # Тест детекции последовательностей
        udim_result = detect_udim_sequences(test_paths[:-1])  # Исключаем обычную текстуру
        print(f"✓ Найдено UDIM последовательностей: {len(udim_result['udim_sequences'])}")
        print(f"✓ Одиночных текстур: {len(udim_result['single_textures'])}")
        
        return True
        
    except ImportError:
        print("✗ UDIM модуль недоступен")
        return False
    except Exception as e:
        print(f"✗ Ошибка тестирования UDIM: {e}")
        return False

def cleanup_test_nodes(matnet):
    """Очищает тестовые ноды"""
    print("\n" + "=" * 60)
    print("ОЧИСТКА ТЕСТОВЫХ НОД")
    print("=" * 60)
    
    try:
        if matnet and matnet.parent():
            matnet.destroy()
            print("✓ Тестовый matnet удален")
        else:
            print("⚠ Matnet уже удален или недоступен")
            
    except Exception as e:
        print(f"✗ Ошибка очистки: {e}")

def run_full_test():
    """Запускает полный тест системы MaterialX"""
    print("ПОЛНЫЙ ТЕСТ СИСТЕМЫ MATERIALX")
    print("=" * 80)
    
    # Настройка окружения
    scripts_path = setup_test_environment()
    
    # Тесты
    test_results = {}
    
    # 1. Тест импорта
    imported_modules = test_imports()
    test_results["imports"] = all(module is not None for module in imported_modules.values())
    
    # 2. Тест менеджера материалов
    test_results["manager"] = test_material_manager()
    
    # 3. Создание тестового matnet
    matnet = create_test_matnet()
    test_results["matnet_creation"] = matnet is not None
    
    # 4. Тест MaterialX
    if matnet:
        test_results["materialx"] = test_materialx_creation(matnet)
        test_results["principled"] = test_principled_creation(matnet)
    
    # 5. Тест UDIM
    test_results["udim"] = test_udim_support()
    
    # Очистка
    if matnet:
        cleanup_test_nodes(matnet)
    
    # Итоговый отчет
    print("\n" + "=" * 80)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 80)
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✓ ПРОЙДЕН" if result else "✗ ПРОВАЛЕН"
        print(f"{test_name:15} {status}")
    
    print(f"\nПройдено тестов: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система MaterialX готова к использованию.")
    else:
        print("⚠ Некоторые тесты провалены. Проверьте установку модулей.")
    
    return test_results

# Запуск тестирования
if __name__ == "__main__":
    run_full_test()
else:
    # Если импортируется как модуль, предоставляем функцию для ручного запуска
    print("Модуль тестирования MaterialX загружен.")
    print("Для запуска полного теста выполните: run_full_test()")