from typing import Dict
from astrbot.api.all import *
import asyncio
import time
import subprocess
import os
import json
import requests
import shutil
import sys

# 用于跟踪每个用户的状态
USER_STATES: Dict[int, Dict[str, any]] = {}

@register("astrbot_plugin_qq_music", "YourName", "一个QQ群点歌插件", "1.0.0")
class QQMusicPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.platforms = {
            "qq": "QQ音乐",
            "netease": "网易云音乐", 
            "kugou": "酷狗音乐",
            "kuwo": "酷我音乐"
        }
        # 从配置中获取值，或使用默认值
        self.default_platform = self.config.get("default_platform", "qq")
        self.enable_conversion = self.config.get("enable_conversion", True)
        self.auto_install_deps = self.config.get("auto_install_deps", True)
        
        # 确保依赖已安装
        if self.auto_install_deps and self.enable_conversion:
            self.ensure_dependencies()
            
    def ensure_dependencies(self):
        """确保所需的依赖已安装"""
        try:
            # 检查是否已安装requests
            import requests
        except ImportError:
            print("安装requests...")
            subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
            
        if self.enable_conversion:
            try:
                # 检查是否已安装pyncm
                import pyncm
            except ImportError:
                print("安装pyncm...")
                subprocess.run([sys.executable, "-m", "pip", "install", "pyncm"], check=True)
                
            try:
                # 检查是否已安装ffmpeg-python (用于音频格式转换)
                import ffmpeg
            except ImportError:
                print("安装ffmpeg-python...")
                subprocess.run([sys.executable, "-m", "pip", "install", "ffmpeg-python"], check=True)
        
    @event_message_type(EventMessageType.ALL)
    async def handle_message(self, event: AstrMessageEvent):
        message = event.message_str
        
        # 检测"点歌："关键词
        if message.startswith("点歌：") or message.startswith("点歌:"):
            song_name = message[3:].strip()
            if song_name:
                # 分离平台信息
                platform = self.default_platform
                if " " in song_name and song_name.split(" ")[0] in self.platforms:
                    platform = song_name.split(" ")[0]
                    song_name = " ".join(song_name.split(" ")[1:])
                
                yield event.plain_result(f"正在搜索歌曲《{song_name}》({self.platforms.get(platform, '未知平台')})")
                
                # 调用搜索函数
                async for result in self.search_and_play_song(event, song_name, platform):
                    yield result
    
    async def search_and_play_song(self, event: AstrMessageEvent, song_name: str, platform: str = "qq"):
        """搜索并播放歌曲"""
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        crawler_path = os.path.join(current_dir, "crawler.py")
        songs_data_path = os.path.join(current_dir, "songs_data.json")
        
        # 检查crawler.py是否存在
        if not os.path.exists(crawler_path):
            yield event.plain_result("错误：crawler.py文件不存在，请检查插件安装。")
            return
        
        # 运行crawler.py搜索歌曲
        try:
            subprocess.run(["python", crawler_path, song_name, platform], check=True)
        except subprocess.CalledProcessError as e:
            yield event.plain_result(f"搜索歌曲时出错：{e}\n可能需要运行'首次运行请点我.bat'安装requests库。")
            return
        
        # 检查搜索结果
        if not os.path.exists(songs_data_path):
            yield event.plain_result("搜索歌曲失败，未返回结果。")
            return
        
        # 解析搜索结果
        try:
            with open(songs_data_path, 'r', encoding='utf-8') as json_file:
                json_data = json.load(json_file)
                data = json_data.get("data", [])
                
                if not data:
                    yield event.plain_result("没有找到符合要求的歌曲。")
                    return
                
                # 获取第一首歌曲信息
                song_info = data[0]
                title = song_info.get("title", "未知歌曲")
                author = song_info.get("author", "未知歌手")
                url = song_info.get("url", "")
                
                if not url:
                    yield event.plain_result(f"无法获取《{title}》的下载链接，请尝试其他歌曲。")
                    return
                
                yield event.plain_result(f"找到歌曲：《{title}》 - {author}，正在准备播放...")
                
                # 下载并播放歌曲
                async for result in self.download_and_play_song(event, song_info):
                    yield result
                
        except Exception as e:
            yield event.plain_result(f"处理搜索结果时出错：{e}")
    
    async def download_and_play_song(self, event: AstrMessageEvent, song_info):

        """下载并播放歌曲，支持格式转换"""
        title = song_info.get("title", "未知歌曲")
        author = song_info.get("author", "未知歌手")
        url = song_info.get("url", "")
        
        if not url:
            yield event.plain_result("无法获取歌曲下载链接。")
            return
        
        # 创建存储目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        songs_dir = os.path.join(current_dir, "songs")
        temp_dir = os.path.join(current_dir, "temp")
        
        if not os.path.exists(songs_dir):
            os.makedirs(songs_dir)
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # 构造文件名
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_()").strip()
        safe_author = "".join(c for c in author if c.isalnum() or c in " -_()").strip()
        if not safe_title:
            safe_title = "未知歌曲"
        if not safe_author:
            safe_author = "未知歌手"
            
        original_filename = f"{safe_title} - {safe_author}"
        
        # 临时文件和目标MP3文件
        temp_file_path = os.path.join(temp_dir, f"{original_filename}.temp")
        mp3_file_path = os.path.join(songs_dir, f"{original_filename}.mp3")
        
        # 如果MP3文件已存在，直接使用
        if os.path.exists(mp3_file_path):
            yield event.plain_result(f"《{title}》已在本地，直接播放...")
        else:
            yield event.plain_result(f"下载歌曲《{title}》中...")
            try:
                # 下载原始文件
                response = requests.get(url, stream=True)
                if response.status_code == 200:
                    with open(temp_file_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    
                    # 检测是否为NCM格式并进行转换
                    if self.enable_conversion and ('.ncm' in url.lower() or self.is_ncm_file(temp_file_path)):
                        yield event.plain_result("检测到NCM格式，正在转换...")
                        converted = await self.convert_ncm_to_mp3(temp_file_path, mp3_file_path)
                        if not converted:
                            yield event.plain_result("格式转换失败，可能是不支持的格式或文件已损坏。")
                            # 作为备选方案，尝试直接将文件作为mp3使用
                            shutil.copy(temp_file_path, mp3_file_path)
                    else:
                        # 如果不是ncm格式或不需要转换，直接复制
                        shutil.copy(temp_file_path, mp3_file_path)
                else:
                    yield event.plain_result(f"下载失败，错误码：{response.status_code}")
                    return
            except Exception as e:
                yield event.plain_result(f"下载歌曲时出错：{e}")
                return
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except:
                        pass
        
        # 发送语音消息
        try:
            chain = [
                Plain(f"🎵 正在播放：《{title}》 - {author}"),
                Record.fromFileSystem(mp3_file_path)
            ]
            
            yield event.chain_result(chain)
        except Exception as e:
            yield event.plain_result(f"播放歌曲时出错：{e}")
    
    def is_ncm_file(self, file_path):
        """简单检测文件是否为NCM格式"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(10)
                # NCM文件的头部特征
                return header.startswith(b'CTENFDAM')
        except:
            return False
    
    async def convert_ncm_to_mp3(self, input_path, output_path):
        """将NCM文件转换为MP3"""
        try:
            # 使用pyncm进行格式转换
            from pyncm.utils.decrypt import decrypt_file
            
            success = decrypt_file(input_path, output_path)
            return success
        except Exception as e:
            print(f"NCM转换出错: {e}")
            return False
        

    
    @llm_tool(name="play_song")
    async def llm_play_song(self, event: AstrMessageEvent, song_name: str, platform: str = "qq"):
        """通过LLM工具搜索并播放歌曲
        
        Args:
            song_name (string): 歌曲名称
            platform (string): 平台名称，可选值：qq, netease, kugou, kuwo
        """
        if platform not in self.platforms:
            platform = self.default_platform
            
        yield event.plain_result(f"正在搜索歌曲《{song_name}》({self.platforms.get(platform, '未知平台')})")
        
        async for result in self.search_and_play_song(event, song_name, platform):
            yield result