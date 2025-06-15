# 进程管理器（含端口）

本项目是一个基于 PyQt5 的 Windows 桌面进程管理器，支持进程查看、端口显示、进程终止等功能。

## 功能特性
- 实时显示所有进程的 PID、进程名、用户名、监听端口
- 支持进程名、PID、端口模糊搜索（支持*通配符）
- 一键终止进程
- 进程命令行详情查看与复制
- 列宽自适应，界面美观无遮挡
- 支持右键菜单操作

## 环境依赖
- Python >= 3.13
- PyQt5
- psutil
- pyperclip

可通过如下命令安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法
1. 运行 `main.py` 启动程序：
   ```bash
   python main.py
   ```
2. 在界面中可实时查看进程、端口信息，支持搜索和终止操作。

## 项目结构
- `main.py`：主程序入口
- `process_manager_icon.png`：程序图标
- `requirements.txt`、`pyproject.toml`：依赖说明

## 许可
本项目仅供学习与交流使用。
