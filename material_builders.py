"""
Material Builders - Объединенные построители материалов для Houdini
Включает исправленные версии Principled Shader и MaterialX билдеров
"""
import hou
import os
from utils import clean_node_name, generate_unique_name

# Импорт UDIM поддержки
try:
    from udim_utils import is_udim_texture
    UDIM_SUPPORT = True
except ImportError:
    UDIM_SUPPORT = False
    def is_udim_texture(path):
        return '<UDIM>' in str(path)


class PrincipledBuilder:
    """Исправленный класс для построения Principled Shader материалов"""
    
    def __init__(self, matnet_node, material_name, material_type="principledshader", logger=None):
        self.matnet_node = matnet_node
        self.material_name = material_name
        self.material_type = material_type
        self.logger = logger
        self.created_nodes = {}
        self.main_shader = None
        
        # Типы Principled шейдеров
        self.available_shader_types = [
            "principledshader",
            "principledshader::2.0",
            "material",
            "surface"
        ]
        
        # Типы Redshift материалов
        self.redshift_types = [
            "redshift::Material",
            "redshift::StandardMaterial"
        ]
    
    def log_debug(self, message):
        """Безопасное логирование"""
        if self.logger:
            self.logger.log_debug(message)
        else:
            print(f"DEBUG Principled: {message}")
    
    def log_error(self, message):
        """Безопасное логирование ошибок"""
        if self.logger:
            self.logger.log_error(message)
        else:
            print(f"ERROR Principled: {message}")
    
    def create_material_network(self, texture_maps):
        """
        Создает Principled Shader материал с исправленным назначением текстур
        
        Args:
            texture_maps (dict): Словарь с текстурами {тип: путь}
            
        Returns:
            hou.Node: Созданный материал или None
        """
        try:
            self.log_debug(f"Создание Principled материала '{self.material_name}' типа {self.material_type}")
            self.log_debug(f"Доступно текстур: {len(texture_maps)}")
            
            # Подсчитываем UDIM текстуры
            udim_count = 0
            if UDIM_SUPPORT:
                udim_count = sum(1 for path in texture_maps.values() if is_udim_texture(path))
                if udim_count > 0:
                    self.log_debug(f"Обнаружено {udim_count} UDIM текстур")
            
            # Определяем стратегию назначения
            use_direct_assignment = not self._needs_texture_nodes(texture_maps)
            
            if use_direct_assignment:
                self.log_debug("Используем прямое назначение файлов")
                return self._create_simple_material(texture_maps)
            else:
                self.log_debug("Используем texture ноды (UDIM/сложные текстуры)")
                return self._create_complex_material(texture_maps)
                
        except Exception as e:
            self.log_error(f"Ошибка создания Principled материала: {e}")
            return None
    
    def _needs_texture_nodes(self, texture_maps):
        """Определяет, нужны ли texture ноды"""
        if not UDIM_SUPPORT:
            return False
        
        # Проверяем UDIM текстуры
        for tex_path in texture_maps.values():
            if is_udim_texture(tex_path):
                return True
        
        return False
    
    def _create_simple_material(self, texture_maps):
        """Создает простой материал с прямым назначением"""
        # Создаем основной шейдер
        self.main_shader = self._create_main_shader()
        if not self.main_shader:
            return None
        
        # Прямое назначение текстур
        self._assign_textures_directly(texture_maps)
        
        self.main_shader.moveToGoodPosition()
        return self.main_shader
    
    def _create_complex_material(self, texture_maps):
        """Создает сложный материал с texture нодами"""
        # Создаем основной шейдер
        self.main_shader = self._create_main_shader()
        if not self.main_shader:
            return None
        
        # Создаем и подключаем texture ноды
        texture_nodes = self._create_texture_nodes(texture_maps)
        self._connect_texture_nodes_properly(texture_nodes, texture_maps)
        
        # Размещаем ноды
        self._arrange_nodes()
        
        return self.main_shader
    
    def _create_main_shader(self):
        """Создает основной Principled шейдер"""
        safe_name = clean_node_name(self.material_name)
        if not safe_name:
            safe_name = "principled_material"
        
        shader_name = generate_unique_name(self.matnet_node, "shader", safe_name)
        
        # Выбираем типы шейдеров в зависимости от material_type
        if self.material_type == "redshift::Material":
            shader_types = self.redshift_types + self.available_shader_types
        else:
            shader_types = self.available_shader_types
        
        # Пробуем создать шейдер
        for shader_type in shader_types:
            try:
                shader = self.matnet_node.createNode(shader_type, shader_name)
                if shader:
                    self.log_debug(f"Создан Principled шейдер типа: {shader_type}")
                    self.created_nodes['main_shader'] = shader
                    
                    # Настраиваем базовые параметры
                    self._configure_base_parameters(shader)
                    
                    return shader
            except Exception as e:
                self.log_debug(f"Не удалось создать {shader_type}: {e}")
                continue
        
        self.log_error("Не удалось создать Principled шейдер любого типа")
        return None
    
    def _configure_base_parameters(self, shader):
        """Настраивает базовые параметры шейдера"""
        try:
            # Устанавливаем базовый цвет в белый для корректной работы с текстурами
            if shader.parmTuple("basecolor"):
                shader.parmTuple("basecolor").set((1.0, 1.0, 1.0))
                self.log_debug("Установлен базовый цвет (1,1,1)")
            elif shader.parmTuple("diffuse"):
                shader.parmTuple("diffuse").set((1.0, 1.0, 1.0))
                self.log_debug("Установлен diffuse цвет (1,1,1)")
            
            # Базовые настройки для Redshift
            if self.material_type == "redshift::Material":
                self._configure_redshift_parameters(shader)
            
        except Exception as e:
            self.log_error(f"Ошибка настройки базовых параметров: {e}")
    
    def _configure_redshift_parameters(self, shader):
        """Специальные настройки для Redshift материалов"""
        try:
            # Устанавливаем Redshift-специфичные параметры
            if shader.parm("refl_brdf"):
                shader.parm("refl_brdf").set(1)  # GGX
            
            self.log_debug("Настроены параметры Redshift")
            
        except Exception as e:
            self.log_debug(f"Предупреждение: не удалось настроить Redshift параметры: {e}")
    
    def _assign_textures_directly(self, texture_maps):
        """Исправленное прямое назначение текстур"""
        self.log_debug(f"Прямое назначение {len(texture_maps)} текстур")
        
        # Простая карта назначения
        assignments = {
            "BaseMap": [
                ("basecolor_useTexture", "basecolor_texture"),
                ("diffuse_useTexture", "diffuse_texture")
            ],
            "Normal": [
                ("baseBumpAndNormal_enable", None),
                ("baseNormal_useTexture", "baseNormal_texture")
            ],
            "Roughness": [
                ("rough_useTexture", "rough_texture")
            ],
            "Metallic": [
                ("metallic_useTexture", "metallic_texture")
            ],
            "AO": [
                ("baseAO_enable", "baseAO_texture")
            ],
            "Emissive": [
                ("emissive_useTexture", "emissive_texture")
            ],
            "Opacity": [
                ("opac_useTexture", "opac_texture")
            ],
            "Height": [
                ("dispTex_enable", "dispTex_texture")
            ],
            "Specular": [
                ("reflect_useTexture", "reflect_texture")
            ]
        }
        
        successful_count = 0
        
        for texture_type, texture_path in texture_maps.items():
            if texture_type in assignments:
                success = False
                for enable_param, texture_param in assignments[texture_type]:
                    try:
                        # Специальная обработка для нормалей
                        if enable_param == "baseBumpAndNormal_enable":
                            if self.main_shader.parm(enable_param):
                                self.main_shader.parm(enable_param).set(True)
                                self.log_debug(f"Активирован {enable_param}")
                            continue
                        
                        # Включаем использование текстуры
                        if enable_param and self.main_shader.parm(enable_param):
                            self.main_shader.parm(enable_param).set(True)
                            self.log_debug(f"Активирован {enable_param}")
                        
                        # Назначаем файл
                        if texture_param and self.main_shader.parm(texture_param):
                            self.main_shader.parm(texture_param).set(texture_path)
                            is_udim = UDIM_SUPPORT and is_udim_texture(texture_path)
                            udim_label = " (UDIM)" if is_udim else ""
                            self.log_debug(f"✓ Прямо назначена {texture_type}: {os.path.basename(texture_path)}{udim_label}")
                            success = True
                            break
                        elif texture_param is None and enable_param:
                            # Случай когда enable параметр сам принимает файл
                            if self.main_shader.parm(enable_param):
                                self.main_shader.parm(enable_param).set(texture_path)
                                success = True
                                break
                                
                    except Exception as e:
                        self.log_debug(f"Ошибка назначения {texture_type}: {e}")
                        continue
                
                if success:
                    successful_count += 1
                else:
                    self.log_debug(f"✗ Не удалось назначить {texture_type}")
        
        self.log_debug(f"Прямо назначено {successful_count} из {len(texture_maps)} текстур")
    
    def _create_texture_nodes(self, texture_maps):
        """Создает texture ноды для каждой текстуры"""
        texture_nodes = {}
        
        for texture_type, texture_path in texture_maps.items():
            try:
                # Создаем texture ноду
                texture_node = self._create_single_texture_node(texture_type, texture_path)
                if texture_node:
                    texture_nodes[texture_type] = texture_node
                    self.created_nodes[f'texture_{texture_type}'] = texture_node
                    
                    # Логирование
                    is_udim = UDIM_SUPPORT and is_udim_texture(texture_path)
                    udim_label = " (UDIM)" if is_udim else ""
                    self.log_debug(f"Создана texture нода для {texture_type}: {texture_node.name()}{udim_label}")
                
            except Exception as e:
                self.log_error(f"Ошибка создания texture ноды для {texture_type}: {e}")
                continue
        
        return texture_nodes
    
    def _create_single_texture_node(self, texture_type, texture_path):
        """Создает одну texture ноду"""
        try:
            # Выбираем тип texture ноды
            texture_node_type = self._get_texture_node_type(texture_type)
            
            # Создаем уникальное имя
            safe_texture_type = clean_node_name(texture_type.lower())
            texture_name = generate_unique_name(
                self.matnet_node,
                texture_node_type,
                f"{clean_node_name(self.material_name)}_{safe_texture_type}"
            )
            
            # Создаем ноду
            texture_node = self.matnet_node.createNode(texture_node_type, texture_name)
            if not texture_node:
                return None
            
            # Настраиваем texture ноду
            self._configure_texture_node(texture_node, texture_type, texture_path)
            
            return texture_node
            
        except Exception as e:
            self.log_error(f"Ошибка создания texture ноды для {texture_type}: {e}")
            return None
    
    def _get_texture_node_type(self, texture_type):
        """Возвращает тип texture ноды в зависимости от типа текстуры"""
        try:
            node_types = hou.nodeTypeCategories()["Vop"].nodeTypes()
            if "texture::2.0" in node_types:
                return "texture::2.0"
            elif "texture" in node_types:
                return "texture"
            else:
                return "file"  # Fallback
        except:
            return "texture"
    
    def _configure_texture_node(self, texture_node, texture_type, texture_path):
        """Настраивает texture ноду"""
        try:
            # Устанавливаем путь к файлу
            file_parms = ["map", "file", "filename", "texture"]
            for parm_name in file_parms:
                if texture_node.parm(parm_name):
                    texture_node.parm(parm_name).set(texture_path)
                    break
            
            # Специальные настройки для разных типов текстур
            if texture_type == "Normal":
                self._configure_normal_texture(texture_node)
            elif texture_type in ["Roughness", "Metallic", "AO", "Height", "Opacity"]:
                self._configure_float_texture(texture_node)
            elif texture_type in ["BaseMap", "Emissive"]:
                self._configure_color_texture(texture_node)
            
            self.log_debug(f"Настроена texture нода для {texture_type}")
            
        except Exception as e:
            self.log_error(f"Ошибка настройки texture ноды для {texture_type}: {e}")
    
    def _configure_normal_texture(self, texture_node):
        """Настраивает texture ноду для нормалей"""
        try:
            # Устанавливаем color space для нормалей
            if texture_node.parm("colorspace"):
                texture_node.parm("colorspace").set("Raw")
            elif texture_node.parm("srccolorspace"):
                texture_node.parm("srccolorspace").set("Raw")
            
            # Отключаем sRGB conversion
            if texture_node.parm("srgb"):
                texture_node.parm("srgb").set(False)
                
        except Exception as e:
            self.log_debug(f"Не удалось настроить normal texture: {e}")
    
    def _configure_float_texture(self, texture_node):
        """Настраивает texture ноду для float значений"""
        try:
            # Устанавливаем Raw color space
            if texture_node.parm("colorspace"):
                texture_node.parm("colorspace").set("Raw")
            elif texture_node.parm("srccolorspace"):
                texture_node.parm("srccolorspace").set("Raw")
            
            # Отключаем sRGB conversion
            if texture_node.parm("srgb"):
                texture_node.parm("srgb").set(False)
                
        except Exception as e:
            self.log_debug(f"Не удалось настроить float texture: {e}")
    
    def _configure_color_texture(self, texture_node):
        """Настраивает texture ноду для цветных текстур"""
        try:
            # Устанавливаем sRGB color space
            if texture_node.parm("colorspace"):
                texture_node.parm("colorspace").set("sRGB")
            elif texture_node.parm("srccolorspace"):
                texture_node.parm("srccolorspace").set("sRGB")
            
            # Включаем sRGB conversion
            if texture_node.parm("srgb"):
                texture_node.parm("srgb").set(True)
                
        except Exception as e:
            self.log_debug(f"Не удалось настроить color texture: {e}")
    
    def _connect_texture_nodes_properly(self, texture_nodes, texture_maps):
        """Исправленное подключение texture нод к шейдеру"""
        self.log_debug(f"Подключение {len(texture_nodes)} texture нод")
        
        # Карта подключений: (shader_input, texture_output)
        connections = {
            "BaseMap": ("basecolor", "clr"),
            "Normal": ("baseN", "clr"),
            "Roughness": ("rough", "clr"),
            "Metallic": ("metallic", "clr"),
            "AO": ("baseAO", "clr"),
            "Emissive": ("emitcolor", "clr"),
            "Opacity": ("opac", "clr"),
            "Height": ("dispTex", "clr"),
            "Specular": ("reflect", "clr")
        }
        
        connected_count = 0
        
        for texture_type, texture_node in texture_nodes.items():
            if texture_type in connections:
                shader_input, texture_output = connections[texture_type]
                
                try:
                    # Правильное подключение в Houdini
                    success = self._connect_nodes_properly(texture_node, texture_output, self.main_shader, shader_input)
                    
                    if success:
                        connected_count += 1
                        is_udim = UDIM_SUPPORT and is_udim_texture(texture_maps[texture_type])
                        udim_label = " (UDIM)" if is_udim else ""
                        self.log_debug(f"✓ Подключено {texture_type}{udim_label}")
                        
                        # Включаем использование текстуры
                        self._enable_texture_input(texture_type)
                    else:
                        self.log_debug(f"✗ Не удалось подключить {texture_type}")
                        
                except Exception as e:
                    self.log_debug(f"Ошибка подключения {texture_type}: {e}")
        
        self.log_debug(f"Подключено {connected_count} из {len(texture_nodes)} текстур к Principled шейдеру")
    
    def _connect_nodes_properly(self, source_node, source_output, target_node, target_input):
        """Правильное подключение двух нод"""
        try:
            # Получаем output connector
            source_output_parm = source_node.parm(source_output)
            if not source_output_parm:
                # Пробуем альтернативные выходы
                for alt_output in ["clr", "color", "out"]:
                    if source_node.parm(alt_output):
                        source_output = alt_output
                        source_output_parm = source_node.parm(alt_output)
                        break
            
            if not source_output_parm:
                self.log_debug(f"Не найден выход {source_output} в {source_node.name()}")
                return False
            
            # Получаем input connector
            target_input_parm = target_node.parm(target_input)
            if not target_input_parm:
                self.log_debug(f"Не найден вход {target_input} в {target_node.name()}")
                return False
            
            # Выполняем подключение через setExpression
            connection_expr = f"ch('{source_node.path()}/{source_output}')"
            target_input_parm.setExpression(connection_expr)
            
            self.log_debug(f"Подключено: {source_node.name()}.{source_output} -> {target_node.name()}.{target_input}")
            return True
            
        except Exception as e:
            self.log_debug(f"Ошибка подключения: {e}")
            return False
    
    def _enable_texture_input(self, texture_type):
        """Включает использование текстурного входа"""
        enable_params = {
            "BaseMap": ["basecolor_useTexture"],
            "Normal": ["baseBumpAndNormal_enable", "baseNormal_useTexture"],
            "Roughness": ["rough_useTexture"],
            "Metallic": ["metallic_useTexture"],
            "AO": ["baseAO_enable"],
            "Emissive": ["emissive_useTexture"],
            "Opacity": ["opac_useTexture"],
            "Height": ["dispTex_enable"],
            "Specular": ["reflect_useTexture"]
        }
        
        if texture_type in enable_params:
            for param_name in enable_params[texture_type]:
                if self.main_shader.parm(param_name):
                    try:
                        self.main_shader.parm(param_name).set(True)
                        self.log_debug(f"Включен параметр {param_name}")
                    except Exception as e:
                        self.log_debug(f"Ошибка включения {param_name}: {e}")
    
    def _arrange_nodes(self):
        """Размещает созданные ноды в network editor"""
        try:
            if not self.main_shader:
                return
            
            # Размещаем основной шейдер
            self.main_shader.moveToGoodPosition()
            
            # Размещаем texture ноды слева от шейдера
            shader_pos = self.main_shader.position()
            
            texture_nodes = [node for key, node in self.created_nodes.items() if key.startswith('texture_')]
            
            for i, texture_node in enumerate(texture_nodes):
                try:
                    # Размещаем texture ноды в колонку слева
                    new_pos = hou.Vector2(shader_pos.x() - 4, shader_pos.y() + (i - len(texture_nodes)/2) * 2)
                    texture_node.setPosition(new_pos)
                except Exception as e:
                    self.log_debug(f"Не удалось разместить {texture_node.name()}: {e}")
                    texture_node.moveToGoodPosition()
            
            self.log_debug("Ноды размещены в network editor")
            
        except Exception as e:
            self.log_error(f"Ошибка размещения нод: {e}")
    
    def get_created_nodes(self):
        """Возвращает словарь созданных нод"""
        return self.created_nodes.copy()
    
    def get_main_material_node(self):
        """Возвращает основную ноду материала для назначения"""
        return self.main_shader


class MaterialXBuilder:
    """Исправленный класс для построения MaterialX сетей шейдеров"""
    
    def __init__(self, matnet_node, material_name, logger=None):
        self.matnet_node = matnet_node
        self.material_name = material_name
        self.logger = logger
        self.created_nodes = {}
        self.main_surface = None
        
        # Типы MaterialX нод
        self.available_surface_types = [
            "mtlxstandardsurface",
            "usdpreviewsurface", 
            "standardsurface",
            "principled_bsdf"
        ]
    
    def log_debug(self, message):
        """Безопасное логирование"""
        if self.logger:
            self.logger.log_debug(message)
        else:
            print(f"DEBUG MaterialX: {message}")
    
    def log_error(self, message):
        """Безопасное логирование ошибок"""
        if self.logger:
            self.logger.log_error(message)
        else:
            print(f"ERROR MaterialX: {message}")
    
    def create_material_network(self, texture_maps):
        """
        Создает MaterialX сеть с исправленным назначением
        
        Args:
            texture_maps (dict): Словарь с текстурами {тип: путь}
            
        Returns:
            hou.Node: Созданный материал или None
        """
        try:
            self.log_debug(f"Создание MaterialX сети для материала '{self.material_name}'")
            self.log_debug(f"Доступно текстур: {len(texture_maps)}")
            
            # Подсчитываем UDIM текстуры
            udim_count = 0
            if UDIM_SUPPORT:
                udim_count = sum(1 for path in texture_maps.values() if is_udim_texture(path))
                if udim_count > 0:
                    self.log_debug(f"Обнаружено {udim_count} UDIM текстур")
            
            # Определяем стратегию
            use_direct_assignment = not self._needs_image_nodes(texture_maps)
            
            if use_direct_assignment:
                self.log_debug("MaterialX: используем прямое назначение файлов")
                return self._create_simple_materialx(texture_maps)
            else:
                self.log_debug("MaterialX: используем mtlximage ноды")
                return self._create_complex_materialx(texture_maps)
                
        except Exception as e:
            self.log_error(f"Ошибка создания MaterialX сети: {e}")
            return None
    
    def _needs_image_nodes(self, texture_maps):
        """Определяет, нужны ли mtlximage ноды"""
        if not UDIM_SUPPORT:
            return False
        
        # Для UDIM обязательно нужны image ноды
        for tex_path in texture_maps.values():
            if is_udim_texture(tex_path):
                return True
        
        return False
    
    def _create_simple_materialx(self, texture_maps):
        """Создает простой MaterialX с прямым назначением"""
        # Создаем основную поверхность
        self.main_surface = self._create_main_surface()
        if not self.main_surface:
            return None
        
        # Прямое назначение файлов
        self._assign_textures_directly_materialx(texture_maps)
        
        # Создаем material wrapper
        material_wrapper = self._create_material_wrapper()
        
        self.main_surface.moveToGoodPosition()
        if material_wrapper:
            material_wrapper.moveToGoodPosition()
        
        return material_wrapper if material_wrapper else self.main_surface
    
    def _create_complex_materialx(self, texture_maps):
        """Создает сложный MaterialX с image нодами"""
        # Создаем основную поверхность
        self.main_surface = self._create_main_surface()
        if not self.main_surface:
            return None
        
        # Создаем image ноды
        image_nodes = self._create_image_nodes(texture_maps)
        
        # Подключаем ноды
        self._connect_image_nodes_properly(image_nodes, texture_maps)
        
        # Создаем material wrapper
        material_wrapper = self._create_material_wrapper()
        
        # Размещаем ноды
        self._arrange_materialx_nodes()
        
        return material_wrapper if material_wrapper else self.main_surface
    
    def _create_main_surface(self):
        """Создает основную MaterialX поверхность"""
        safe_name = clean_node_name(self.material_name)
        if not safe_name:
            safe_name = "materialx_surface"
        
        surface_name = generate_unique_name(self.matnet_node, "surface", f"{safe_name}_surface")
        
        # Пробуем создать разные типы MaterialX поверхностей
        for surface_type in self.available_surface_types:
            try:
                surface = self.matnet_node.createNode(surface_type, surface_name)
                if surface:
                    self.log_debug(f"Создана MaterialX поверхность типа: {surface_type}")
                    self.created_nodes['main_surface'] = surface
                    return surface
            except Exception as e:
                self.log_debug(f"Не удалось создать {surface_type}: {e}")
                continue
        
        self.log_error("Не удалось создать MaterialX поверхность любого типа")
        return None
    
    def _assign_textures_directly_materialx(self, texture_maps):
        """Исправленное прямое назначение файлов в MaterialX"""
        self.log_debug(f"MaterialX: прямое назначение {len(texture_maps)} текстур")
        
        # MaterialX карта назначения
        materialx_assignments = {
            "BaseMap": ["base_color", "diffuse_color", "basecolor"],
            "Normal": ["normal", "normalmap", "normal_map"],
            "Roughness": ["specular_roughness", "roughness"],
            "Metallic": ["metalness", "metallic"],
            "AO": ["diffuse_roughness", "ao"],
            "Emissive": ["emission_color", "emission"],
            "Opacity": ["opacity", "alpha"],
            "Height": ["displacement", "height"],
            "Specular": ["specular", "specular_color"]
        }
        
        successful_count = 0
        
        for texture_type, texture_path in texture_maps.items():
            if texture_type in materialx_assignments:
                success = False
                for param_name in materialx_assignments[texture_type]:
                    if self.main_surface.parm(param_name):
                        try:
                            self.main_surface.parm(param_name).set(texture_path)
                            is_udim = UDIM_SUPPORT and is_udim_texture(texture_path)
                            udim_label = " (UDIM)" if is_udim else ""
                            self.log_debug(f"✓ MaterialX прямо назначена {texture_type} через {param_name}: {os.path.basename(texture_path)}{udim_label}")
                            success = True
                            break
                        except Exception as e:
                            self.log_debug(f"Ошибка назначения {param_name}: {e}")
                            continue
                
                if success:
                    successful_count += 1
                else:
                    self.log_debug(f"✗ MaterialX не удалось назначить {texture_type}")
        
        self.log_debug(f"MaterialX прямо назначено {successful_count} из {len(texture_maps)} текстур")
    
    def _create_image_nodes(self, texture_maps):
        """Создает mtlximage ноды для каждой текстуры"""
        image_nodes = {}
        
        for texture_type, texture_path in texture_maps.items():
            try:
                # Создаем уникальное имя для image ноды
                safe_texture_type = clean_node_name(texture_type.lower())
                image_name = generate_unique_name(
                    self.matnet_node, 
                    "mtlximage", 
                    f"{clean_node_name(self.material_name)}_{safe_texture_type}_img"
                )
                
                # Создаем mtlximage ноду
                image_node = self.matnet_node.createNode("mtlximage", image_name)
                if not image_node:
                    self.log_error(f"Не удалось создать mtlximage для {texture_type}")
                    continue
                
                # Настраиваем image ноду
                self._configure_image_node(image_node, texture_type, texture_path)
                
                image_nodes[texture_type] = image_node
                self.created_nodes[f'image_{texture_type}'] = image_node
                
                # Логирование
                is_udim = UDIM_SUPPORT and is_udim_texture(texture_path)
                udim_label = " (UDIM)" if is_udim else ""
                self.log_debug(f"Создана image нода для {texture_type}: {image_name}{udim_label}")
                
            except Exception as e:
                self.log_error(f"Ошибка создания image ноды для {texture_type}: {e}")
                continue
        
        return image_nodes
    
    def _configure_image_node(self, image_node, texture_type, texture_path):
        """Настраивает mtlximage ноду"""
        try:
            # Устанавливаем путь к файлу
            if image_node.parm("file"):
                image_node.parm("file").set(texture_path)
            
            # Специальные настройки для разных типов текстур
            if texture_type == "Normal":
                # Для нормалей устанавливаем правильный color space
                if image_node.parm("signature"):
                    try:
                        image_node.parm("signature").set("vector3")
                    except:
                        pass
                
                if image_node.parm("colorspace"):
                    try:
                        image_node.parm("colorspace").set("Raw")
                    except:
                        pass
            
            elif texture_type in ["Roughness", "Metallic", "AO", "Height", "Opacity"]:
                # Для односложных текстур устанавливаем float signature
                if image_node.parm("signature"):
                    try:
                        image_node.parm("signature").set("float")
                    except:
                        pass
                
                if image_node.parm("colorspace"):
                    try:
                        image_node.parm("colorspace").set("Raw")
                    except:
                        pass
            
            elif texture_type in ["BaseMap", "Emissive"]:
                # Для цветных текстур
                if image_node.parm("signature"):
                    try:
                        image_node.parm("signature").set("color3")
                    except:
                        pass
                
                if image_node.parm("colorspace"):
                    try:
                        image_node.parm("colorspace").set("sRGB")
                    except:
                        pass
            
            self.log_debug(f"Настроена image нода для {texture_type}")
            
        except Exception as e:
            self.log_error(f"Ошибка настройки image ноды для {texture_type}: {e}")
    
    def _connect_image_nodes_properly(self, image_nodes, texture_maps):
        """Исправленное подключение mtlximage нод к поверхности"""
        self.log_debug(f"MaterialX: подключение {len(image_nodes)} image нод")
        
        # MaterialX карта подключений
        connection_map = {
            "BaseMap": "base_color",
            "Normal": "normal", 
            "Roughness": "specular_roughness",
            "Metallic": "metalness",
            "AO": "diffuse_roughness",
            "Emissive": "emission_color",
            "Opacity": "opacity",
            "Height": "displacement",
            "Specular": "specular"
        }
        
        connected_count = 0
        
        for texture_type, image_node in image_nodes.items():
            if texture_type in connection_map:
                surface_input = connection_map[texture_type]
                
                try:
                    # Правильное подключение MaterialX нод
                    success = self._connect_materialx_nodes(image_node, self.main_surface, surface_input)
                    
                    if success:
                        connected_count += 1
                        is_udim = UDIM_SUPPORT and is_udim_texture(texture_maps[texture_type])
                        udim_label = " (UDIM)" if is_udim else ""
                        self.log_debug(f"✓ MaterialX подключено {texture_type} -> {surface_input}{udim_label}")
                    else:
                        self.log_debug(f"✗ MaterialX не удалось подключить {texture_type}")
                        
                except Exception as e:
                    self.log_debug(f"Ошибка подключения MaterialX {texture_type}: {e}")
        
        self.log_debug(f"MaterialX подключено {connected_count} из {len(image_nodes)} image нод")
    
    def _connect_materialx_nodes(self, source_node, target_node, target_input):
        """Правильное подключение MaterialX нод"""
        try:
            # Определяем выходной параметр image ноды
            source_output = "out"  # Стандартный выход mtlximage
            
            # Проверяем наличие параметров
            source_output_parm = source_node.parm(source_output)
            target_input_parm = target_node.parm(target_input)
            
            if not source_output_parm:
                # Пробуем альтернативные выходы
                for alt_output in ["out", "outa", "outcolor"]:
                    if source_node.parm(alt_output):
                        source_output = alt_output
                        source_output_parm = source_node.parm(alt_output)
                        break
                else:
                    self.log_debug(f"Не найден выход {source_output} в {source_node.name()}")
                    return False
            
            if not target_input_parm:
                self.log_debug(f"Не найден вход {target_input} в {target_node.name()}")
                return False
            
            # MaterialX подключение через setExpression
            connection_expr = f"ch('{source_node.path()}/{source_output}')"
            target_input_parm.setExpression(connection_expr)
            
            self.log_debug(f"MaterialX подключено: {source_node.name()}.{source_output} -> {target_node.name()}.{target_input}")
            return True
            
        except Exception as e:
            self.log_debug(f"Ошибка MaterialX подключения: {e}")
            return False
    
    def _create_material_wrapper(self):
        """Создает material wrapper для MaterialX"""
        try:
            material_name = generate_unique_name(self.matnet_node, "material", clean_node_name(self.material_name))
            material_node = self.matnet_node.createNode("material", material_name)
            
            if material_node and self.main_surface:
                # Подключаем поверхность к материалу
                try:
                    if material_node.parm("surface"):
                        # Подключение через expression
                        surface_expr = f"ch('{self.main_surface.path()}/surface')"
                        material_node.parm("surface").setExpression(surface_expr)
                    elif material_node.parm("shop_surfacepath"):
                        material_node.parm("shop_surfacepath").set(self.main_surface.path())
                    
                    self.created_nodes['material_wrapper'] = material_node
                    self.log_debug(f"Создан MaterialX wrapper: {material_node.path()}")
                    return material_node
                    
                except Exception as e:
                    self.log_error(f"Ошибка подключения поверхности к wrapper: {e}")
                    return material_node
            
            return material_node
            
        except Exception as e:
            self.log_error(f"Ошибка создания MaterialX wrapper: {e}")
            return None
    
    def _arrange_materialx_nodes(self):
        """Размещает MaterialX ноды в network editor"""
        try:
            if not self.main_surface:
                return
            
            # Размещаем основную поверхность
            self.main_surface.moveToGoodPosition()
            
            # Размещаем image ноды слева от поверхности
            surface_pos = self.main_surface.position()
            
            image_nodes = [node for key, node in self.created_nodes.items() if key.startswith('image_')]
            
            for i, image_node in enumerate(image_nodes):
                try:
                    # Размещаем image ноды в колонку слева
                    new_pos = hou.Vector2(surface_pos.x() - 3, surface_pos.y() + (i - len(image_nodes)/2) * 1.5)
                    image_node.setPosition(new_pos)
                except Exception as e:
                    self.log_debug(f"Не удалось разместить {image_node.name()}: {e}")
                    image_node.moveToGoodPosition()
            
            # Размещаем material wrapper справа
            if 'material_wrapper' in self.created_nodes:
                material_wrapper = self.created_nodes['material_wrapper']
                wrapper_pos = hou.Vector2(surface_pos.x() + 3, surface_pos.y())
                material_wrapper.setPosition(wrapper_pos)
            
            self.log_debug("MaterialX ноды размещены в network editor")
            
        except Exception as e:
            self.log_error(f"Ошибка размещения MaterialX нод: {e}")
    
    def get_created_nodes(self):
        """Возвращает словарь созданных нод"""
        return self.created_nodes.copy()
    
    def get_main_material_node(self):
        """Возвращает основную ноду материала для назначения"""
        # Приоритет: material_wrapper -> main_surface
        if 'material_wrapper' in self.created_nodes:
            return self.created_nodes['material_wrapper']
        elif self.main_surface:
            return self.main_surface
        else:
            return None


# Функции-обертки для создания материалов

def create_principled_network(matnet_node, material_name, texture_maps, material_type="principledshader", logger=None):
    """
    Функция-обертка для создания Principled Shader сети
    
    Args:
        matnet_node: Material network нода
        material_name: Имя материала
        texture_maps: Словарь с текстурами
        material_type: Тип материала
        logger: Логгер (опционально)
        
    Returns:
        hou.Node: Созданный материал или None
    """
    builder = PrincipledBuilder(matnet_node, material_name, material_type, logger)
    return builder.create_material_network(texture_maps)


def create_materialx_network(matnet_node, material_name, texture_maps, logger=None):
    """
    Функция-обертка для создания MaterialX сети
    
    Args:
        matnet_node: MaterialX network нода
        material_name: Имя материала  
        texture_maps: Словарь с текстурами
        logger: Логгер (опционально)
        
    Returns:
        hou.Node: Созданный материал или None
    """
    builder = MaterialXBuilder(matnet_node, material_name, logger)
    return builder.create_material_network(texture_maps)


def create_material_network_universal(matnet_node, material_name, texture_maps, material_type="principledshader", logger=None):
    """
    Универсальная функция создания материалов
    
    Args:
        matnet_node: Material network нода
        material_name: Имя материала
        texture_maps: Словарь с текстурами
        material_type: Тип материала (principledshader, materialx, redshift::Material)
        logger: Логгер (опционально)
        
    Returns:
        hou.Node: Созданный материал или None
    """
    
    if material_type == "materialx":
        return create_materialx_network(matnet_node, material_name, texture_maps, logger)
    else:
        return create_principled_network(matnet_node, material_name, texture_maps, material_type, logger)


# Функции проверки доступности

def is_principled_available():
    """Проверяет доступность Principled Shader в Houdini"""
    try:
        node_types = hou.nodeTypeCategories()["Vop"].nodeTypes()
        principled_types = ["principledshader", "principledshader::2.0", "material"]
        
        return any(node_type in node_types for node_type in principled_types)
        
    except Exception:
        return False


def is_redshift_available():
    """Проверяет доступность Redshift материалов"""
    try:
        node_types = hou.nodeTypeCategories()["Vop"].nodeTypes()
        redshift_types = ["redshift::Material", "redshift::StandardMaterial"]
        
        return any(node_type in node_types for node_type in redshift_types)
        
    except Exception:
        return False


def is_materialx_available():
    """Проверяет доступность MaterialX в Houdini"""
    try:
        # Проверяем наличие MaterialX нод
        node_types = hou.nodeTypeCategories()["Vop"].nodeTypes()
        materialx_types = ["mtlxstandardsurface", "mtlximage", "usdpreviewsurface"]
        
        available_count = sum(1 for node_type in materialx_types if node_type in node_types)
        return available_count >= 2  # Нужны хотя бы image и surface ноды
        
    except Exception:
        return False


def get_available_material_types():
    """Возвращает список доступных типов материалов"""
    available_types = []
    
    if is_principled_available():
        available_types.append("principledshader")
    
    if is_redshift_available():
        available_types.append("redshift::Material")
    
    if is_materialx_available():
        available_types.append("materialx")
    
    return available_types


def get_material_builders_info():
    """Возвращает информацию о доступных построителях материалов"""
    return {
        "principled": {
            "available": is_principled_available(),
            "types": ["principledshader", "principledshader::2.0", "material"]
        },
        "redshift": {
            "available": is_redshift_available(),
            "types": ["redshift::Material", "redshift::StandardMaterial"]
        },
        "materialx": {
            "available": is_materialx_available(),
            "types": ["mtlxstandardsurface", "usdpreviewsurface", "standardsurface"]
        }
    }