# 进程管理器 - 打包说明

## 环境准备

### 1. 创建虚拟环境（如果还没有）
```bash
python -m venv venv
```

### 2. 激活虚拟环境
```bash
# Windows
venv\Scripts\activate.bat

# 或者在PowerShell中
venv\Scripts\Activate.ps1
```

### 3. 验证虚拟环境
激活后，命令行提示符前应该显示 `(venv)`

## 一键打包

### 运行打包脚本
```bash
build.bat
```

打包脚本会自动完成以下步骤：
1. 检查并激活虚拟环境
2. 安装项目依赖
3. 安装构建工具（PyInstaller、Pillow）
4. 创建应用图标
5. 清理旧的构建文件
6. 使用PyInstaller打包
7. 验证构建结果
8. 清理临时文件

### 打包结果
- 成功后会在 `dist` 文件夹中生成 `ProcessManager.exe`
- 这是一个独立的可执行文件，包含所有依赖
- 可以在没有Python环境的Windows机器上运行

## 手动打包（可选）

如果需要手动打包，可以按以下步骤：

### 1. 安装依赖
```bash
pip install -r requirements.txt
pip install pyinstaller pillow
```

### 2. 创建图标
```bash
python create_icon.py
```

### 3. 运行PyInstaller
```bash
pyinstaller --clean build_config.spec
```

## 故障排除

### 常见问题

1. **虚拟环境未激活**
   - 确保看到命令行前缀 `(venv)`
   - 重新运行 `venv\Scripts\activate.bat`

2. **依赖安装失败**
   - 检查网络连接
   - 尝试使用国内镜像：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt`

3. **PyInstaller打包失败**
   - 检查main.py是否有语法错误
   - 确保所有依赖都已正确安装
   - 查看详细错误信息

4. **图标创建失败**
   - 脚本会自动使用无图标配置
   - 不影响程序功能

### 文件说明

- `build.bat`: 一键打包脚本
- `build_config.spec`: PyInstaller配置文件
- `create_icon.py`: 图标创建脚本
- `main.py`: 主程序文件
- `requirements.txt`: 项目依赖列表
- `pyproject.toml`: 项目配置文件

## 程序特性

打包后的程序具有以下特性：
- 单一exe文件，无需安装
- 包含所有Python依赖
- 支持实时进程监控
- 支持端口查看和管理
- 美观的图形界面
- 支持进程搜索和过滤
- 支持进程终止操作