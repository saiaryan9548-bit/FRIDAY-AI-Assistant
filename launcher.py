"""HANDS: universal Windows application launcher."""

import os
import shutil
import subprocess
import tempfile

import config


# ---------------------------------------------------------
# BASIC TARGET LAUNCHER
# ---------------------------------------------------------

def _try_target(target):
    """Try to launch a Windows target."""

    target = os.path.expandvars(target)

    try:
        # File, folder, or executable path
        if os.path.exists(target):
            os.startfile(target)
            return True

        # Program available on PATH
        found = shutil.which(target)

        if found:
            subprocess.Popen(
                [found],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True

        # Windows registered application/protocol
        os.startfile(target)
        return True

    except (OSError, FileNotFoundError):
        return False


# ---------------------------------------------------------
# CLEAN SPOKEN APP NAME
# ---------------------------------------------------------

def _clean_name(name):
    """Clean the name received from speech recognition."""

    name = name.lower().strip()

    # Speech recognition sometimes adds these words
    removable_words = [
        " app",
        " application",
        " program",
    ]

    changed = True

    while changed:
        changed = False

        for word in removable_words:
            if name.endswith(word):
                name = name[:-len(word)].strip()
                changed = True

    return name


# ---------------------------------------------------------
# WINDOWS SPECIAL APPLICATIONS
# ---------------------------------------------------------

def _open_special_windows_app(name):
    """Open common Windows applications using their commands."""

    special_apps = {

        # Windows
        "calculator": "calculator:",
        "calc": "calculator:",

        "notepad": "notepad",
        "paint": "mspaint",

        "file explorer": "explorer",
        "explorer": "explorer",

        "settings": "ms-settings:",
        "windows settings": "ms-settings:",

        "task manager": "taskmgr",

        "command prompt": "cmd",
        "cmd": "cmd",

        "powershell": "powershell",

        # Microsoft Store
        "microsoft store": "ms-windows-store:",
        "store": "ms-windows-store:",

    }

    target = special_apps.get(name)

    if target:
        return _try_target(target)

    return False


# ---------------------------------------------------------
# START MENU SEARCH
# ---------------------------------------------------------

def _search_start_menu(name):
    """Search Windows Start Menu shortcuts."""

    locations = [
        os.path.expandvars(
            r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"
        ),
        os.path.expandvars(
            r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"
        ),
    ]

    name = name.lower()

    # First look for an exact match
    for location in locations:

        if not os.path.exists(location):
            continue

        for root, dirs, files in os.walk(location):

            for file in files:

                if not file.lower().endswith(".lnk"):
                    continue

                app_name = os.path.splitext(file)[0].lower()

                if app_name == name:
                    shortcut = os.path.join(root, file)

                    if _try_target(shortcut):
                        return True

    # Then look for partial matches
    for location in locations:

        if not os.path.exists(location):
            continue

        for root, dirs, files in os.walk(location):

            for file in files:

                if not file.lower().endswith(".lnk"):
                    continue

                app_name = os.path.splitext(file)[0].lower()

                if name in app_name or app_name in name:
                    shortcut = os.path.join(root, file)

                    if _try_target(shortcut):
                        return True

    return False


# ---------------------------------------------------------
# WINDOWS APPX / MICROSOFT STORE APPS
# ---------------------------------------------------------

def _search_appx(name):
    """
    Search installed Microsoft Store / packaged applications.

    Uses PowerShell's Get-StartApps command, which asks Windows
    for applications registered with the Start menu.
    """

    name = name.lower().strip()

    powershell_script = r"""
$apps = Get-StartApps | Select-Object Name, AppID
$apps | ConvertTo-Json -Compress
"""

    try:

        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                powershell_script,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        if result.returncode != 0:
            return False

        output = result.stdout.strip()

        if not output:
            return False

        import json

        apps = json.loads(output)

        # If only one result is returned, PowerShell gives an object
        if isinstance(apps, dict):
            apps = [apps]

        exact_match = None
        partial_match = None

        for app in apps:

            app_name = str(app.get("Name", "")).strip()
            app_id = str(app.get("AppID", "")).strip()

            if not app_name or not app_id:
                continue

            app_name_lower = app_name.lower()

            # Exact match
            if app_name_lower == name:
                exact_match = app_id
                break

            # Partial match
            if name in app_name_lower:
                partial_match = app_id

        app_id = exact_match or partial_match

        if not app_id:
            return False

        # Launch through Windows shell
        return _launch_appid(app_id)

    except Exception as error:
        print(f"AppX search error: {error}")
        return False


# ---------------------------------------------------------
# APPID LAUNCHER
# ---------------------------------------------------------

def _launch_appid(app_id):
    """Launch a Windows registered application by AppID."""

    try:

        # Start menu shortcut launcher
        command = f'shell:AppsFolder\\{app_id}'

        os.startfile(command)

        return True

    except OSError:

        # Fallback through explorer.exe
        try:

            subprocess.Popen(
                [
                    "explorer.exe",
                    f"shell:AppsFolder\\{app_id}"
                ],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            return True

        except OSError:
            return False


# ---------------------------------------------------------
# INSTALLED PROGRAM SEARCH
# ---------------------------------------------------------

def _search_program_files(name):
    """
    Search common Program Files locations for executables.
    This is a fallback for traditional desktop applications.
    """

    locations = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
    ]

    name = name.lower()

    for location in locations:

        if not location or not os.path.exists(location):
            continue

        try:

            for root, dirs, files in os.walk(location):

                # Avoid extremely deep/irrelevant folders
                dirs[:] = [
                    d for d in dirs
                    if d.lower() not in {
                        "node_modules",
                        "__pycache__",
                        ".git",
                    }
                ]

                for file in files:

                    if not file.lower().endswith(".exe"):
                        continue

                    exe_name = os.path.splitext(file)[0].lower()

                    if exe_name == name:

                        path = os.path.join(root, file)

                        if _try_target(path):
                            return True

        except (PermissionError, OSError):
            continue

    return False


# ---------------------------------------------------------
# MAIN UNIVERSAL LAUNCHER
# ---------------------------------------------------------

def open_item(key):
    """
    Universal application launcher.

    Search order:

    1. Configured apps
    2. Special Windows applications
    3. Microsoft Store / AppX applications
    4. Start Menu applications
    5. Program Files executables
    6. PATH applications
    """

    name = _clean_name(key)

    print(f"Searching for application: {name}")

    # -----------------------------------------------------
    # 1. EXISTING CONFIG APPS
    # -----------------------------------------------------

    entry = config.OPENABLE.get(name)

    if entry:

        for target in entry["targets"]:

            if _try_target(target):
                print(f"Opened configured application: {name}")
                return True

    # -----------------------------------------------------
    # 2. WINDOWS SPECIAL APPS
    # -----------------------------------------------------

    if _open_special_windows_app(name):
        print(f"Opened Windows application: {name}")
        return True

    # -----------------------------------------------------
    # 3. MICROSOFT STORE / APPX
    # -----------------------------------------------------

    if _search_appx(name):
        print(f"Opened installed Store application: {name}")
        return True

    # -----------------------------------------------------
    # 4. START MENU
    # -----------------------------------------------------

    if _search_start_menu(name):
        print(f"Opened Start Menu application: {name}")
        return True

    # -----------------------------------------------------
    # 5. PROGRAM FILES
    # -----------------------------------------------------

    if _search_program_files(name):
        print(f"Opened executable application: {name}")
        return True

    # -----------------------------------------------------
    # 6. PATH FALLBACK
    # -----------------------------------------------------

    if _try_target(name):
        print(f"Opened PATH application: {name}")
        return True

    print(f"Could not find installed application: {name}")

    return False