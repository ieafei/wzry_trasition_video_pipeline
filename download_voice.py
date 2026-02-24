#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
王者荣耀英雄语音包下载脚本
用于从 https://pvp.qq.com/ip/voice.html 下载指定英雄的语音包
"""

import requests
import json
import re
import os
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HonorOfKingsVoiceDownloader:
    """王者荣耀语音包下载器"""
    
    def __init__(self, base_url="https://pvp.qq.com"):
        self.base_url = base_url
        self.session = requests.Session()
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://pvp.qq.com/ip/voice.html',
        })
    
    def get_hero_list(self):
        """获取英雄列表"""
        url = f"{self.base_url}/zlkdatasys/yuzhouzhan/list/heroList.json?t={int(time.time())}"
        
        try:
            logger.info(f"获取英雄列表: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            # 英雄数据存储在 yzzyxs_4880 字段中
            heroes = data.get('yzzyxs_4880', [])
            
            logger.info(f"成功获取 {len(heroes)} 个英雄信息")
            return heroes
        except requests.RequestException as e:
            logger.error(f"获取英雄列表失败: {e}")
            return []
    
    def get_hero_voices(self, hero_id):
        """获取指定英雄的语音数据"""
        url = f"{self.base_url}/zlkdatasys/yuzhouzhan/herovoice/{hero_id}.json?t={int(time.time())}"
        
        try:
            logger.info(f"获取英雄语音数据: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            # 语音数据存储在 dqpfyy_5403 字段中，是一个数组
            voice_data = data.get('dqpfyy_5403', [])
            
            if voice_data:
                logger.info(f"成功获取英雄语音数据，共 {len(voice_data)} 条语音")
                return voice_data
            else:
                logger.warning(f"未找到英雄 {hero_id} 的语音数据")
                return None
        except requests.RequestException as e:
            logger.error(f"获取英雄语音数据失败: {e}")
            return None
    
    def search_hero_by_name(self, hero_name, heroes):
        """根据英雄名称搜索英雄"""
        target_hero = None
        
        for hero in heroes:
            # 使用正确的字段名：yzzyxm_4588 是英雄名称
            hero_name_field = hero.get('yzzyxm_4588', '')
            if hero_name.lower() in hero_name_field.lower():
                target_hero = hero
                logger.info(f"找到匹配英雄: {hero_name_field} (ID: {hero.get('yzzyxi_2602', '未知')})")
                break
        
        if not target_hero:
            # 如果没有完全匹配，尝试模糊匹配
            for hero in heroes:
                hero_name_field = hero.get('yzzyxm_4588', '')
                if any(keyword in hero_name_field.lower() for keyword in hero_name.lower().split()):
                    target_hero = hero
                    logger.info(f"模糊匹配到英雄: {hero_name_field} (ID: {hero.get('yzzyxi_2602', '未知')})")
                    break
        
        return target_hero
    
    def extract_voice_urls(self, voice_data):
        """从语音数据中提取语音文件URL"""
        voice_urls = []
        
        # 语音数据格式: dqpfyy_5403 是一个数组，每个元素包含皮肤信息和语音列表
        for skin_data in voice_data:
            # 皮肤名称
            skin_name = skin_data.get('pfmczt_7754', '默认皮肤')
            
            # 语音列表存储在 yylbzt_9132 字段中
            voice_list = skin_data.get('yylbzt_9132', [])
            
            for voice_item in voice_list:
                # 语音文本
                voice_text = voice_item.get('yywbzt_1517', '未知台词')
                # 语音文件URL（需要添加https://协议）
                voice_url = voice_item.get('yywjzt_5304', '')
                # 语音功能/类型
                voice_function = voice_item.get('yygn_8632', '未知功能')
                
                if voice_url and (voice_url.endswith('.wav') or voice_url.endswith('.mp3')):
                    # 为URL添加https://协议前缀
                    if voice_url.startswith('//'):
                        voice_url = 'https:' + voice_url
                    
                    voice_urls.append({
                        'url': voice_url,
                        'text': voice_text,
                        'function': voice_function,
                        'skin': skin_name
                    })
        
        logger.info(f"提取到 {len(voice_urls)} 个语音文件")
        return voice_urls
    
    def download_voice_file(self, voice_info, output_dir="voices"):
        """下载单个语音文件"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        url = voice_info['url']
        skin_name = voice_info['skin']
        function = voice_info['function']
        text = voice_info['text']
        
        # 清理文件名中的非法字符
        safe_skin_name = re.sub(r'[<>:"/\\|?*]', '_', skin_name)
        safe_function = re.sub(r'[<>:"/\\|?*]', '_', function)
        safe_text = re.sub(r'[<>:"/\\|?*]', '_', text)[:50]  # 限制文件名长度
        
        # 生成文件名
        filename = f"{safe_skin_name}_{safe_function}_{safe_text}_{int(time.time())}.mp3"
        filepath = os.path.join(output_dir, filename)
        
        try:
            logger.info(f"下载语音文件: {skin_name} - {function} - {text}")
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"语音文件保存成功: {filepath}")
            return filepath
        except requests.RequestException as e:
            logger.error(f"下载语音文件失败: {e}")
            return None
    
    def download_hero_voices(self, hero_name, output_dir="voices"):
        """下载指定英雄的所有语音包"""
        logger.info(f"开始下载英雄 '{hero_name}' 的语音包")
        
        # 获取英雄列表
        heroes = self.get_hero_list()
        if not heroes:
            logger.error("无法获取英雄列表")
            return False
        
        # 搜索指定英雄
        target_hero = self.search_hero_by_name(hero_name, heroes)
        if not target_hero:
            logger.error(f"未找到英雄 '{hero_name}'")
            # 显示可用英雄列表
            available_heroes = [hero.get('yzzyxm_4588', '未知') for hero in heroes[:20]]  # 只显示前20个
            logger.info(f"可用英雄: {available_heroes}")
            return False
        
        hero_id = target_hero.get('yzzyxi_2602', '')
        hero_name_field = target_hero.get('yzzyxm_4588', '未知英雄')
        
        logger.info(f"开始处理英雄: {hero_name_field} (ID: {hero_id})")
        
        # 获取语音数据
        voice_data = self.get_hero_voices(hero_id)
        if not voice_data:
            logger.error(f"无法获取英雄 {hero_name_field} 的语音数据")
            return False
        
        # 提取语音URL
        voice_urls = self.extract_voice_urls(voice_data)
        if not voice_urls:
            logger.warning(f"英雄 {hero_name_field} 没有可用的语音文件")
            return False
        
        # 创建英雄专属目录
        hero_dir = os.path.join(output_dir, f"{hero_name_field}_{hero_id}")
        if not os.path.exists(hero_dir):
            os.makedirs(hero_dir)
        
        # 下载所有语音文件
        success_count = 0
        for i, voice_info in enumerate(voice_urls):
            logger.info(f"下载进度: {i+1}/{len(voice_urls)}")
            
            result = self.download_voice_file(voice_info, hero_dir)
            if result:
                success_count += 1
            
            # 添加延迟避免请求过快
            time.sleep(0.5)
        
        logger.info(f"下载完成: {success_count}/{len(voice_urls)} 个文件成功下载到目录 {hero_dir}")
        return True
    
    def interactive_mode(self):
        """交互式模式"""
        print("=== 王者荣耀英雄语音包下载器 ===")
        print("请输入英雄名称（如：李白、妲己、孙悟空等）：")
        
        hero_name = input("英雄名称: ").strip()
        if not hero_name:
            print("请输入有效的英雄名称")
            return
        
        print(f"\n开始下载英雄 '{hero_name}' 的语音包...")
        
        success = self.download_hero_voices(hero_name)
        if success:
            print(f"\n✓ 英雄 '{hero_name}' 的语音包下载完成！")
            print("语音文件保存在 'voices' 目录中")
        else:
            print(f"\n✗ 下载失败，请检查英雄名称是否正确")

def main():
    """主函数"""
    downloader = HonorOfKingsVoiceDownloader()
    
    # 测试连接和功能
    print("正在初始化王者荣耀语音包下载器...")
    
    # 获取英雄列表测试
    heroes = downloader.get_hero_list()
    if heroes:
        print(f"成功连接到王者荣耀API，发现 {len(heroes)} 个英雄")
        
        # 显示前10个英雄
        print("\n前10个英雄:")
        for i, hero in enumerate(heroes[:10]):
            hero_name = hero.get('yzzyxm_4588', '未知')
            hero_id = hero.get('yzzyxi_2602', '未知')
            hero_title = hero.get('yzzyxc_4613', '未知')
            print(f"  {i+1}. {hero_name} ({hero_title}) - ID: {hero_id}")
        
        # 启动交互模式
        downloader.interactive_mode()
    else:
        print("无法连接到王者荣耀API，请检查网络连接")

if __name__ == "__main__":
    main()