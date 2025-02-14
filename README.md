# AI 文档解读助手

一个基于大模型的文档解读工具，可以自动分析文档内容，生成结构化的解读报告。特别适合处理技术文档、产品文档等专业内容。

## 功能特点

- PDF文本提取：自动提取PDF文档中的文本内容
- 分页处理：按页分析，保持文档结构
- 智能解读：对每页内容进行深度分析，包括：
  - 核心概念解释
  - 技术挑战分析
  - 解决方案详解
  - 方案优势总结
  - 最佳实践建议
- 实时进度：显示处理进度和资源使用统计
- 错误处理：支持跳过或中止两种错误处理策略
- 费用统计：自动计算API调用费用

## 安装说明

1. 克隆项目并安装依赖：
```bash
git clone [repository-url]
cd [project-directory]
pip install -r requirements.txt
```

2. 配置设置：
- 复制配置模板创建配置文件：
```bash
cp config.template.json config.json
```
- 编辑 `config.json`，填入你的API配置信息

## 使用方法

### 1. 提取PDF文本

```bash
python extract_pdf.py input.pdf [output.txt]
```
- `input.pdf`: 输入的PDF文件
- `output.txt`: 可选，输出的文本文件（默认与PDF同名，扩展名为.txt）

### 2. 生成解读报告

```bash
python generate_notes.py input.txt [options]
```

可选参数：
- `--config`: 配置文件路径（默认：config.json）
- `--topic`: 文档主题（默认：技术综述）
- `--error-strategy`: 错误处理策略（skip/abort，默认：skip）
- `--log-level`: 日志级别（debug/info，默认：info）
- `--save-stats`: 保存统计信息到指定JSON文件

### 示例

```bash
# 1. 提取PDF文本
python extract_pdf.py docs/product.pdf

# 2. 生成解读报告
python generate_notes.py docs/product.txt --topic "产品介绍" --log-level debug
```

## 配置说明

`config.json` 主要配置项：
```json
{
    "api_base": "API端点URL",
    "api_key": "你的API密钥",
    "model": "使用的模型ID",
    "max_tokens": 4096,
    "context_window": 32768,
    "temperature": 0.7,
    "price_per_1m_tokens": 4.0,
    "log_level": "info"
}
```

## 输出格式

生成的解读报告采用Markdown格式，包含以下结构：
```markdown
# Page 1

## 原文
[原文内容]

## 内容解读
### 概念解释
[关键概念解释]

### 技术挑战
[技术挑战分析]

### 解决方案
[解决方案详解]

### 方案优势
[方案优势总结]

### 最佳实践
[最佳实践建议]
```

## 注意事项

1. 请确保配置文件中包含正确的API认证信息
2. 大文件处理可能产生较高的API调用费用
3. 建议先使用小文件测试配置是否正确
4. 默认情况下错误处理策略为skip，会跳过处理失败的页面
5. 使用debug日志级别可以查看详细的API调用信息

## License

MIT License