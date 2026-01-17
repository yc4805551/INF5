import React from 'react';
import { ContentBlock } from '../types';
import './BlockRenderer.css';

interface BlockRendererProps {
    block: ContentBlock;
    isEditing: boolean;
    onUpdate: (blockId: string, text: string) => void;
    onKeyDown?: (e: React.KeyboardEvent, blockId: string) => void;
}

export const BlockRenderer: React.FC<BlockRendererProps> = ({
    block,
    isEditing,
    onUpdate,
    onKeyDown
}) => {
    const handleInput = (e: React.FormEvent<HTMLDivElement>) => {
        const text = e.currentTarget.textContent || '';
        onUpdate(block.id, text);
    };

    const getClassName = () => {
        const classes = ['content-block', `block-${block.type}`];
        if (block.style?.bold) classes.push('bold');
        if (block.style?.italic) classes.push('italic');
        if (block.style?.underline) classes.push('underline');
        if (block.style?.align) classes.push(`align-${block.style.align}`);
        return classes.join(' ');
    };

    const getTag = () => {
        switch (block.type) {
            case 'heading1': return 'h1';
            case 'heading2': return 'h2';
            case 'heading3': return 'h3';
            case 'quote': return 'blockquote';
            case 'list': return 'li';
            default: return 'p';
        }
    };

    const Tag = getTag() as keyof JSX.IntrinsicElements;

    return (
        <Tag
            className={getClassName()}
            contentEditable={isEditing}
            suppressContentEditableWarning
            onInput={handleInput}
            onKeyDown={(e) => onKeyDown?.(e, block.id)}
            data-block-id={block.id}
        >
            {block.text}
        </Tag>
    );
};
