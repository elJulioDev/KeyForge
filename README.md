# KeyForge - Advanced Contextual Key Remapping

This project is a modern and robust desktop tool developed in Python for real-time key management and remapping. Unlike simple remapping scripts, **KeyForge** offers a professional graphical interface (GUI) and an intelligent context detection engine, allowing keyboard rules to apply globally or only when a specific application is in the foreground.

It is designed with a modular architecture that separates the key interception logic (low-level Hooks) from the user interface, ensuring optimal performance with no input lag, ideal for productivity workflows or gaming.

## Main Features
* **Hybrid Remapping Engine:**
    * **Hold Mode:** The remapped key remains physically pressed while the user holds down the original key.
    * **Toggle Mode:** Converts any key into a switch (On/Off), ideal for automating held actions without physical effort.
    * **Zero Latency:** Optimized algorithm using O(1) Hash Map lookups for instant response times.
    * **Recursion Prevention:** Internal algorithm that prevents infinite loops if rules intersect (e.g., A->B and B->A).

* **Smart Focus:**
    * **Contextual Detection:** Allows linking key profiles to a specific window (e.g., "Minecraft", "Photoshop"). If you switch windows, the script pauses automatically.
    * **WinEventHook (Optimization):** On Windows, it uses the low-level API (`user32.dll`) to detect focus changes via events instead of constant polling, reducing CPU usage to nearly zero.

* **Enhanced User Experience (New in v1.4):**
    * **Dynamic Splash Screen:** A polished startup experience that automatically adapts to your selected theme (Light/Dark) and displays loading progress.
    * **Automatic Updates:** Integrated system that checks GitHub Releases to notify you when a new version is available, ensuring you always have the latest features and fixes.

* **Personalization & Accessibility Hub:**
    * **Theme Selector:** Instantly switch between multiple visual styles, including Light (Cosmo, Flatly, Yeti) and Dark (Darkly, Cyborg, Vapor) themes to match your system or preference.
    * **Language Switcher:** Change interface language (English/Spanish) directly from the GUI.
    * **Auto-Restart System:** The application intelligently restarts itself to apply visual and language changes seamlessly.

* **Advanced Diagnostics (New in v1.4):**
    * **Professional Logging:** Robust rotating log system that tracks errors and performance metrics without filling up your disk (auto-cleanup included).
    * **Performance Monitoring:** Latency tracking to ensure the hook engine remains responsive under load.

* **Modern and Functional Interface:**
    * **Dark Mode Design:** Built with `ttkbootstrap` for a clean and professional aesthetic.
    * **Floating Widget (Mini-Mode):** Ability to minimize the app to a semi-transparent floating widget that visually indicates the script status (Active/Inactive) without being intrusive.
    * **CRUD Rule Manager:** Interactive table to add, edit, and delete multiple remapping rules simultaneously.

* **Persistence and Localization:**
    * Automatic configuration saving system in JSON.
    * Multi-language support (Spanish/English) with dynamic loading from `lang.json`.

## Technologies Used
The project uses a stack focused on operating system integration and user experience:
* **Language:** Python 3.8+
* **GUI Framework:** `ttkbootstrap` (Modern wrapper for Tkinter).
* **Core Logic:**
    * `keyboard`: For installing global keyboard hooks.
    * `pygetwindow`: For active window management and detection.
    * `ctypes` (WinAPI): For deep integration with Windows events.
    * `requests` & `packaging`: For the auto-update mechanism.
* **Packaging:** Structure prepared for compilation with `PyInstaller` (relative path support with `sys._MEIPASS`).

## Prerequisites
Ensure you have the following installed and configured:
* Python 3.8 or higher
* Administrator Privileges (Required for the `keyboard` library to intercept system events).
* Windows Operating System (Recommended for full window detection support).

## Installation and Configuration
Follow these steps to set up the project in your local environment:

1. **Clone the repository:**
```bash
git clone [https://github.com/elJulioDev/keyforge.git](https://github.com/elJulioDev/keyforge.git)
cd keyforge
```

2. **Create and activate a virtual environment:**
```bash
python -m venv venv
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the application:**
**Note:** It is crucial to run the terminal as Administrator for the keyboard hooks to work correctly.
```bash
 python KeyForge.py
```

## System Usage
1. **Rule Management**
    * In the "Rules" tab, click "Add".
    * Use the "🔍 Detect" button to capture the physical key you want to replace and the target key.
    * Select the mode (Hold for normal behavior, Toggle for switch).
2. **Target App Configuration**
    * In the Dashboard, enable "Focus on specific application".
    * Select the desired process from the dropdown list (eg: `notepad.exe`).
    * KeyForge will only intercept keys when that window is active.
3. **Personalization**
    * Navigate to the **"Accessibility"** tab.
    * Select your preferred language or choose a new visual theme from the list.
    * The application will automatically restart to apply the new settings.
4. **Widget Mode**
    * Click the "Minimize" button. The main window will hide, and a small floating icon will appear.
    * The icon changes color (Gray -> Neon Green) to indicate if the script is actively intercepting keys.
    * Double-click the widget to restore the main window.

## Project Structure

```text
keyforge/
├── data/                               # External data files
│   ├── config.json                     # Rule persistence and options
│   └── lang.json                       # Translation file (ES/EN)
├── src/                                # Modular source code
│   ├── config/                         # Configuration managers and constants
│   │   ├── config_manager.py
│   │   └── constants.py
│   ├── core/                           # Business logic (Backend)
│   │   ├── app_monitor.py              # Window detection (Polling/Hooks)
│   │   ├── key_handler.py              # Remapping logic (O(1) Map)
│   │   └── window_event_monitor.py     # ctypes wrapper for WinAPI
│   ├── gui/                            # Graphical Interface (Frontend)
│   │   ├── accessibility_settings.py   # Language & Theme configuration
│   │   ├── components.py               # Reusable widgets (Status, Buttons)
│   │   ├── main_window.py              # Main window and orchestrator
│   │   ├── minimized_window.py         # Floating widget (Canvas drawing)
│   │   ├── rules_manager.py            # Rule management table (Treeview)
│   │   └── splash_screen.py            # Dynamic loading screen [New]
│   └── utils/                          # General utilities
│       ├── auto_updater.py             # GitHub Releases checker [New]
│       ├── logger.py                   # Rotating log system [New]
│       └── window_manager.py           # Window centering and dragging
├── KeyForge.py                         # Entry Point
├── requirements.txt                    # Project dependencies
└── README.md                           # Documentation
```

## License
This project is open source and is distributed under the MIT license.
