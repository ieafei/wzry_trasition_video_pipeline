#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆包API图片过渡描述词生成脚本
用于调用豆包API，传入两张图片作为首尾帧，生成一段描述词
"""

import requests
import json
import base64
import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DoubaoImageToText:
    """豆包API图片转描述词生成器"""
    
    def __init__(self, api_key: str = None, base_url: str = "https://api.doubao.com"):
        """
        初始化豆包API客户端
        
        Args:
            api_key: 豆包API密钥，如果为None则从环境变量读取
            base_url: API基础URL
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.getenv('DOUBAO_API_KEY')
        
        if not self.api_key:
            logger.warning("未设置豆包API密钥，请设置DOUBAO_API_KEY环境变量或传入api_key参数")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json',
        })
    
    def encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """
        将图片文件编码为base64字符串
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            base64编码的图片字符串，失败返回None
        """
        try:
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                base64_encoded = base64.b64encode(image_data).decode('utf-8')
                
                # 获取文件扩展名
                file_extension = Path(image_path).suffix.lower()
                mime_type = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp',
                    '.webp': 'image/webp'
                }.get(file_extension, 'image/jpeg')
                
                return f"data:{mime_type};base64,{base64_encoded}"
        except Exception as e:
            logger.error(f"图片编码失败: {e}")
            return None
    
    def generate_transition_description(self, start_image_path: str, end_image_path: str, 
                                       prompt: str = "根据这两张图片的过渡变化，生成一段描述词",
                                       max_tokens: int = 500) -> Optional[str]:
        """
        生成两张图片之间的过渡描述词
        
        Args:
            start_image_path: 起始图片路径
            end_image_path: 结束图片路径
            prompt: 生成提示词
            max_tokens: 最大生成token数
            
        Returns:
            生成的描述词文本，失败返回None
        """
        if not self.api_key:
            logger.error("未设置豆包API密钥")
            return None
        
        # 检查图片文件是否存在
        if not os.path.exists(start_image_path):
            logger.error(f"起始图片不存在: {start_image_path}")
            return None
        
        if not os.path.exists(end_image_path):
            logger.error(f"结束图片不存在: {end_image_path}")
            return None
        
        # 编码图片为base64
        logger.info("正在编码图片...")
        start_image_base64 = self.encode_image_to_base64(start_image_path)
        end_image_base64 = self.encode_image_to_base64(end_image_path)
        
        if not start_image_base64 or not end_image_base64:
            logger.error("图片编码失败")
            return None
        
        # 构建API请求数据
        request_data = {
            "model": "doubao-vision",  # 假设的视觉模型名称，请根据实际API调整
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": start_image_base64
                            }
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": end_image_base64
                            }
                        }
                    ]
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        # 添加API密钥到请求头
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.info("正在调用豆包API生成描述词...")
            
            # 注意：实际API端点可能需要调整
            api_url = f"{self.base_url}/v1/chat/completions"
            
            response = self.session.post(api_url, headers=headers, 
                                        json=request_data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            # 提取生成的文本
            if "choices" in result and len(result["choices"]) > 0:
                description = result["choices"][0]["message"]["content"]
                logger.info("描述词生成成功")
                return description.strip()
            else:
                logger.error("API响应格式异常")
                return None
                
        except requests.RequestException as e:
            logger.error(f"API调用失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"响应状态码: {e.response.status_code}")
                logger.error(f"响应内容: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"处理API响应时发生错误: {e}")
            return None
    
    def save_description_to_file(self, description: str, output_path: str = "transition_description.txt"):
        """
        将生成的描述词保存到文件
        
        Args:
            description: 描述词文本
            output_path: 输出文件路径
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(description)
            
            logger.info(f"描述词已保存到: {output_path}")
        except Exception as e:
            logger.error(f"保存描述词失败: {e}")
    
    def batch_process(self, image_pairs: list, output_dir: str = "descriptions"):
        """
        批量处理多对图片
        
        Args:
            image_pairs: 图片对列表，每个元素为(start_image, end_image)元组
            output_dir: 输出目录
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        success_count = 0
        
        for i, (start_img, end_img) in enumerate(image_pairs):
            logger.info(f"处理第 {i+1}/{len(image_pairs)} 对图片...")
            
            description = self.generate_transition_description(start_img, end_img)
            
            if description:
                # 生成输出文件名
                start_name = Path(start_img).stem
                end_name = Path(end_img).stem
                output_file = f"{output_dir}/transition_{start_name}_to_{end_name}.txt"
                
                self.save_description_to_file(description, output_file)
                success_count += 1
            else:
                logger.warning(f"第 {i+1} 对图片处理失败")
            
            # 添加延迟避免请求过快
            time.sleep(1)
        
        logger.info(f"批量处理完成: {success_count}/{len(image_pairs)} 对图片成功")

def main():
    """主函数 - 使用示例"""
    # 初始化豆包API客户端
    # 方式1: 从环境变量读取API密钥
    # export DOUBAO_API_KEY="your_api_key_here"
    
    # 方式2: 直接传入API密钥
    # api_key = "your_api_key_here"
    # generator = DoubaoImageToText(api_key=api_key)
    
    generator = DoubaoImageToText()
    
    # 示例1: 单对图片处理
    print("=== 单对图片过渡描述词生成示例 ===")
    
    # 替换为您的实际图片路径
    start_image = "path/to/your/start_image.jpg"
    end_image = "path/to/your/end_image.jpg"
    
    if os.path.exists(start_image) and os.path.exists(end_image):
        description = generator.generate_transition_description(
            start_image_path=start_image,
            end_image_path=end_image,
            prompt="请根据这两张图片的过渡变化，生成一段生动形象的描述词，描述从第一张图片到第二张图片的变化过程"
        )
        
        if description:
            print("生成的描述词:")
            print("-" * 50)
            print(description)
            print("-" * 50)
            
            # 保存到文件
            generator.save_description_to_file(description, "generated_description.txt")
        else:
            print("描述词生成失败，请检查API密钥和网络连接")
    else:
        print("示例图片不存在，请替换为您的实际图片路径")
    
    # 示例2: 批量处理（需要准备多对图片）
    print("\n=== 批量处理示例 ===")
    
    # 准备图片对列表
    image_pairs = [
        ("image1_start.jpg", "image1_end.jpg"),
        ("image2_start.jpg", "image2_end.jpg"),
        # 添加更多图片对...
    ]
    
    # 过滤掉不存在的图片对
    valid_pairs = []
    for start, end in image_pairs:
        if os.path.exists(start) and os.path.exists(end):
            valid_pairs.append((start, end))
    
    if valid_pairs:
        generator.batch_process(valid_pairs, "batch_descriptions")
    else:
        print("没有找到有效的图片对，请检查图片路径")

if __name__ == "__main__":
    main()