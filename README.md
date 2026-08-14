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
    * **Linux:** Uses `wmctrl`/`xdotool` (X11/XWayland) as a polling fallback — see [Linux extra packages](#linux-extra-packages). Not guaranteed under a strict native-Wayland session without XWayland.

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
    * **Multi-Theme Design:** Built with `ttkbootstrap` supporting Light (Cosmo, Flatly, Yeti) and Dark (Darkly, Cyborg, Vapor) themes, switchable from the Accessibility tab.
    * **Floating Widget (Mini-Mode):** Ability to minimize the app to a semi-transparent floating widget that visually indicates the script status (Active/Inactive) without being intrusive.
    * **CRUD Rule Manager:** Interactive table to add, edit, and delete multiple remapping rules simultaneously.

* **Persistence and Localization:**
    * Automatic configuration saving system in JSON.
    * Multi-language support (Spanish/English) with dynamic loading from `lang.json`.

## Technologies Used
The project uses a stack focused on operating system integration and user experience:
* **Language:** Python 3.11+
* **GUI Framework:** `ttkbootstrap` (Modern wrapper for Tkinter).
* **Core Logic:**
    * `keyboard`: For installing global keyboard hooks.
    * `pygetwindow`: Active window detection on Windows/macOS (on Linux this library is not supported; `wmctrl`/`xdotool` are used instead, see below).
    * `Pillow`: Renders the app's icon set (real icons, no emoji) from `assets/icons/`.
    * `ctypes` (WinAPI): For deep integration with Windows events.
    * `pywin32`: Windows-only (installed conditionally via environment marker in `pyproject.toml`).
    * `requests` & `packaging`: For the auto-update mechanism.
* **Packaging:** Structure prepared for compilation with `PyInstaller` (relative path support with `sys._MEIPASS`).

## Prerequisites
Ensure you have the following installed and configured:
* Python 3.11 or higher
* Windows: Administrator Privileges (required for the `keyboard` library to intercept system events).
* Linux: your user needs access to input devices — see [Linux permissions](#linux-permissions) below. Root is **not** required.

## Installation and Configuration
Follow these steps to set up the project in your local environment:

1. **Clone the repository:**
```bash
git clone https://github.com/elJulioDev/KeyForge.git
cd keyforge
```

2. **Install dependencies and create virtual environment:**
```bash
uv sync
```

3. **Run the application:**
**Windows note:** run the terminal as Administrator for the keyboard hooks to work correctly.
```bash
uv run python main.py
```

## Linux permissions
The `keyboard` library reads raw input events, which on Linux requires either root or explicit access to `/dev/input`. Running as root is **not recommended**; instead grant your user access once:

```bash
sudo usermod -aG input $USER

sudo tee /etc/udev/rules.d/50-keyforge-input.rules > /dev/null <<'EOF'
KERNEL=="uinput", GROUP="input", MODE="0660"
SUBSYSTEM=="input", GROUP="input", MODE="0660"
EOF

sudo udevadm control --reload-rules && sudo udevadm trigger
```

Log out and back in (or reboot) so the group membership takes effect.

## Linux extra packages
A couple of things Python's `pip` can't install for you:

* **Tkinter** usually ships with Python on Debian/Ubuntu, but not on Arch/CachyOS — install it separately:
```bash
# Arch / CachyOS
sudo pacman -S tk
# Debian / Ubuntu
sudo apt install python3-tk
```

* **`wmctrl` + `xdotool`** power the Smart Focus window detection (app list + active window). Without them the target-app dropdown stays empty:
```bash
# Arch / CachyOS
sudo pacman -S wmctrl xdotool
# Debian / Ubuntu
sudo apt install wmctrl xdotool
```

## System Usage
1. **Rule Management**
    * In the "Rules" tab, click "Add".
    * Use the "Detect" button to capture the physical key you want to replace and the target key.
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
├── assets/
│   └── icons/                          # Real icon set (Lucide, no emoji) [New]
├── data/                               # External data files
│   ├── config.json                     # Rule persistence (auto-generated, gitignored)
│   └── lang.json                       # Translation file (ES/EN)
├── src/                                # Modular source code
│   ├── config/                         # Configuration managers and constants
│   │   ├── config_manager.py
│   │   ├── constants.py
│   │   └── translation_manager.py      # Language hot-reload (ES/EN)
│   ├── core/                           # Business logic (Backend)
│   │   ├── app_monitor.py              # Window detection (win32 / wmctrl+xdotool fallback)
│   │   ├── key_handler.py              # Remapping logic (O(1) Map)
│   │   └── window_event_monitor.py     # ctypes wrapper for WinAPI
│   ├── gui/                            # Graphical Interface (Frontend)
│   │   ├── accessibility_settings.py   # Language & Theme configuration
│   │   ├── components.py               # Reusable widgets (Status, Buttons)
│   │   ├── main_window.py              # Main window and orchestrator
│   │   ├── minimized_window.py         # Floating widget (Canvas drawing)
│   │   ├── rules_manager.py            # Rule management table (Treeview)
│   │   └── splash_screen.py            # Dynamic loading screen
│   └── utils/                          # General utilities
│       ├── auto_updater.py             # GitHub Releases checker
│       ├── icons.py                    # Loads/tints real icons from assets/icons [New]
│       ├── logger.py                   # Rotating log system
│       └── window_manager.py           # Window centering, dragging, dialog stacking
├── .gitignore                          # [New]
├── main.py                             # Entry Point
├── pyproject.toml                      # Project metadata & dependencies
├── uv.lock                             # Locked dependencies
└── README.md                           # Documentation
```

## License
This project is open source and is distributed under the MIT license.
