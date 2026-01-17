import { useState, useCallback, useEffect } from 'react';
import { FastDocument, ContentBlock, BlockType } from '../types';
import { v4 as uuidv4 } from 'uuid';

/**
 * 快速画布核心Hook
 */
export const useFastCanvas = () => {
    const [document, setDocument] = useState<FastDocument | null>(null);
    const [isDirty, setIsDirty] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    // 创建新文档
    const createDocument = useCallback((title: string = '无标题文档') => {
        const newDoc: FastDocument = {
            id: uuidv4(),
            title,
            created: Date.now(),
            updated: Date.now(),
            content: [
                {
                    id: uuidv4(),
                    type: 'paragraph',
                    text: '',
                    order: 0
                }
            ],
            metadata: {
                wordCount: 0,
                characterCount: 0,
                version: 1
            }
        };
        setDocument(newDoc);
        setIsDirty(false);
        return newDoc;
    }, []);

    // 更新内容块
    const updateBlock = useCallback((blockId: string, updates: Partial<ContentBlock>) => {
        setDocument(prev => {
            if (!prev) return null;

            const updatedContent = prev.content.map(block =>
                block.id === blockId ? { ...block, ...updates } : block
            );

            // 重新计算元数据
            const allText = updatedContent.map(b => b.text).join('');
            const metadata = {
                ...prev.metadata,
                wordCount: allText.split(/\s+/).filter(Boolean).length,
                characterCount: allText.length,
                version: prev.metadata.version + 1
            };

            return {
                ...prev,
                content: updatedContent,
                updated: Date.now(),
                metadata
            };
        });
        setIsDirty(true);
    }, []);

    // 添加新块
    const addBlock = useCallback((afterBlockId?: string, type: BlockType = 'paragraph') => {
        setDocument(prev => {
            if (!prev) return null;

            const newBlock: ContentBlock = {
                id: uuidv4(),
                type,
                text: '',
                order: prev.content.length
            };

            let updatedContent: ContentBlock[];
            if (afterBlockId) {
                const index = prev.content.findIndex(b => b.id === afterBlockId);
                updatedContent = [
                    ...prev.content.slice(0, index + 1),
                    newBlock,
                    ...prev.content.slice(index + 1)
                ];
            } else {
                updatedContent = [...prev.content, newBlock];
            }

            // 重新排序
            updatedContent = updatedContent.map((block, idx) => ({
                ...block,
                order: idx
            }));

            return {
                ...prev,
                content: updatedContent,
                updated: Date.now()
            };
        });
        setIsDirty(true);
    }, []);

    // 删除块
    const deleteBlock = useCallback((blockId: string) => {
        setDocument(prev => {
            if (!prev || prev.content.length <= 1) return prev; // 至少保留一个块

            const updatedContent = prev.content
                .filter(b => b.id !== blockId)
                .map((block, idx) => ({ ...block, order: idx }));

            return {
                ...prev,
                content: updatedContent,
                updated: Date.now()
            };
        });
        setIsDirty(true);
    }, []);

    // 保存文档
    const saveDocument = useCallback(async () => {
        if (!document || !isDirty) return;

        setIsSaving(true);
        try {
            // 保存到LocalStorage
            localStorage.setItem(`fast-canvas-doc-${document.id}`, JSON.stringify(document));

            // TODO: 后端备份
            // await fetch('/api/fast-canvas/save', {
            //   method: 'POST',
            //   body: JSON.stringify(document)
            // });

            setIsDirty(false);
        } catch (error) {
            console.error('Failed to save document:', error);
        } finally {
            setIsSaving(false);
        }
    }, [document, isDirty]);

    // 自动保存
    useEffect(() => {
        if (!isDirty) return;

        const timer = setTimeout(() => {
            saveDocument();
        }, 2000); // 2秒后自动保存

        return () => clearTimeout(timer);
    }, [isDirty, saveDocument]);

    // 加载文档
    const loadDocument = useCallback((docId: string) => {
        const saved = localStorage.getItem(`fast-canvas-doc-${docId}`);
        if (saved) {
            const doc = JSON.parse(saved) as FastDocument;
            setDocument(doc);
            setIsDirty(false);
        }
    }, []);

    // 导出为纯文本
    const exportText = useCallback(() => {
        if (!document) return '';
        return document.content.map(block => block.text).join('\n\n');
    }, [document]);

    return {
        document,
        isDirty,
        isSaving,
        createDocument,
        loadDocument,
        updateBlock,
        addBlock,
        deleteBlock,
        saveDocument,
        exportText
    };
};
