import PyPDF2
import argparse
import os

def extract_text_from_pdf(pdf_path):
    """
    从PDF文件中提取文本并按指定格式输出
    """
    try:
        # 打开PDF文件
        with open(pdf_path, 'rb') as file:
            # 创建PDF读取器对象
            pdf_reader = PyPDF2.PdfReader(file)
            
            # 获取PDF总页数
            total_pages = len(pdf_reader.pages)
            
            # 存储提取的文本
            extracted_text = ""
            
            # 逐页提取文本
            for page_num in range(total_pages):
                # 获取当前页面文本
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                # 清理和格式化文本
                cleaned_text = clean_text(text)
                
                # 只有当文本非空时才添加页面
                if cleaned_text.strip():
                    extracted_text += f"### Page {page_num + 1}\n\n"
                    extracted_text += cleaned_text + "\n\n"
            
            return extracted_text.strip()
            
    except Exception as e:
        print(f"处理PDF时发生错误: {str(e)}")
        return None

def clean_text(text: str) -> str:
    """
    清理和格式化文本
    """
    # 分割成行
    lines = text.split('\n')
    
    # 清理每一行
    cleaned_lines = []
    for line in lines:
        # 去除首尾空白
        line = line.strip()
        # 跳过空行
        if not line:
            continue
        # 合并多个空格
        line = ' '.join(line.split())
        cleaned_lines.append(line)
    
    # 重新组合文本，保持段落结构
    cleaned_text = []
    current_paragraph = []
    
    for line in cleaned_lines:
        # 如果行以特殊字符开始，认为是新段落
        if line.startswith(('•', '-', '*', '1.', '2.', '3.')):
            if current_paragraph:
                cleaned_text.append(' '.join(current_paragraph))
                current_paragraph = []
            cleaned_text.append(line)
        else:
            current_paragraph.append(line)
    
    # 添加最后一个段落
    if current_paragraph:
        cleaned_text.append(' '.join(current_paragraph))
    
    return '\n\n'.join(cleaned_text)

def main():
    parser = argparse.ArgumentParser(description='从PDF文件中提取文本')
    parser.add_argument('pdf_path', help='输入PDF文件路径')
    parser.add_argument('output_path', nargs='?', help='输出文本文件路径（可选，默认与PDF同名）')
    
    args = parser.parse_args()
    
    # 如果未指定输出路径，使用默认路径
    if not args.output_path:
        # 获取PDF文件的路径和文件名
        pdf_dir = os.path.dirname(args.pdf_path)
        pdf_name = os.path.splitext(os.path.basename(args.pdf_path))[0]
        # 构造默认输出路径
        args.output_path = os.path.join(pdf_dir, f"{pdf_name}.txt")
    
    try:
        # 读取PDF文件
        print(f"正在读取PDF文件: {args.pdf_path}")
        text = extract_text_from_pdf(args.pdf_path)
        
        # 保存文本
        print(f"正在保存文本到: {args.output_path}")
        with open(args.output_path, 'w', encoding='utf-8') as f:
            f.write(text)
            
        print("处理完成！")
        
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main() 