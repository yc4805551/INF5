import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import { Node } from '@tiptap/pm/model';
import { AISuggestion } from '../../../types';

export interface AuditExtensionOptions {
    suggestions: AISuggestion[];
    onSuggestionClick?: (id: string) => void;
}

export const AuditExtension = Extension.create<AuditExtensionOptions>({
    name: 'auditExtension',

    addOptions() {
        return {
            suggestions: [],
            onSuggestionClick: undefined,
        };
    },

    addProseMirrorPlugins() {
        const { suggestions, onSuggestionClick } = this.options;

        return [
            new Plugin({
                key: new PluginKey('auditDecorations'),
                props: {
                    handleClick(view, pos, event) {
                        if (!onSuggestionClick) return false;

                        const target = event.target as HTMLElement;
                        if (target && target.hasAttribute('data-suggestion-id')) {
                            const id = target.getAttribute('data-suggestion-id');
                            if (id) {
                                onSuggestionClick(id);
                                return true; // Handled
                            }
                        }
                        return false;
                    },
                    decorations(state) {
                        const { doc } = state;
                        const decorations: Decoration[] = [];

                        if (!suggestions || suggestions.length === 0) {
                            return DecorationSet.create(doc, []);
                        }

                        // For each suggestion, find its position in the doc
                        // Note: ideally backend sends position, but for now we search.
                        // Optimization: Search only unique texts or cached positions.

                        const text = doc.textBetween(0, doc.content.size, '\n', '\n');

                        suggestions.forEach(suggestion => {
                            if (!suggestion.original) return;

                            // Simple global search - can be improved with precise positions
                            // This finds ALL occurrences, which might be risky if "the" is the error.
                            // But for "Proofreader", context usually makes it unique enough or we just highlight all.
                            // Better approach: User clicks to verify.

                            // Regex escape
                            const escapedKey = suggestion.original.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                            const regex = new RegExp(escapedKey, 'g');

                            let match;
                            while ((match = regex.exec(text)) !== null) {
                                const from = match.index;
                                const to = match.index + suggestion.original.length;

                                // Map plain text offset to Node positions (ProseMirror is tricky here)
                                // doc.resolve(pos) helps, but textBetween with default block separator simplified things.
                                // We need robust mapping. Let's use a node traversal instead for accuracy.
                                // NOTE: The below traversal finds the first match in each text node.
                            }
                        });


                        // Improved Traversal Strategy
                        doc.descendants((node, pos) => {
                            if (!node.isText || !node.text) return;

                            suggestions.forEach(suggestion => {
                                if (!suggestion.original) return;

                                // Reset regex to ensure fresh search on each node
                                // Using loop to find all occurrences in this node
                                const customNodeText = node.text || '';
                                let index = customNodeText.indexOf(suggestion.original);
                                while (index !== -1) {
                                    const from = pos + index;
                                    const to = from + suggestion.original.length;

                                    const className = suggestion.type === 'proofread'
                                        ? 'audit-error-proofread'
                                        : 'audit-error-polish';

                                    decorations.push(
                                        Decoration.inline(from, to, {
                                            class: className,
                                            'data-suggestion-id': suggestion.id, // For Bubble Menu to read
                                            'data-suggestion-type': suggestion.type
                                        })
                                    );

                                    // Search next occurrence
                                    index = customNodeText.indexOf(suggestion.original, index + 1);
                                }
                            });
                        });

                        return DecorationSet.create(doc, decorations);
                    },
                },
            }),
        ];
    },
});
