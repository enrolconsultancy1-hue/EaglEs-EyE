# Troubleshooting

## Python Not Found

**Error:**
```
'python' is not recognized as an internal or external command
```

**Solution:**
- Install Python 3.12+ from [python.org](https://python.org)
- During installation, check **"Add Python to PATH"**
- Restart your terminal after installation

To verify:
```powershell
python --version
```

## Missing Dependencies

**Error:**
```
ModuleNotFoundError: No module named 'watchdog'
```

**Solution:**
```powershell
# Make sure your virtual environment is activated:
.venv\Scripts\Activate.ps1

# Install all dependencies:
pip install -r requirements.txt
```

## Port Already in Use

**Error (or GUI fails to start):**
```
OSError: [WinError 10048] ... address already in use
```

**Solution:**
- Another process is using port 9103
- Use a different port:
  ```powershell
  $env:GUI_PORT = "9104"
  python -m gui.app
  ```
- Or find and stop the other process:
  ```powershell
  netstat -ano | findstr :9103
  taskkill /PID <PID> /F
  ```

## Permission Errors

**Error:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
- EaglEs EyE needs read access to your project folder
- Make sure the project path is accessible
- On Windows, avoid system-protected directories
- Run the terminal as a normal user (not Administrator)

## Project Folder Inaccessible

**Error:**
```
Project path does not exist: C:\Users\me\nonexistent
```

**Solution:**
- Verify the path is correct and the folder exists:
  ```powershell
  Test-Path "C:\Users\me\My Project"
  ```
- If the path contains spaces, it is handled automatically
- Make sure you are using the full absolute path, not a relative one

## Git Repository Not Detected

**Observation:**
After connecting a project, the twin shows `git: false`.

**Explanation:**
- EaglEs EyE checks for a `.git` subdirectory
- Not every project is a Git repository
- If your project has a `.git` folder but it is reported as missing,
  ensure the folder is readable and not hidden from the scan

## Large Project Scanning Delay

**Observation:**
The scan phase takes a long time or appears stuck.

**Explanation:**
- EaglEs EyE walks the entire directory tree (excluding `.git`,
  `node_modules`, `build`, `.venv`, `__pycache__`, and `.dart_tool`)
- Very large projects (10,000+ files) may take several seconds
- Progress is logged; wait for the notification `PROJECT TWIN CREATED`

**To speed up:**
- Exclude additional directories by editing `config/eye.config.json`
  (the `ignore` list)
- Scan only specific subfolders instead of the entire project

## GUI Shows "Loading..." Indefinitely

**Observation:**
The dashboard or other pages show "Loading..." and never update.

**Solution:**
- Check the terminal where `python -m gui.app` is running for errors
- Verify the MCP subprocess started successfully
- Restart the GUI:
  ```powershell
  # Press Ctrl+C to stop, then:
  python -m gui.app
  ```

## Reset All Data

**To erase all stored knowledge and twins:**

```powershell
# Find your memory path (default is a temp dir):
# Check the GUI startup output or set it explicitly:
$env:EAGLE_EYE_MEMORY_PATH = "C:\Users\me\eye-data"
Remove-Item -Recurse -Force "$env:EAGLE_EYE_MEMORY_PATH\knowledge.db"
Remove-Item -Recurse -Force "$env:EAGLE_EYE_MEMORY_PATH\twins"
```

Then restart the application.

## Getting Help

If you encounter an issue not covered here:
- Check the [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Review [PROJECT_STATUS.md](PROJECT_STATUS.md) for known limitations
- Open an issue at https://github.com/anomalyco/EaglEs-EyE/issues
