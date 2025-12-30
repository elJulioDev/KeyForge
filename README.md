# KeyForge - Remapeo de Teclas Avanzado y Contextual
Este proyecto es una herramienta de escritorio moderna y robusta desarrollada en Python para la gestión y remapeo de teclas en tiempo real. A diferencia de scripts sencillos de remapeo, KeyForge ofrece una interfaz gráfica profesional (GUI) y un motor de detección de contexto inteligente, permitiendo que las reglas de teclado se apliquen globalmente o únicamente cuando una aplicación específica está en primer plano.

Está diseñado con una arquitectura modular que separa la lógica de intercepción de teclas (Hooks de bajo nivel) de la interfaz de usuario, garantizando un rendimiento óptimo sin input lag, ideal para flujos de trabajo de productividad o gaming.

## 🚀 Características Principales
* **Motor de Remapeo Híbrido:**
    * **Modo Hold:** La tecla reasignada se mantiene presionada físicamente mientras el usuario sostiene la tecla original.
    * **Modo Toggle:** Convierte cualquier tecla en un interruptor (On/Off), ideal para automatizar acciones mantenidas sin esfuerzo físico.
    * **Prevención de Recursión:** Algoritmo interno que evita bucles infinitos si se cruzan reglas (ej: A->B y B->A).
* **Enfoque Inteligente (Smart Focus):**
    * **Detección Contextual:** Permite vincular perfiles de teclas a una ventana específica (ej. "Minecraft", "Photoshop"). Si cambias de ventana, el script se pausa automáticamente.
    * **WinEventHook (Optimización):** En Windows, utiliza la API de bajo nivel (`user32.dll`) para detectar cambios de foco por eventos en lugar de polling constante, reduciendo el uso de CPU a casi cero.
* **Interfaz Moderna y Funcional:**
    * **Diseño Dark Mode:** Construido con `ttkbootstrap` para una estética limpia y profesional.
    * **Widget Flotante (Mini-Mode):** Capacidad de minimizar la app a un widget flotante semitransparente que indica visualmente el estado del script (Activo/Inactivo) sin estorbar.
    * **Gestor de Reglas CRUD:** Tabla interactiva para agregar, editar y eliminar múltiples reglas de remapeo simultáneamente.
* **Persistencia y Localización:**
    * Sistema de guardado automático de configuraciones en JSON.
    * Soporte multi-idioma (Español/Inglés) con carga dinámica desde `lang.json`.

## 🛠️ Tecnologías Utilizadas
El proyecto utiliza un stack enfocado en la integración con el sistema operativo y la experiencia de usuario:
* Lenguaje: Python 3.8+
* GUI Framework: `ttkbootstrap` (Wrapper moderno para Tkinter).
* Core Logic:
    * `keyboard`: Para la instalación de hooks globales de teclado.
    * `pygetwindow`: Para la gestión y detección de ventanas activas.
    * `ctypes` (WinAPI): Para la integración profunda con eventos de Windows.
* Empaquetado: Estructura preparada para compilación con `PyInstaller` (soporte de rutas relativas con `sys._MEIPASS`).

## 📋 Pre-requisitos
Asegúrate de tener instalado y configurado lo siguiente:
* Python 3.8 o superior
* Permisos de Administrador (Necesario para que la librería `keyboard` intercepte eventos del sistema).
* Sistema Operativo Windows (Recomendado para el soporte completo de detección de ventanas).

## 🔧 Instalación y Configuración
Sigue estos pasos para levantar el proyecto en tu entorno local:

1. Clonar el repositorio:
```bash
git clone https://github.com/elJulioDev/keyforge.git
cd keyforge
```

2. Crear y activar un entorno virtual:
```bash
python -m venv venv
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Ejecutar la aplicación:
**Nota:** Es crucial ejecutar la terminal como Administrador para que los hooks de teclado funcionen correctamente.
```bash
 python KeyForge.py
```

## 🔐 Uso del Sistema
**1. Gestión de Reglas**
    * En la pestaña "Rules", pulsa "Add".
    * Usa el botón "🔍 Detect" para capturar la tecla física que deseas reemplazar y la tecla destino.
    * Selecciona el modo (Hold para comportamiento normal, Toggle para interruptor).
**2. Configuración de Objetivo (Target App)**
    * En el Dashboard, activa "Enfoque en aplicación específica".
    * Selecciona el proceso deseado de la lista desplegable (ej: `notepad.exe`).
    * KeyForge solo interceptará las teclas cuando esa ventana esté activa.
**3. Modo Widget**
    * Pulsa el botón "Minimizar". La ventana principal se ocultará y aparecerá un pequeño icono flotante.
    * El icono cambia de color (Gris -> Verde Neón) para indicar si el script está interceptando teclas activamente.
    * Doble clic en el widget para restaurar la ventana principal.

## 📂 Estructura del Proyecto

```text
keyforge/
├── data/                           # Archivos de datos externos
│   ├── config.json                 # Persistencia de reglas y opciones
│   └── lang.json                   # Archivo de traducción (ES/EN)
├── src/                            # Código fuente modular
│   ├── config/                     # Gestores de configuración y constantes
│   │   ├── config_manager.py
│   │   └── constants.py
│   ├── core/                       # Lógica de negocio (Backend)
│   │   ├── app_monitor.py          # Detección de ventanas (Polling/Hooks)
│   │   ├── key_handler.py          # Lógica de remapeo y prevención de ciclos
│   │   └── window_event_monitor.py # Wrapper de ctypes para WinAPI
│   ├── gui/                        # Interfaz Gráfica (Frontend)
│   │   ├── components.py           # Widgets reutilizables (Status, Buttons)
│   │   ├── main_window.py          # Ventana principal y orquestador
│   │   ├── minimized_window.py     # Widget flotante (Canvas drawing)
│   │   └── rules_manager.py        # Tabla de gestión de reglas (Treeview)
│   └── utils/                      # Utilidades generales
│       └── window_manager.py       # Centrado y arrastre de ventanas
├── KeyForge.py                     # Punto de entrada (Entry Point)
├── requirements.txt                # Dependencias del proyecto
```

## 👥 Créditos
Desarrollado por Alexis González como una solución avanzada para la personalización de periféricos y accesibilidad en entornos Windows.

## 📄 Licencia
Este proyecto es de código abierto y se distribuye bajo la licencia MIT.
