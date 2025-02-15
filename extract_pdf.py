import argparse
import os
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from typing import List, Dict
import tempfile
import numpy

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    使用PaddleOCR从PDF文件中提取文本
    """
    try:
        # 初始化PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
        
        # 将PDF转换为图片
        print("正在将PDF转换为图片...")
        images = convert_from_path(pdf_path)
        
        # 存储提取的文本
        extracted_text = ""
        
        # 逐页处理
        for i, image in enumerate(images, 1):
            print(f"正在处理第 {i}/{len(images)} 页...")
            
            # 使用OCR识别文本
            result = ocr.ocr(numpy.array(image))
            
            if result[0]:
                # 提取当前页面的文本
                page_text = process_ocr_result(result[0])
                
                # 只有当文本非空时才添加页面
                if page_text.strip():
                    extracted_text += f"### Page {i}\n\n"
                    extracted_text += page_text + "\n\n"
        
        return extracted_text.strip()
            
    except Exception as e:
        print(f"处理PDF时发生错误: {str(e)}")
        return None

def process_ocr_result(result: List[Dict]) -> str:
    """
    处理OCR识别结果，将其转换为格式化文本
    """
    # 按照y坐标排序，确保文本按照从上到下的顺序
    sorted_text = sorted(result, key=lambda x: x[0][0][1])  # 根据第一个点的y坐标排序
    
    # 提取文本并合并
    text_lines = []
    current_line = []
    current_y = None
    y_threshold = 10  # y坐标差异阈值，用于判断是否为同一行
    
    for box in sorted_text:
        text = box[1][0]  # 获取识别的文本
        y_coord = box[0][0][1]  # 获取文本框的y坐标
        
        if current_y is None:
            current_y = y_coord
            current_line.append(text)
        else:
            # 如果y坐标相近，认为是同一行
            if abs(y_coord - current_y) <= y_threshold:
                current_line.append(text)
            else:
                # 开始新的一行
                text_lines.append(' '.join(current_line))
                current_line = [text]
                current_y = y_coord
    
    # 添加最后一行
    if current_line:
        text_lines.append(' '.join(current_line))
    
    return '\n\n'.join(text_lines)

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
        
        if text:
            # 保存文本
            print(f"正在保存文本到: {args.output_path}")
            with open(args.output_path, 'w', encoding='utf-8') as f:
                f.write(text)
                
            print("处理完成！")
        else:
            print("无法提取文本，请检查PDF文件是否有效。")
            exit(1)
        
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main() 