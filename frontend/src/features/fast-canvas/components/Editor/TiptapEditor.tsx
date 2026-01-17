import React, { useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import './TiptapEditor.css';

interface TiptapEditorProps {
    value: string;
    onChange: (html: string, text: string) => void;
    editable?: boolean;
}

export interface TiptapEditorRef {
    replaceText: (original: string, replacement: string) => boolean;
}

export const TiptapEditor = React.forwardRef<TiptapEditorRef, TiptapEditorProps>(({
    value,
    onChange,
    editable = true
}, ref) => {
    const editor = useEditor({
        extensions: [
            StarterKit,
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
            {/* Toolbar could be added here */}
            <MenuBar editor={editor} />
            <EditorContent editor={editor} />
        </div>
    );
});

const MenuBar = ({ editor }: { editor: any }) => {
    if (!editor) {
        return null;
    }

    return (
        <div className="tiptap-menu-bar">
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
