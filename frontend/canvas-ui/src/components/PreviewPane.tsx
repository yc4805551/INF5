import { useState } from 'react';
import type { PreviewItem } from '../types';

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
        <div className="h-full overflow-y-auto p-8 bg-gray-100 relative" onMouseUp={handleMouseUp}>
            {selection && (
                <div 
                    className="fixed z-50 transform -translate-x-1/2 -translate-y-full mb-2"
                    style={{ left: selection.x, top: selection.y }}
                >
                    <button 
                        onClick={handleEditClick}
                        className="bg-blue-600 text-white px-3 py-1.5 rounded-full shadow-lg text-sm font-medium flex items-center gap-2 hover:bg-blue-700 transition-colors animate-in fade-in zoom-in duration-200"
                    >
                        <span className="w-4 h-4">✨</span>
                        AI Edit
                    </button>
                </div>
            )}
            <div className="max-w-[850px] mx-auto bg-white min-h-[1100px] p-[96px] shadow-lg transition-all duration-300 ease-in-out ring-1 ring-gray-900/5">
                {paragraphs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-400 mt-40">
                        <p className="text-lg font-medium">No document loaded</p>
                        <p className="text-sm mt-2">Upload a .docx file to see the preview here.</p>
                    </div>
                ) : (
                    (paragraphs || []).map((p) => (
                        <div
                            key={p.id}
                            data-paragraph-id={p.id}
                            className={`mb-4 leading-relaxed ${p.style === 'Heading 1' ? 'text-4xl font-bold mb-6 text-gray-900' :
                                p.style === 'Heading 2' ? 'text-2xl font-bold mb-4 text-gray-800' :
                                    p.style === 'Heading 3' ? 'text-xl font-bold mb-3 text-gray-800' :
                                        'text-base text-gray-900'
                                }`}
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
