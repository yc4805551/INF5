import { useState } from 'react';
import type { PreviewItem } from './types';

interface PreviewPaneProps {
    paragraphs: PreviewItem[];
    onSelectionEdit?: (selectedText: string, paragraphIds: number[]) => void;
}

export const PreviewPane: React.FC<PreviewPaneProps> = ({ paragraphs, onSelectionEdit }) => {
    const [selection, setSelection] = useState<{ text: string; ids: number[]; x: number; y: number } | null>(null);

    const handleMouseUp = () => {
        const winSelection = window.getSelection();
        if (!winSelection || winSelection.isCollapsed) {
            setSelection(null);
            return;
        }

        const text = winSelection.toString();
        if (!text.trim()) return;

        // Find all paragraph IDs in the selection
        const range = winSelection.getRangeAt(0);
        const container = range.commonAncestorContainer;

        // Helper to find parent with data-paragraph-id
        const findParagraphId = (node: Node | null): number | null => {
            let curr = node;
            while (curr) {
                if (curr instanceof HTMLElement && curr.dataset.paragraphId) {
                    return parseInt(curr.dataset.paragraphId);
                }
                curr = curr.parentNode;
            }
            return null;
        };

        const ids = new Set<number>();

        // If selection is within one node
        const startId = findParagraphId(range.startContainer);
        if (startId !== null) ids.add(startId);

        const endId = findParagraphId(range.endContainer);
        if (endId !== null) ids.add(endId);

        // If selection spans multiple nodes, we might need a more robust traversal
        // For now, let's assume we captured the start and end. 
        // If start and end are different, we should technically fill in the middle.
        if (startId !== null && endId !== null && startId !== endId) {
            for (let i = Math.min(startId, endId); i <= Math.max(startId, endId); i++) {
                ids.add(i);
            }
        }

        if (ids.size > 0) {
            const rect = range.getBoundingClientRect();
            setSelection({
                text,
                ids: Array.from(ids),
                x: rect.left + (rect.width / 2),
                y: rect.top - 10 // Position above
            });
        }
    };

    const handleEditClick = () => {
        if (selection && onSelectionEdit) {
            onSelectionEdit(selection.text, selection.ids);
            setSelection(null);
            window.getSelection()?.removeAllRanges();
        }
    };

    return (
        <div className="preview-scroll-container" onMouseUp={handleMouseUp}>
            {selection && (
                <div
                    className="selection-popup"
                    style={{ left: selection.x, top: selection.y }}
                >
                    <button
                        onClick={handleEditClick}
                        className="ai-edit-btn"
                    >
                        <span style={{ fontSize: '16px' }}>✨</span>
                        AI Edit
                    </button>
                </div>
            )}
            <div className={`document-page ${paragraphs.length === 0 ? 'empty' : ''}`}>
                {paragraphs.length === 0 ? (
                    <div className="document-empty">
                        <p style={{ fontSize: '18px', fontWeight: 500, marginBottom: '8px' }}>No document loaded</p>
                        <p style={{ fontSize: '14px' }}>Upload a .docx file to see the preview here.</p>
                    </div>
                ) : (
                    (paragraphs || []).map((p) => (
                        <div
                            key={p.id}
                            data-paragraph-id={p.id}
                            style={{
                                marginBottom: '16px',
                                lineHeight: '1.6',
                                fontSize: p.style === 'Heading 1' ? '32px' :
                                    p.style === 'Heading 2' ? '24px' :
                                        p.style === 'Heading 3' ? '20px' : '16px',
                                fontWeight: p.style?.startsWith('Heading') ? 'bold' : 'normal',
                                color: p.style?.startsWith('Heading') ? '#111' : '#333'
                            }}
                        >
                            {p.runs ? (
                                p.runs.map((run, idx) => (
                                    <span
                                        key={idx}
                                        style={{
                                            fontWeight: run.bold ? 'bold' : 'normal',
                                            fontStyle: run.italic ? 'italic' : 'normal',
                                            textDecoration: run.underline ? 'underline' : 'none',
                                            color: run.color || 'inherit',
                                            fontSize: run.fontSize ? `${run.fontSize}pt` : 'inherit'
                                        }}
                                    >
                                        {run.text}
                                    </span>
                                ))
                            ) : (
                                // Fallback if no runs data
                                <span>{p.text}</span>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};
