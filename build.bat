@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo 进程管理器 - 自动打包脚本
echo ========================================
echo.

:: 检查是否在虚拟环境中
if not defined VIRTUAL_ENV (
    echo 检测到未激活虚拟环境，尝试激活venv...
    if exist "venv\Scripts\activate.bat" (
        echo 找到venv虚拟环境，正在激活...
        call venv\Scripts\activate.bat
    ) else (
        echo 警告：未找到venv虚拟环境，请确保已创建并激活虚拟环境
        echo 建议运行：python -m venv venv 然后 venv\Scripts\activate.bat
        pause
        exit /b 1
    )
) else (
    echo 虚拟环境已激活：%VIRTUAL_ENV%
)

:: 检查Python是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python，请检查虚拟环境配置
    pause
    exit /b 1
)

echo [1/7] 检查并安装项目依赖...
echo 安装项目依赖包...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo 错误：项目依赖安装失败
    pause
    exit /b 1
)

echo [2/7] 检查并安装构建依赖...
echo 安装 PyInstaller...
pip install pyinstaller>=6.0.0 --quiet
if errorlevel 1 (
    echo 错误：PyInstaller安装失败
    pause
    exit /b 1
)
echo 安装 Pillow (用于图标创建)...
pip install pillow --quiet

echo [3/7] 创建应用图标...
python create_icon.py
if not exist "app_icon.ico" (
    echo 警告：图标创建失败，使用默认配置
    copy /y build_config.spec build_config_no_icon.spec >nul
    powershell -Command "(Get-Content build_config_no_icon.spec) -replace 'icon=''app_icon.ico''', 'icon=None' | Set-Content build_config_no_icon.spec"
    set SPEC_FILE=build_config_no_icon.spec
) else (
    echo 图标创建成功！
    set SPEC_FILE=build_config.spec
)

echo [4/7] 清理之前的构建文件...
if exist "dist" rmdir /s /q "dist" >nul 2>&1
if exist "build" rmdir /s /q "build" >nul 2>&1

echo [5/7] 开始打包应用程序...
echo 这可能需要几分钟时间，请耐心等待...
pyinstaller --clean %SPEC_FILE%
if errorlevel 1 (
    echo 错误：PyInstaller打包失败
    pause
    exit /b 1
)

echo [6/7] 检查构建结果...
if exist "dist\ProcessManager.exe" (
    echo.
    echo ========================================
    echo 🎉 构建成功！
    echo ========================================
    echo 可执行文件位置：%cd%\dist\ProcessManager.exe
    echo 文件大小：
    for %%I in ("dist\ProcessManager.exe") do echo   %%~zI 字节
    echo.
    echo [7/7] 清理临时文件...
    if exist "build" rmdir /s /q "build" >nul 2>&1
    if exist "build_config_no_icon.spec" del "build_config_no_icon.spec" >nul 2>&1
    if exist "ProcessManager.spec" del "ProcessManager.spec" >nul 2>&1
    
    echo.
    echo 构建完成！您可以在 dist 文件夹中找到 ProcessManager.exe
    echo 这是一个独立的可执行文件，可以在没有Python环境的机器上运行。
    echo.
    echo 程序特性：
    echo - 单一exe文件，无需安装
    echo - 包含所有依赖，可独立运行
    echo - 支持进程管理和端口查看
    echo.
    
    set /p choice="是否现在运行程序？(y/n): "
    if /i "%choice%"=="y" (
        echo 启动程序...
        start "" "dist\ProcessManager.exe"
    )
) else (
    echo.
    echo ========================================
    echo ❌ 构建失败！
    echo ========================================
    echo 请检查上面的错误信息。
    echo 常见问题：
    echo 1. 确保所有依赖都已正确安装
    echo 2. 检查main.py文件是否存在语法错误
    echo 3. 确保有足够的磁盘空间
    echo.
)

echo.
pause