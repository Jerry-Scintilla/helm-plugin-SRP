@echo off
setlocal
cd /d "%~dp0"

echo ==================================================
echo  helm-plugin-srp  build script
echo ==================================================

echo.
echo [1/3] Cleaning old build artifacts...
if exist build       rmdir /s /q build
if exist dist        rmdir /s /q dist
for /d %%d in (*.egg-info) do rmdir /s /q "%%d"
echo      OK

echo.
echo [2/3] Building Vue frontend...
pushd helm_plugin_srp\frontend
call npm install
if errorlevel 1 ( echo [ERROR] npm install failed & popd & pause & exit /b 1 )
call npm run build
if errorlevel 1 ( echo [ERROR] frontend build failed & popd & pause & exit /b 1 )
popd
echo      OK

echo.
echo [2.5/3] Checking build tool...
python -m build --version >nul 2>&1
if errorlevel 1 (
    echo      build not found, installing...
    pip install build -q
    if errorlevel 1 ( echo [ERROR] pip install build failed & pause & exit /b 1 )
)
echo      OK

echo.
echo [3/3] Building Python wheel...
python -m build --wheel
if errorlevel 1 ( echo [ERROR] wheel build failed & pause & exit /b 1 )
echo      OK

echo.
echo ==================================================
echo  Build complete
echo ==================================================
for %%f in ("dist\*.whl") do echo   %%f
echo.
echo   Dev install  :  pip install -e "%~dp0"
echo   Prod install :  pip install dist\*.whl
echo.
echo   Register with Helm:
echo     curl -X POST http://localhost:8000/api/v1/admin/plugins/install
echo          -H "Authorization: Bearer ^<jwt^>"
echo          -d "{\"package_name\": \"helm-plugin-srp\"}"
echo.
endlocal
pause
