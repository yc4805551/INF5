import React, { useEffect, useState } from 'react';
import { Editor } from '@tiptap/react';
import { BubbleMenu } from '@tiptap/react/menus';
import { AISuggestion } from '../../../types';
import { Check, X, Wand2 } from 'lucide-react';
import './SuggestionBubble.css';

interface SuggestionBubbleProps {
    editor: Editor;
    suggestions: AISuggestion[];
    onApply: (suggestion: AISuggestion) => void;
    onDismiss: (id: string) => void;
}

export const SuggestionBubble: React.FC<SuggestionBubbleProps> = ({
    editor,
    suggestions,
    onApply,
    onDismiss
}) => {
    const [activeSuggestion, setActiveSuggestion] = useState<AISuggestion | null>(null);

    // Logic to update active suggestion based on cursor position
    useEffect(() => {
        if (!editor || !suggestions.length) {
            setActiveSuggestion(null);
            return;
        }

        const updateActiveSuggestion = () => {
            const { from, to } = editor.state.selection;
            const doc = editor.state.doc;

            // Optimization: Only check if selection is collapsed (cursor) or small range
            // Search text around cursor or check precise overlaps?
            // Re-running full search is heavy. Ideally we use the positions from AuditExtension.
            // But checking current node text is fast enough for small docs.

            let found: AISuggestion | null = null;

            doc.descendants((node, pos) => {
                if (found) return false;
                if (!node.isText || !node.text) return;

                // If cursor is not potentially in this node, skip
                if (pos + node.nodeSize < from || pos > to) return;

                suggestions.forEach(s => {
                    if (found) return;
                    if (!s.original) return;

                    // Find all occurrences in this node
                    const nodeText = node.text || '';
                    let index = nodeText.indexOf(s.original);
                    while (index !== -1) {
                        const sFrom = pos + index;
                        const sTo = sFrom + s.original.length;

                        // Check overlap with selection
                        if (from >= sFrom && from <= sTo) {
                            found = s;
                        }

                        index = nodeText.indexOf(s.original, index + 1);
                    }
                });
            });

            setActiveSuggestion(found);
        };

        editor.on('selectionUpdate', updateActiveSuggestion);
        editor.on('update', updateActiveSuggestion);

        return () => {
            editor.off('selectionUpdate', updateActiveSuggestion);
            editor.off('update', updateActiveSuggestion);
        };
    }, [editor, suggestions]);

    if (!activeSuggestion) return null;

    return (
        <BubbleMenu
            editor={editor}
            tippyOptions={{ duration: 100, placement: 'bottom-start' }}
            shouldShow={() => !!activeSuggestion}
            className="suggestion-bubble"
        >
            <div className={`bubble-card ${activeSuggestion.type}`}>
                <div className="bubble-header">
                    <span className="bubble-type">
                        {activeSuggestion.type === 'proofread' ? '🔴 纠错' : '🟠 建议'}
                    </span>
                    <span className="bubble-original">{activeSuggestion.original}</span>
                </div>

                <div className="bubble-arrow">⬇️ 改为</div>

                <div className="bubble-suggestion">
                    {activeSuggestion.suggestion}
                </div>

                {activeSuggestion.reason && (
                    <div className="bubble-reason">
                        {activeSuggestion.reason}
                    </div>
                )}

                <div className="bubble-actions">
                    <button
                        className="bubble-btn apply"
                        onClick={() => onApply(activeSuggestion)}
                    >
                        <Check size={14} /> 采纳
                    </button>
                    <button
                        className="bubble-btn dismiss"
                        onClick={() => {
                            onDismiss(activeSuggestion.id!);
                            setActiveSuggestion(null);
                        }}
                    >
                        <X size={14} /> 忽略
                    </button>
                </div>
            </div>
        </BubbleMenu>
    );
};
