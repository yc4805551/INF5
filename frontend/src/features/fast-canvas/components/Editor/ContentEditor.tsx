import React, { useRef, useState, useCallback } from 'react';
import { BlockRenderer } from './BlockRenderer';
import { FormattingBar, FormatAction } from './FormattingBar';
import { ContentBlock, BlockType } from '../../types';
import './ContentEditor.css';

interface ContentEditorProps {
    blocks: ContentBlock[];
    onUpdateBlock: (blockId: string, text: string) => void;
    onAddBlock: (afterBlockId?: string, type?: BlockType) => void;
    onDeleteBlock: (blockId: string) => void;
    onUpdateBlockStyle: (blockId: string, updates: Partial<ContentBlock>) => void;
}

export const ContentEditor: React.FC<ContentEditorProps> = ({
    blocks,
    onUpdateBlock,
    onAddBlock,
    onDeleteBlock,
    onUpdateBlockStyle
}) => {
    const editorRef = useRef<HTMLDivElement>(null);
    const [focusedBlockId, setFocusedBlockId] = useState<string | null>(null);

    // 处理键盘事件
    const handleKeyDown = useCallback((e: React.KeyboardEvent, blockId: string) => {
        // Enter: 创建新段落
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            const currentBlock = blocks.find(b => b.id === blockId);
            if (currentBlock) {
                // 如果是标题，新建普通段落
                const newType = currentBlock.type.startsWith('heading') ? 'paragraph' : currentBlock.type;
                onAddBlock(blockId, newType);

                // 聚焦到新块
                setTimeout(() => {
                    const newBlockElement = editorRef.current?.querySelector(`[data-block-id="${blockId}"]`)?.nextElementSibling as HTMLElement;
                    newBlockElement?.focus();
                }, 10);
            }
        }

        // Backspace: 删除空块或合并
        if (e.key === 'Backspace') {
            const target = e.currentTarget as HTMLElement;
            if (target.textContent === '') {
                e.preventDefault();
                if (blocks.length > 1) {
                    onDeleteBlock(blockId);
                    // 聚焦到上一个块
                    const currentIndex = blocks.findIndex(b => b.id === blockId);
                    if (currentIndex > 0) {
                        setTimeout(() => {
                            const prevBlock = editorRef.current?.querySelector(`[data-block-id="${blocks[currentIndex - 1].id}"]`) as HTMLElement;
                            prevBlock?.focus();
                        }, 10);
                    }
                }
            }
        }

        // Ctrl+B/I/U: 格式化快捷键
        if (e.ctrlKey || e.metaKey) {
            if (e.key === 'b') {
                e.preventDefault();
                handleFormat({ type: 'style', value: 'bold' });
            } else if (e.key === 'i') {
                e.preventDefault();
                handleFormat({ type: 'style', value: 'italic' });
            } else if (e.key === 'u') {
                e.preventDefault();
                handleFormat({ type: 'style', value: 'underline' });
            }
        }
    }, [blocks, onAddBlock, onDeleteBlock]);

    // 处理格式化
    const handleFormat = useCallback((action: FormatAction) => {
        if (!focusedBlockId) return;

        const block = blocks.find(b => b.id === focusedBlockId);
        if (!block) return;

        if (action.type === 'style') {
            const currentValue = block.style?.[action.value];
            onUpdateBlockStyle(focusedBlockId, {
                style: {
                    ...block.style,
                    [action.value]: !currentValue
                }
            });
        } else if (action.type === 'blockType') {
            onUpdateBlockStyle(focusedBlockId, {
                type: action.value
            });
        } else if (action.type === 'align') {
            onUpdateBlockStyle(focusedBlockId, {
                style: {
                    ...block.style,
                    align: action.value
                }
            });
        }
    }, [focusedBlockId, blocks, onUpdateBlockStyle]);

    // 处理焦点
    const handleFocus = (blockId: string) => {
        setFocusedBlockId(blockId);
    };

    return (
        <div className="content-editor-wrapper">
            <FormattingBar onFormat={handleFormat} disabled={!focusedBlockId} />

            <div
                ref={editorRef}
                className="content-editor"
                onClick={() => {
                    // 点击空白处聚焦到最后一个块
                    if (blocks.length > 0) {
                        const lastBlock = editorRef.current?.querySelector(`[data-block-id="${blocks[blocks.length - 1].id}"]`) as HTMLElement;
                        lastBlock?.focus();
                    }
                }}
            >
                {blocks.map(block => (
                    <div
                        key={block.id}
                        onFocus={() => handleFocus(block.id)}
                    >
                        <BlockRenderer
                            block={block}
                            isEditing={true}
                            onUpdate={onUpdateBlock}
                            onKeyDown={handleKeyDown}
                        />
                    </div>
                ))}

                {blocks.length === 0 && (
                    <div className="editor-placeholder">
                        开始输入...
                    </div>
                )}
            </div>
        </div>
    );
};
