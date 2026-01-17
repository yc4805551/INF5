"""
Canvas Converter: Tiptap JSON ↔ DOCX 双向转换
为快速画布和专业画布提供无缝数据互通
"""
import io
import logging
from typing import Dict, Any, List
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

logger = logging.getLogger(__name__)

def tiptap_to_docx(json_content: Dict[str, Any]) -> io.BytesIO:
    """
    将Tiptap JSON转换为DOCX文件流
    
    支持的节点类型:
    - paragraph (段落)
    - heading (标题 level 1-6)
    - bulletList / listItem (无序列表)
    - orderedList / listItem (有序列表)
    - hardBreak (换行)
    
    支持的标记:
    - bold (粗体)
    - italic (斜体)
    - underline (下划线)
    - strike (删除线)
    """
    doc = Document()
    
    # 处理content数组
    content = json_content.get('content', [])
    
    for block in content:
        block_type = block.get('type')
        
        if block_type == 'paragraph':
            _process_paragraph(doc, block)
        
        elif block_type == 'heading':
            level = block.get('attrs', {}).get('level', 1)
            text_content = _extract_text(block)
            doc.add_heading(text_content, level=min(level, 3))
        
        elif block_type == 'bulletList':
            _process_list(doc, block, ordered=False)
        
        elif block_type == 'orderedList':
            _process_list(doc, block, ordered=True)
    
    # 返回BytesIO
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def _process_paragraph(doc: Document, block: Dict):
    """处理段落节点，应用文本标记"""
    para = doc.add_paragraph()
    content = block.get('content', [])
    
    for item in content:
        if item.get('type') == 'text':
            text = item.get('text', '')
            run = para.add_run(text)
            
            # 应用标记
            marks = item.get('marks', [])
            for mark in marks:
                mark_type = mark.get('type')
                if mark_type == 'bold':
                    run.bold = True
                elif mark_type == 'italic':
                    run.italic = True
                elif mark_type == 'underline':
                    run.underline = True
                elif mark_type == 'strike':
                    run.font.strike = True
        
        elif item.get('type') == 'hardBreak':
            para.add_run('\n')

def _process_list(doc: Document, block: Dict, ordered: bool = False):
    """处理列表节点"""
    content = block.get('content', [])
    
    for idx, item in enumerate(content):
        if item.get('type') == 'listItem':
            text_content = _extract_text(item)
            prefix = f"{idx + 1}. " if ordered else "• "
            doc.add_paragraph(prefix + text_content)

def _extract_text(block: Dict) -> str:
    """递归提取文本内容"""
    content = block.get('content', [])
    text_parts = []
    
    for item in content:
        if item.get('type') == 'text':
            text_parts.append(item.get('text', ''))
        elif 'content' in item:
            text_parts.append(_extract_text(item))
    
    return ''.join(text_parts)

# ==================== DOCX → Tiptap JSON ====================

def docx_to_tiptap(file_stream: io.BytesIO) -> Dict[str, Any]:
    """
    将DOCX转换为Tiptap JSON格式
    
    返回格式:
    {
        "type": "doc",
        "content": [...]
    }
    """
    doc = Document(file_stream)
    content = []
    
    for para in doc.paragraphs:
        # 检测标题
        if para.style.name.startswith('Heading'):
            try:
                level = int(para.style.name[-1])
                content.append({
                    "type": "heading",
                    "attrs": {"level": level},
                    "content": [{"type": "text", "text": para.text}]
                })
            except ValueError:
                # 无法解析标题级别，按段落处理
                content.append(_para_to_tiptap(para))
        else:
            content.append(_para_to_tiptap(para))
    
    return {
        "type": "doc",
        "content": content
    }

def _para_to_tiptap(para) -> Dict:
    """将DOCX段落转换为Tiptap段落节点"""
    text_content = []
    
    for run in para.runs:
        text_node = {"type": "text", "text": run.text}
        
        # 提取marks
        marks = []
        if run.bold:
            marks.append({"type": "bold"})
        if run.italic:
            marks.append({"type": "italic"})
        if run.underline:
            marks.append({"type": "underline"})
        if run.font.strike:
            marks.append({"type": "strike"})
        
        if marks:
            text_node["marks"] = marks
        
        text_content.append(text_node)
    
    return {
        "type": "paragraph",
        "content": text_content if text_content else [{"type": "text", "text": ""}]
    }
