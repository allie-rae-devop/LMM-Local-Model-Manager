# Changelog

All notable changes to the **Local Model Manager (LMM)** project will be documented in this file.

## [0.1.0] - 2025-12-01

### 🚀 Major Features
- **Unified GUI:** Replaced separate windows with a single, tabbed `MainWindow` using `sv_ttk` for native Dark Mode.
- **Dashboard:** Added real-time VRAM monitoring, Temperature readout, and an "Active AI Processes" tree view.
- **Game Mode:** Implemented a process killer to instantly free up VRAM for gaming (targets Ollama, Handy, Python).
- **External Models:** Added "Process Watcher" settings to track non-Ollama AI agents (e.g., Handy AI) in the dashboard.
- **Hardware Monitor:** integrated `nvidia-ml-py` and `psutil` for deep system monitoring.

### 🛠️ Architecture & Refactoring
- **Modularization:** Split monolithic script into `core/`, `gui/`, and `utils/` packages.
- **Dependency Update:** Migrated from `pynvml` to `nvidia-ml-py`.
- **Settings:** Switched to a robust JSON-based `ConfigManager`.

### 🐛 Fixes
- Fixed System Tray crashing on exit.
- Fixed Window closing behavior (`WM_DELETE_WINDOW` protocol).
- Fixed high DPI scaling issues in GUI.