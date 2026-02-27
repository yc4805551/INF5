import React, { useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { AuditExtension } from './extensions/AuditExtension';

import { AISuggestion } from '../../types';
import './TiptapEditor.css';
import './extensions/AuditExtension.css';

interface TiptapEditorProps {
    value: string;
    onChange: (html: string, text: string) => void;
    editable?: boolean;
    suggestions?: AISuggestion[];
    onApplySuggestion?: (suggestion: AISuggestion) => void;
    onDismissSuggestion?: (id: string) => void;
    onSuggestionClick?: (id: string) => void;
}

export interface TiptapEditorRef {
    replaceText: (original: string, replacement: string) => boolean;
    selectText: (text: string) => boolean;
    setContent: (content: any) => boolean;
    insertContent: (content: string) => boolean;
}

export const TiptapEditor = React.forwardRef<TiptapEditorRef, TiptapEditorProps>(({
    value,
    onChange,
    editable = true,
    suggestions = [],
    onApplySuggestion,
    onDismissSuggestion,
    onSuggestionClick
}, ref) => {
    const editor = useEditor({
        extensions: [
            StarterKit,
            AuditExtension.configure({
                suggestions: suggestions,
                onSuggestionClick: onSuggestionClick
            })
        ],
        content: value,
        editable: editable,
        onUpdate: ({ editor }) => {
            const html = editor.getHTML();
            const text = editor.getText();
            onChange(html, text);
        },
        editorProps: {
            attributes: {
                class: 'prose prose-sm sm:prose lg:prose-lg xl:prose-2xl mx-auto focus:outline-none custom-tiptap-editor',
            },
        },
    });

    // Update extension options when suggestions change
    useEffect(() => {
        if (editor && suggestions) {
            // Reconfigure extension to force update decorations
            // Tiptap extension configuration update
            // We might need to destroy/recreate or specific command? 
            // extension-kit usually allows .configure() but runtime updates are tricky.
            // Let's try destroying and re-adding? No, that loses state.
            // Best way: The extension reads checks this.options.
            // We can hack it by re-setting the extension config via a custom command or just forcing update.
            // Actually, `useEditor` dependencies re-create the editor if deps change. 
            // But we don't want to re-create editor on every typing.

            // Let's try just re-running decorations by dispatching a transaction
            // But we need to update the OPTIONS inside the extension instance.
            // Valid Tiptap way: editor.extensionStorage['auditExtension'].suggestions = suggestions;
            // But our extension logic reads `this.options`.

            // Let's use a simpler approach: define suggestions as a prop passed to the extension
            // or use `editor.setOptions`.

            // Note: Tiptap doesn't deeply watch config obj.
            // Workaround: We'll make the extension read from a command or storage.
            // Or simpler: Just re-mount the component? No.

            // Let's rely on `useEditor` dependency array for now, but that reset cursor.
            // Better: update valid options.
            if (!editor.isDestroyed) {
                // Hack to update options directly
                const extension = editor.extensionManager.extensions.find(e => e.name === 'auditExtension');
                if (extension) {
                    extension.options.suggestions = suggestions;
                    // Force re-render decorations
                    editor.view.dispatch(editor.state.tr);
                }
            }
        }
    }, [editor, suggestions]);

    // Expose methods via ref
    React.useImperativeHandle(ref, () => ({
        replaceText: (original: string, replacement: string) => {
            if (!editor) return false;

            // Search for the text in the document
            // Simplified search: finding first occurrence in text nodes
            const { state } = editor;
            const { doc } = state;

            let foundPos = -1;

            try {
                // Iterate through nodes to find text
                doc.descendants((node, pos) => {
                    if (foundPos !== -1) return false; // Stop if found

                    if (node.isText && node.text) {
                        const index = node.text.indexOf(original);
                        if (index !== -1) {
                            foundPos = pos + index;
                            return false; // Stop iteration
                        }
                    }
                });

                if (foundPos !== -1) {
                    editor.chain()
                        .focus()
                        .setTextSelection({ from: foundPos, to: foundPos + original.length })
                        .insertContent(replacement)
                        .run();
                    return true;
                }
            } catch (e) {
                console.error("Replacement failed", e);
            }
            return false;
        },
        selectText: (text: string) => {
            if (!editor) return false;
            const { doc } = editor.state;
            let foundPos = -1;
            doc.descendants((node, pos) => {
                if (foundPos !== -1) return false;
                if (node.isText && node.text) {
                    const index = node.text.indexOf(text);
                    if (index !== -1) {
                        foundPos = pos + index;
                        return false;
                    }
                }
            });

            if (foundPos !== -1) {
                editor.chain()
                    .focus()
                    .setTextSelection({ from: foundPos, to: foundPos + text.length })
                    .scrollIntoView()
                    .run();
                return true;
            }
            return false;
        },
        setContent: (content: any) => {
            if (editor) {
                editor.commands.setContent(content);
                return true;
            }
            return false;
        },
        insertContent: (content: string) => {
            if (editor) {
                // Focus at the end of the document and insert
                editor.chain().focus().insertContent(content).run();
                return true;
            }
            return false;
        }
    }));

    // Sync external value changes if needed (e.g. loaded from backend)
    // Avoid loops by checking if content is different
    useEffect(() => {
        if (editor && value && editor.getHTML() !== value) {
            // Only set content if it's drastically different to avoid cursor jumps
            if (editor.getText() === '') {
                editor.commands.setContent(value);
            }
        }
    }, [value, editor]);

    if (!editor) {
        return null;
    }

    return (
        <div className="tiptap-container">
            {/* Toolbar */}
            <MenuBar editor={editor} />

            <div className="editor-scroll-area">
                <EditorContent editor={editor} />
            </div>
        </div>
    );
});

const MenuBar = ({ editor }: { editor: any }) => {
    if (!editor) {
        return null;
    }

    return (
        <div className="tiptap-menu-bar">
            {/* ... Existing buttons ... */}
            <button
                onClick={() => editor.chain().focus().toggleBold().run()}
                disabled={!editor.can().chain().focus().toggleBold().run()}
                className={editor.isActive('bold') ? 'is-active' : ''}
            >
                Bold
            </button>
            <button
                onClick={() => editor.chain().focus().toggleItalic().run()}
                disabled={!editor.can().chain().focus().toggleItalic().run()}
                className={editor.isActive('italic') ? 'is-active' : ''}
            >
                Italic
            </button>
            <button
                onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
                className={editor.isActive('heading', { level: 1 }) ? 'is-active' : ''}
            >
                H1
            </button>
            <button
                onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                className={editor.isActive('heading', { level: 2 }) ? 'is-active' : ''}
            >
                H2
            </button>
            <button
                onClick={() => editor.chain().focus().toggleBulletList().run()}
                className={editor.isActive('bulletList') ? 'is-active' : ''}
            >
                Bullet List
            </button>
        </div>
    );
};
