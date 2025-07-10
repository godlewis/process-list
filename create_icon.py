# -*- coding: utf-8 -*-
"""
创建应用程序图标
"""
import os

def create_simple_icon():
    """创建一个简单的进程管理器图标"""
    try:
        from PIL import Image, ImageDraw
        
        # 创建256x256的图标
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 绘制背景圆形
        margin = 20
        draw.ellipse([margin, margin, size-margin, size-margin], 
                    fill=(70, 130, 180, 255), outline=(25, 25, 112, 255), width=8)
        
        # 绘制进程符号（三个矩形代表进程列表）
        rect_width = 60
        rect_height = 20
        spacing = 25
        start_x = (size - rect_width) // 2
        start_y = (size - (3 * rect_height + 2 * spacing)) // 2
        
        for i in range(3):
            y = start_y + i * (rect_height + spacing)
            draw.rectangle([start_x, y, start_x + rect_width, y + rect_height],
                          fill=(255, 255, 255, 255), outline=(200, 200, 200, 255), width=2)
        
        # 保存为ICO格式
        img.save('app_icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        print("Icon file app_icon.ico created successfully!")
        return True
        
    except ImportError:
        print("PIL not installed, creating placeholder icon...")
        return create_placeholder_icon()
    except Exception as e:
        print(f"Error creating icon: {e}")
        return create_placeholder_icon()

def create_placeholder_icon():
    """创建占位符图标"""
    try:
        # 创建一个最小的有效ICO文件
        ico_data = (
            b'\x00\x00\x01\x00\x01\x00\x20\x20\x00\x00\x01\x00\x20\x00\xa8\x10\x00\x00\x16\x00\x00\x00'
            b'\x28\x00\x00\x00\x20\x00\x00\x00\x40\x00\x00\x00\x01\x00\x20\x00\x00\x00\x00\x00\x80\x10\x00\x00'
            + b'\x00' * 4096  # 32x32 RGBA数据
        )
        
        with open('app_icon.ico', 'wb') as f:
            f.write(ico_data)
        print("Placeholder icon created!")
        return True
    except Exception as e:
        print(f"Failed to create placeholder icon: {e}")
        return False

if __name__ == "__main__":
    create_simple_icon()