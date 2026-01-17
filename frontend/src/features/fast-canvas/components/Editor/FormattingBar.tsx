import React from 'react';
import { BlockType } from '../../types';
import {
    Bold,
    Italic,
    Underline,
    Heading1,
    Heading2,
    List,
    AlignLeft,
    AlignCenter,
    AlignRight,
    Quote
} from 'lucide-react';
import './FormattingBar.css';

interface FormattingBarProps {
    onFormat: (action: FormatAction) => void;
    disabled?: boolean;
}

export type FormatAction =
    | { type: 'style'; value: 'bold' | 'italic' | 'underline' }
    | { type: 'blockType'; value: BlockType }
    | { type: 'align'; value: 'left' | 'center' | 'right' };

export const FormattingBar: React.FC<FormattingBarProps> = ({ onFormat, disabled }) => {
    const handleClick = (action: FormatAction) => {
        if (disabled) return;
        onFormat(action);
    };

    return (
        <div className="formatting-bar">
            {/* Text Styles */}
            <div className="format-group">
                <button
                    className="format-btn"
                    onClick={() => handleClick({ type: 'style', value: 'bold' })}
                    title="加粗 (Ctrl+B)"
                    disabled={disabled}
                >
                    <Bold size={16} />
                </button>
                <button
                    className="format-btn"
                    onClick={() => handleClick({ type: 'style', value: 'italic' })}
                    title="斜体 (Ctrl+I)"
                    disabled={disabled}
                >
                    <Italic size={16} />
                </button>
                <button
                    className="format-btn"
                    onClick={() => handleClick({ type: 'style', value: 'underline' })}
                    title="下划线 (Ctrl+U)"
                    disabled={disabled}
                >
                    <Underline size={16} />
                </button>
            </div>

            <div className="format-divider" />

            {/* Block Types */}
            <div className="format-group">
                <button
                    className="format-btn"
                    onClick={() => handleClick({ type: 'blockType', value: 'heading1' })}
                    title="一级标题"
                    disabled={disabled}
                >
                    <Heading1 size={16} />
                </button>
                <button
                    className="format-btn"
                    onClick={() => handleClick({ type: 'blockType', value: 'heading2' })}
                    title="二级标题"
                    disabled={disabled}
                >
                    <Heading2 size={16} />
                </button>
                <button
                    className="format-btn"
                    onClick={() => handleClick({ type: 'blockType', value: 'list' })}
                    title="列表"
                    disabled={disabled}
                >
                    <List size={16} />
                </button>
                <button
                    className="format-btn"
                    onClick={() => handleClick({ type: 'blockType', value: 'quote' })}
                    title="引用"
                    disabled={disabled}
                >
                    <Quote size={16} />
                </button>
            </div>

            <div className="format-divider" />

            {/* Alignment */}
            <div className="format-group">
                <button
                    className="format-btn"
                    onClick={() => handleClick({ type: 'align', value: 'left' })}
                    title="左对齐"
                    disabled={disabled}
                >
                    <AlignLeft size={16} />
                </button>
                <button
                    className="format-btn"
                    onClick={() => handleClick({ type: 'align', value: 'center' })}
                    title="居中"
                    disabled={disabled}
                >
                    <AlignCenter size={16} />
                </button>
                <button
                    className="format-btn"
                    onClick={() => handleClick({ type: 'align', value: 'right' })}
                    title="右对齐"
                    disabled={disabled}
                >
                    <AlignRight size={16} />
                </button>
            </div>
        </div>
    );
};
