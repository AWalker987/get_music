@echo off
chcp 65001
echo 正在检查并安装必要的依赖库...

echo 安装requests...
pip install requests

echo 安装pyncm (用于NCM格式转换)...
pip install pyncm

echo 安装ffmpeg-python (用于音频处理)...
pip install ffmpeg-python

echo 所有依赖安装完成！
pause