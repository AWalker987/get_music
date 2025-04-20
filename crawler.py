import requests
import json
import sys
import os

# 获取命令行参数
if len(sys.argv) > 1:
    song_name = sys.argv[1]
    platform = "qq"  # 默认平台
    if len(sys.argv) > 2:
        platform = sys.argv[2]
else:
    print("请输入歌曲名称作为参数！")
    sys.exit(1)

# 请求的URL
url = "https://music.txqq.pro/"

# 请求头部
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10,0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

# 请求的数据
data = {
    "input": song_name,     # 歌曲名称
    "filter": "name",       # 按歌曲名称搜索
    "type": platform,       # 音乐平台类型
    "page": 1               # 查询结果的页码
}

try:
    # 发送POST请求
    response = requests.post(url, data=data, headers=headers)
    
    # 如果请求成功，解析返回的JSON数据
    if response.status_code == 200:
        json_data = response.json()  # 解析JSON数据
        
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 构造绝对路径
        file_path = os.path.join(current_dir, 'songs_data.json')
        
        # 将搜索结果保存到JSON文件
        with open(file_path, 'w', encoding='utf-8') as json_file:
            json.dump(json_data, json_file, ensure_ascii=False, indent=4)
        
        print("数据已保存到 'songs_data.json' 文件")
        
        # 打印歌曲信息
        for song in json_data.get("data", []):
            print(f"歌曲名称: {song.get('title', '未知')}")
            print(f"作者: {song.get('author', '未知')}")
            print(f"歌曲链接: {song.get('link', '无')}")
            print(f"下载链接: {song.get('url', '无')}")
            print("-" * 50)
    else:
        print(f"请求失败，状态码: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"发生错误: {e}")
    sys.exit(1)