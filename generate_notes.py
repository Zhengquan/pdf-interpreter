import json
import argparse
import os
from typing import List, Dict, Optional
import requests
import tiktoken
from tqdm import tqdm
import time
import sys

class StatsDisplay:
    """统计信息显示管理器"""
    def __init__(self):
        self.stats_lines = 11  # 统计信息的总行数
        self.initialized = False
        self.last_content = ""  # 记录上一次的统计内容
        
    def init_display(self):
        """初始化显示区域"""
        if not self.initialized:
            # 为统计信息预留空间
            print("\n" * (self.stats_lines + 1))  # 多预留一行作为缓冲
            sys.stdout.write(f"\033[{self.stats_lines + 1}A")
            sys.stdout.flush()
            self.initialized = True
    
    def get_cursor_position(self) -> int:
        """获取当前光标位置"""
        import os
        try:
            # 尝试获取终端大小
            rows, _ = os.popen('stty size', 'r').read().split()
            return int(rows)
        except:
            return 0
    
    def update_stats(self, stats: Dict):
        """更新统计信息显示"""
        if not self.initialized:
            self.init_display()
            return
        
        # 格式化统计信息
        stats_text = (
            "="*50 + "\n"
            f"API调用统计:\n"
            f"总调用次数: {stats['api_calls']}次\n\n"
            f"Token消耗统计:\n"
            f"输入Token数: {stats['prompt_tokens']:,}\n"
            f"输出Token数: {stats['completion_tokens']:,}\n"
            f"总Token数: {stats['total_tokens']:,}\n\n"
            f"费用统计: ¥{stats['total_cost']:.4f}\n"
            + "="*50
        )
        
        # 如果内容没有变化，不更新
        if stats_text == self.last_content:
            return
            
        # 保存当前内容
        self.last_content = stats_text
        
        # 移动到统计信息区域起始位置
        sys.stdout.write(f"\033[{self.stats_lines + 1}A")
        
        # 清除并更新统计信息
        lines = stats_text.split('\n')
        for i, line in enumerate(lines):
            sys.stdout.write("\033[2K")  # 清除当前行
            if i < len(lines) - 1:
                print(line)
            else:
                print(line, end='')
        
        # 移动回进度条位置
        sys.stdout.write(f"\033[{self.stats_lines - len(lines) + 1}B")
        sys.stdout.flush()

    def cleanup(self):
        """清理显示"""
        if self.initialized:
            sys.stdout.write(f"\033[{self.stats_lines + 1}A")  # 移动到统计信息开始处
            for _ in range(self.stats_lines + 1):  # 多清理一行
                sys.stdout.write("\033[2K\n")
            sys.stdout.write(f"\033[{self.stats_lines + 2}A")  # 多回退一行
            sys.stdout.flush()

class NotesGenerator:
    def __init__(self, config_path: str):
        """初始化生成器"""
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # 初始化tokenizer，使用cl100k_base编码器
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            print(f"警告: 无法加载tokenizer: {str(e)}")
            # 如果无法加载tokenizer，使用简单的字符计数作为后备方案
            self.tokenizer = None
        
        # 添加用量统计
        self.usage_stats = {
            'total_tokens': 0,
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_cost': 0.0,
            'api_calls': 0,
            'last_update': time.time()
        }
        self.stats_display = StatsDisplay()
        
        # 设置日志级别
        self.log_level = self.config.get('log_level', 'info').lower()

    def count_tokens(self, text: str) -> int:
        """计算文本的token数量"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # 后备方案：使用字符数除以4作为估算（这是一个粗略的估计）
            return len(text) // 4
    
    def create_prompt(self, text: str, topic: str) -> str:
        """创建提示词"""
        return f"""作为一位专业的技术分析专家，请帮助我深入理解以下内容。

主题方向：{topic}

源内容：
{text}

请按照以下结构进行内容分析和总结， 需避免单纯的列表罗列：

### 概念解释
请提取并解释文中最关键的2-3个技术概念或术语，确保解释准确且易于理解。每个概念解释应包含：

### 技术挑战
分析文中描述的主要技术挑战，以及传统解决方案的局限性

### 解决方案
详细分析文中提出的解决方案：
- 核心技术架构
- 关键实现方法

### 方案优势
系统总结该方案的优势

### 最佳实践
总结相关领域的实践经验

要求：
- 分析要准确、客观，避免主观臆测
- 重点突出技术本质和创新点
- 保持专业性的同时确保表述清晰
- 适当补充相关领域的专业见解
- 每个部分都需要完整的语段阐述，而不是简单列举

请基于文本内容进行分析，如有不足之处，可以基于专业知识适当补充，但要明确区分原文信息和补充信息。
"""

    def chunk_text(self, text: str) -> List[str]:
        """将文本分块，确保每块不超过上下文窗口大小"""
        pages = text.split("-------\n")
        chunks = []
        current_chunk = ""
        
        for page in pages:
            if not page.strip():
                continue
                
            # 计算当前chunk加上新页面的token数
            potential_chunk = current_chunk + page
            if self.count_tokens(potential_chunk) < self.config['context_window'] - 1000:
                current_chunk = potential_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = page
        
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    def log_debug(self, message: str):
        """输出调试信息"""
        if self.log_level == 'debug':
            tqdm.write(message)

    def call_llm_api(self, prompt: str) -> str:
        """调用大模型API"""
        headers = {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.config['model'],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config['temperature'],
            "max_tokens": self.config['max_tokens']
        }
        
        try:
            # 打印请求信息
            self.log_debug(f"\nAPI请求信息:")
            self.log_debug(f"URL: {self.config['api_base']}/chat/completions")
            self.log_debug(f"模型: {self.config['model']}")
            self.log_debug(f"输入Token数: {self.count_tokens(prompt)}")
            
            # 记录请求开始时间
            start_time = time.time()
            
            response = requests.post(
                f"{self.config['api_base']}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            
            # 计算请求耗时
            elapsed_time = time.time() - start_time
            self.log_debug(f"请求耗时: {elapsed_time:.2f}秒")
            
            if response.status_code == 200:
                response_data = response.json()
                # 更新用量统计
                usage = response_data.get('usage', {})
                self.usage_stats['prompt_tokens'] += usage.get('prompt_tokens', 0)
                self.usage_stats['completion_tokens'] += usage.get('completion_tokens', 0)
                self.usage_stats['total_tokens'] += usage.get('total_tokens', 0)
                self.usage_stats['api_calls'] += 1
                
                # 计算费用
                cost = (usage.get('total_tokens', 0) / 1_000_000) * self.config['price_per_1m_tokens']
                self.usage_stats['total_cost'] += cost
                
                # 打印响应信息
                self.log_debug(f"响应状态: 成功")
                self.log_debug(f"输出Token数: {usage.get('completion_tokens', 0)}")
                self.log_debug(f"总Token数: {usage.get('total_tokens', 0)}")
                self.log_debug(f"本次费用: ¥{cost:.4f}\n")
                
                return response_data['choices'][0]['message']['content']
            else:
                # 打印错误响应详情
                error_msg = f"响应状态: 失败 (状态码: {response.status_code})\n错误信息: {response.text}"
                self.log_debug(error_msg)
                raise Exception(f"API调用失败 (状态码: {response.status_code}): {response.text}")
                
        except requests.exceptions.Timeout:
            self.log_debug(f"请求超时 (>60秒)")
            raise Exception("API请求超时")
        except requests.exceptions.RequestException as e:
            self.log_debug(f"请求异常: {str(e)}")
            raise Exception(f"API请求异常: {str(e)}")
        except Exception as e:
            self.log_debug(f"其他错误: {str(e)}")
            raise

    def format_stats(self) -> str:
        """格式化进度条中显示的简要统计信息"""
        return (f"调用: {self.usage_stats['api_calls']}次 | "
                f"Token: {self.usage_stats['total_tokens']:,} | "
                f"费用: ¥{self.usage_stats['total_cost']:.4f}")

    def print_final_stats(self):
        """打印最终的详细统计信息"""
        stats = (
            "\n" + "="*50 + "\n"
            "API调用统计:\n"
            f"总调用次数: {self.usage_stats['api_calls']}次\n\n"
            "Token消耗统计:\n"
            f"输入Token数: {self.usage_stats['prompt_tokens']:,}\n"
            f"输出Token数: {self.usage_stats['completion_tokens']:,}\n"
            f"总Token数: {self.usage_stats['total_tokens']:,}\n\n"
            f"费用统计: ¥{self.usage_stats['total_cost']:.4f}\n"
            + "="*50
        )
        print(stats)

    def update_progress_stats(self, pbar: tqdm) -> None:
        """更新进度条中的统计信息"""
        current_time = time.time()
        if current_time - self.usage_stats['last_update'] >= 1.0:
            pbar.set_postfix_str(self.format_stats(), refresh=True)
            self.usage_stats['last_update'] = current_time

    def process_file(self, input_path: str, topic: str, error_strategy: str = 'skip') -> None:
        """处理输入文件并生成笔记"""
        print(f"正在读取文件: {input_path}")
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        output_path = os.path.splitext(input_path)[0] + '_notes.md'
        pages = text.split('### Page')
        pages = [page.strip() for page in pages[1:] if page.strip()]
        
        print(f"共发现 {len(pages)} 页内容\n")
        
        # 创建或清空输出文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("")
        
        # 创建进度条，添加统计信息
        with tqdm(total=len(pages), desc="生成笔记", unit="页") as pbar:
            for i, page_text in enumerate(pages, 1):
                try:
                    # 生成当前页的笔记
                    page_note = self.process_single_page(i, page_text, topic)
                    
                    # 实时追加到文件
                    with open(output_path, 'a', encoding='utf-8') as f:
                        f.write(page_note)
                    
                    # 更新进度条和统计信息
                    pbar.update(1)
                    self.update_progress_stats(pbar)
                        
                except Exception as e:
                    error_msg = f"处理第 {i} 页时发生错误: {str(e)}"
                    tqdm.write(error_msg)
                    
                    if error_strategy == 'abort':
                        raise Exception(f"由于错误策略设置为'abort'，停止处理。最后错误: {str(e)}")
                    
                    # 记录错误信息到文件
                    with open(output_path, 'a', encoding='utf-8') as f:
                        f.write(f"# Page {i}\n\n")
                        f.write("## 原文\n")
                        f.write(page_text + "\n\n")
                        f.write("## 内容解读\n")
                        f.write(f"生成失败: {str(e)}\n\n")
                    
                    # 更新进度条
                    pbar.update(1)
                    self.update_progress_stats(pbar)

        # 处理完成后打印详细统计信息
        print("\n处理完成！")
        self.print_final_stats()

    def process_single_page(self, page_num: int, page_text: str, topic: str) -> str:
        """处理单个页面并返回格式化的笔记"""
        notes = []
        
        # 添加页码标题（一级标题）
        notes.append(f"# Page {page_num}\n")
        
        # 添加原文部分（二级标题）
        notes.append("## 原文\n")
        notes.append(page_text + "\n\n")
        
        # 生成内容解读部分（二级标题）
        notes.append("## 内容解读\n")
        prompt = self.create_prompt(page_text, topic)
        response = self.call_llm_api(prompt)
        notes.append(response + "\n\n")
        
        return "\n".join(notes)

def main():
    parser = argparse.ArgumentParser(description='生成Presentation Notes')
    parser.add_argument('input_path', help='输入文本文件路径')
    parser.add_argument('--config', default='config.json', help='配置文件路径')
    parser.add_argument('--topic', default='技术综述', help='演讲主题方向')
    parser.add_argument('--error-strategy', 
                       choices=['skip', 'abort'],
                       default='skip',
                       help='错误处理策略：skip(跳过错误页面) 或 abort(遇错停止)')
    parser.add_argument('--save-stats',
                       help='保存统计信息到指定JSON文件')
    parser.add_argument('--log-level',
                       choices=['debug', 'info'],
                       help='日志级别：debug(显示API请求详情) 或 info(只显示基本信息)')
    
    args = parser.parse_args()
    
    try:
        print("初始化生成器...")
        generator = NotesGenerator(args.config)
        
        # 如果命令行指定了日志级别，覆盖配置文件的设置
        if args.log_level:
            generator.log_level = args.log_level.lower()
        
        print(f"开始处理文件，主题: {args.topic}")
        generator.process_file(args.input_path, args.topic, args.error_strategy)
        
        # 如果指定了统计文件，保存统计信息
        if args.save_stats:
            with open(args.save_stats, 'w', encoding='utf-8') as f:
                json.dump(generator.usage_stats, f, indent=2, ensure_ascii=False)
            print(f"\n统计信息已保存到: {args.save_stats}")
        
    except Exception as e:
        print(f"\n处理过程中发生错误: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main() 