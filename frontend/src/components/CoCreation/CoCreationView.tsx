import React, { useState, useRef, useEffect } from 'react';
import { ArrowLeft, Send, Plus, Upload, Bold, Italic, Heading1, Heading2, List, ListOrdered, Quote, Code, Undo, Redo, ClipboardList, BookOpen, X, Download, Wand2 } from 'lucide-react';
import { marked } from 'marked';
import mammoth from 'mammoth';
import './cocreation.css';
import { useCoCreation } from './useCoCreation';

// Tiptap
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Markdown } from 'tiptap-markdown';
import { Table } from '@tiptap/extension-table';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';
import TableRow from '@tiptap/extension-table-row';

interface CoCreationViewProps {
    onBack: () => void;
    callAiStream: (
        systemPrompt: string,
        userPrompt: string,
        history: any[],
        onChunk: (chunk: string) => void,
        onComplete: () => void,
        onError: (err: Error) => void
    ) => Promise<void>;
}

interface ContextFile {
    name: string;
    content: string;
    type: 'requirement' | 'reference';
}

const MenuBar = ({ editor }: { editor: any }) => {
    if (!editor) return null;

    return (
        <div className="cc-toolbar">
            <button onClick={() => editor.chain().focus().toggleBold().run()} className={`cc-tab ${editor.isActive('bold') ? 'active' : ''}`} title="Bold"><Bold size={16} /></button>
            <button onClick={() => editor.chain().focus().toggleItalic().run()} className={`cc-tab ${editor.isActive('italic') ? 'active' : ''}`} title="Italic"><Italic size={16} /></button>
            <div className="cc-divider"></div>
            <button onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} className={`cc-tab ${editor.isActive('heading', { level: 1 }) ? 'active' : ''}`} title="Heading 1"><Heading1 size={16} /></button>
            <button onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} className={`cc-tab ${editor.isActive('heading', { level: 2 }) ? 'active' : ''}`} title="Heading 2"><Heading2 size={16} /></button>
            <div className="cc-divider"></div>
            <button onClick={() => editor.chain().focus().toggleBulletList().run()} className={`cc-tab ${editor.isActive('bulletList') ? 'active' : ''}`} title="Bullet List"><List size={16} /></button>
            <button onClick={() => editor.chain().focus().toggleOrderedList().run()} className={`cc-tab ${editor.isActive('orderedList') ? 'active' : ''}`} title="Ordered List"><ListOrdered size={16} /></button>
            <div className="cc-divider"></div>
            <button onClick={() => editor.chain().focus().toggleBlockquote().run()} className={`cc-tab ${editor.isActive('blockquote') ? 'active' : ''}`} title="Blockquote"><Quote size={16} /></button>
            <button onClick={() => editor.chain().focus().toggleCodeBlock().run()} className={`cc-tab ${editor.isActive('codeBlock') ? 'active' : ''}`} title="Code Block"><Code size={16} /></button>
            <div className="cc-divider"></div>
            <button onClick={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()} className="cc-tab" title="Insert Table"><span style={{ fontSize: 12, fontWeight: 'bold' }}>Tbl</span></button>
            <div className="cc-divider"></div>
            <button onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} className="cc-tab" title="Undo"><Undo size={16} /></button>
            <button onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} className="cc-tab" title="Redo"><Redo size={16} /></button>
        </div>
    );
};

export const CoCreationView: React.FC<CoCreationViewProps> = ({ onBack, callAiStream }) => {
    const { state, setContent, addMessage, setProcessing } = useCoCreation();
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // File Inputs
    const importInputRef = useRef<HTMLInputElement>(null);
    const reqInputRef = useRef<HTMLInputElement>(null);
    const refInputRef = useRef<HTMLInputElement>(null);

    const [contextFiles, setContextFiles] = useState<ContextFile[]>([]);

    // Custom Bubble Menu State
    const [bubbleParams, setBubbleParams] = useState<{ x: number, y: number, visible: boolean } | null>(null);
    const [pendingRefinement, setPendingRefinement] = useState<{ from: number, to: number, text: string } | null>(null);

    const editor = useEditor({
        extensions: [
            StarterKit,
            Markdown,
            Table.configure({ resizable: true }),
            TableRow,
            TableHeader,
            TableCell,
        ],
        content: state.content,
        onUpdate: ({ editor }) => {
            const markdown = (editor.storage as any).markdown.getMarkdown();
            setContent(markdown);
        },
        onSelectionUpdate: ({ editor }) => {
            const { selection } = editor.state;
            const { empty, from, to } = selection;

            if (empty || from === to) {
                setBubbleParams(null);
                return;
            }

            // Calculate coords
            // We use the 'to' position (end of selection) to position the menu
            const coords = editor.view.coordsAtPos(to);
            // We need to offset relative to the viewport or container?
            // Since the menu will be fixed/absolute, viewport coords are usually best if using fixed.
            // But if our container is relative, we might need adjustments.
            // Let's us standard viewport coords and position: fixed for the menu.

            // Just a small delay to prevent flickering
            setTimeout(() => {
                if (editor.state.selection.empty) {
                    setBubbleParams(null);
                } else {
                    setBubbleParams({ x: coords.left, y: coords.top - 40, visible: true });
                }
            }, 50);
        }
    });

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => { scrollToBottom(); }, [state.messages]);

    const renderMarkdown = (text: string) => {
        try { return { __html: marked.parse(text) }; } catch (e) { return { __html: text }; }
    };

    const handleApply = (text: string) => {
        if (!editor) return;
        // Insert at cursor
        editor.chain().focus().insertContent(text).run();
    };

    const readContextFile = async (files: FileList | null, type: 'requirement' | 'reference') => {
        if (!files) return;
        Array.from(files).forEach(file => {
            const reader = new FileReader();
            reader.onload = async (event) => {
                const fileContent = event.target?.result;
                let text = '';
                if (file.name.endsWith('.docx')) {
                    try {
                        const result = await mammoth.extractRawText({ arrayBuffer: fileContent as ArrayBuffer });
                        text = result.value;
                    } catch (err) { alert(`无法解析 ${file.name}`); return; }
                } else { text = fileContent as string; }
                setContextFiles(prev => [...prev, { name: file.name, content: text, type }]);
            };
            if (file.name.endsWith('.docx')) reader.readAsArrayBuffer(file);
            else reader.readAsText(file);
        });
        if (reqInputRef.current) reqInputRef.current.value = '';
        if (refInputRef.current) refInputRef.current.value = '';
    };

    const handleImportToCanvas = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = async (event) => {
            const fileContent = event.target?.result;
            let text = '';
            if (file.name.endsWith('.docx')) {
                try {
                    const result = await mammoth.extractRawText({ arrayBuffer: fileContent as ArrayBuffer });
                    text = result.value;
                } catch (err) { alert("DOCX Error"); return; }
            } else { text = fileContent as string; }
            if (editor) editor.chain().focus().insertContentAt(editor.state.doc.content.size, '\n\n' + text).run();
            if (importInputRef.current) importInputRef.current.value = '';
        };
        if (file.name.endsWith('.docx')) reader.readAsArrayBuffer(file);
        else reader.readAsText(file);
    };

    const handleExport = () => {
        if (!editor) return;
        const markdown = (editor.storage as any).markdown.getMarkdown();
        const blob = new Blob([markdown], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'co-creation-canvas.md';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const handleExportDocx = async () => {
        if (!editor) return;
        const markdown = (editor.storage as any).markdown.getMarkdown();

        try {
            const response = await fetch('/api/canvas/export_docx', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ markdown })
            });

            if (!response.ok) throw new Error('Export failed');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'export.docx';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (e) {
            console.error(e);
            alert('导出 Word 失败');
        }
    };

    const removeFile = (index: number) => {
        setContextFiles(prev => prev.filter((_, i) => i !== index));
    };

    // Refinement Logic
    // ... (rest of logic)

    // ...

    <div className="cc-canvas-panel">
        <div className="cc-top-controls">
            <button className="cc-tab" style={{ width: 'auto', padding: '0 12px' }} onClick={() => importInputRef.current?.click()}><Upload size={14} style={{ marginRight: 6 }} /> 导入文件</button>
            <input type="file" ref={importInputRef} style={{ display: 'none' }} accept=".txt,.md,.docx" onChange={handleImportToCanvas} />
            <div className="cc-divider"></div>
            <button className="cc-tab" style={{ width: 'auto', padding: '0 12px' }} onClick={handleExport}><Download size={14} style={{ marginRight: 6 }} /> MD</button>
            <button className="cc-tab" style={{ width: 'auto', padding: '0 12px', marginLeft: 8 }} onClick={handleExportDocx}><Download size={14} style={{ marginRight: 6 }} /> Word</button>
        </div>

    // Refinement Logic
    const handleRefineRequest = () => {
        if (!editor || !bubbleParams) return;
        const {from, to} = editor.state.selection;
        const selectedText = editor.state.doc.textBetween(from, to, '\n');

        setPendingRefinement({from, to, text: selectedText });
        setInput(`Refine this text: "${selectedText}"`); // Pre-fill input
        setBubbleParams(null); // Hide menu
    };

    // Cancel refinement
    const cancelRefine = () => {
            setPendingRefinement(null);
        setInput('');
    };

    const handleSend = async () => {
        if (!input.trim() || state.isProcessing) return;
        const userText = input;
        setInput('');
        addMessage('user', userText);
        setProcessing(true);

        const fullContent = editor ? (editor.storage as any).markdown.getMarkdown() : state.content;
        const contextContent = fullContent.length > 6000 ? "...(truncated)\n" + fullContent.slice(-6000) : fullContent;

        const requirements = contextFiles.filter(f => f.type === 'requirement').map(f => f.content).join('\n\n');
        const references = contextFiles.filter(f => f.type === 'reference').map(f => f.content).join('\n\n');

        let systemPrompt = `You are a professional co-creation writing assistant.`;
        if (requirements.trim()) systemPrompt += `\n\n=== [REQUIREMENTS] ===\n${requirements}\n==================`;
        if (references.trim()) systemPrompt += `\n\n=== [REFERENCE] ===\n${references}\n===============`;

        systemPrompt += `\n\n=== DOCUMENT ===\n\`\`\`markdown\n${contextContent}\n\`\`\`\n`;

        // Refinement Prompting
        let isRefineMode = false;
        if (pendingRefinement) {
            systemPrompt += `\nTASK: REWRITE ONLY the selected text below based on user instruction.\nSELECTED TEXT: "${pendingRefinement.text}"\n`;
        isRefineMode = true;
        }

        systemPrompt += `\nINSTRUCTIONS:
        1. ONLY if the user EXPLICITLY asks for a "First Draft", "Full Article", "Rewrite Document", or "Fill Canvas", start response with ":::CANVAS:::".
        2. For normal questions (e.g., "Give me 3 titles", "Make this paragraph better"), DO NOT use ":::CANVAS:::". Instead, output Markdown code blocks in the chat.
        3. If Refinement Mode is active, start response with ":::CANVAS:::" to stream the replacement directly into the document.
        4. Support Tables.
        `;

        let currentResponse = '';
        let isCanvasStream = false;
        let lineBuffer = '';

        await callAiStream(
        systemPrompt,
        userText,
        state.messages,
            (chunk: string) => {
                // Check markers
                if (!isCanvasStream && (currentResponse + chunk).includes(':::CANVAS:::')) {
            isCanvasStream = true;
        // Remove marker
        const parts = (currentResponse + chunk).split(':::CANVAS:::');
        const cleanChunk = parts[1] || '';
        lineBuffer += cleanChunk;
        currentResponse = '';

        // If refinement, delete old text first
        if (isRefineMode && pendingRefinement && editor) {
            editor.chain().deleteRange({ from: pendingRefinement.from, to: pendingRefinement.to }).run();
                        // Reset so we don't delete again
                        // pendingRefinement = null; // Can't mute state inside callback easily without ref
                    }
        return;
                }

        if (isCanvasStream) {
                    const combined = lineBuffer + chunk;
        const lines = combined.split('\n');
        const partial = lines.pop();

                    if (lines.length > 0) {
                        const contentToInsert = lines.join('\n') + '\n';
        if (editor) editor.chain().insertContent(contentToInsert).run();
                    }
        lineBuffer = partial || '';
                } else {
            currentResponse += chunk;
                }
            },
            () => {
            setProcessing(false);
        if (isCanvasStream) {
                    if (lineBuffer && editor) {
            editor.chain().insertContent(lineBuffer).run();
                    }
        if (isRefineMode) {
            setPendingRefinement(null);
        addMessage('model', '✅ 已完成选中内容的修改。');
                    } else {
            addMessage('model', '✅ 内容已生成到画布。');
                    }
                } else {
            // Normal Chat Response
            addMessage('model', currentResponse);
                }
            },
            (err) => {
            setProcessing(false);
        addMessage('model', `Error: ${err.message}`);
            }
        );
    };

        const renderMessageContent = (msg: {role: string, text: string }) => {
        if (msg.role === 'user') return <div className="markdown-body" dangerouslySetInnerHTML={renderMarkdown(msg.text)} />;
        const parts = msg.text.split(/(```markdown[\s\S]*?```)/g);
        return (
        <div>
            {parts.map((part, index) => {
                const match = part.match(/^```markdown\s*([\s\S]*?)```$/);
                if (match) {
                    const codeContent = match[1];
                    return (
                        <div key={index} className="cc-code-block">
                            <div className="cc-code-header">
                                <span>Markdown Output</span>
                                <button className="cc-apply-btn" onClick={() => handleApply(codeContent)}><Plus size={14} /> 插入到画布</button>
                            </div>
                            <div className="cc-code-content">{codeContent}</div>
                        </div>
                    );
                } else { return !part.trim() ? null : <div key={index} className="markdown-body" dangerouslySetInnerHTML={renderMarkdown(part)} />; }
            })}
        </div>
        );
    };

        return (
        <div className="cc-container">
            {/* Custom Bubble Menu (Fixed Position) */}
            {bubbleParams && bubbleParams.visible && (
                <div
                    className="cc-bubble-menu-custom"
                    style={{
                        position: 'fixed',
                        left: bubbleParams.x,
                        top: bubbleParams.y,
                        zIndex: 1000
                    }}
                >
                    <button onClick={handleRefineRequest} className="cc-bubble-btn">
                        <Wand2 size={14} /> AI 优化选中
                    </button>
                </div>
            )}

            <div className="cc-chat-panel">
                <div className="cc-header">
                    <button onClick={onBack} className="cc-icon-btn"><ArrowLeft size={18} /></button>
                    <span className="cc-title">共创画布</span>
                </div>
                <div className="cc-messages">
                    {state.messages.map((msg, idx) => (
                        <div key={idx} className={`cc-message ${msg.role}`}>
                            <div className="cc-bubble">{renderMessageContent(msg)}</div>
                        </div>
                    ))}
                    {state.isProcessing && <div className="cc-message model"><div className="cc-bubble typing">思考中...</div></div>}
                    <div ref={messagesEndRef} />
                </div>
                <div className="cc-input-area-wrapper">
                    {contextFiles.length > 0 && (
                        <div className="cc-context-chips">
                            {contextFiles.map((file, idx) => (
                                <div key={idx} className={`cc-chip ${file.type}`}>
                                    {file.type === 'requirement' ? <ClipboardList size={12} /> : <BookOpen size={12} />}
                                    <span className="cc-chip-text">{file.name}</span>
                                    <button onClick={() => removeFile(idx)} className="cc-chip-remove"><X size={12} /></button>
                                </div>
                            ))}
                        </div>
                    )}
                    <div className="cc-input-area">
                        <button className="cc-icon-btn" title="Requirements" onClick={() => reqInputRef.current?.click()}><ClipboardList size={18} color="#ef4444" /></button>
                        <input type="file" ref={reqInputRef} multiple style={{ display: 'none' }} accept=".txt,.md,.docx" onChange={(e) => readContextFile(e.target.files, 'requirement')} />
                        <button className="cc-icon-btn" title="Reference" onClick={() => refInputRef.current?.click()}><BookOpen size={18} color="#3b82f6" /></button>
                        <input type="file" ref={refInputRef} multiple style={{ display: 'none' }} accept=".txt,.md,.docx" onChange={(e) => readContextFile(e.target.files, 'reference')} />

                        <div style={{ flex: 1, position: 'relative' }}>
                            {pendingRefinement && (
                                <div className="cc-refine-badge">
                                    <span>修饰模式</span>
                                    <button onClick={cancelRefine}><X size={10} /></button>
                                </div>
                            )}
                            <textarea value={input} onChange={e => setInput(e.target.value)} placeholder={pendingRefinement ? "输入修改指令..." : "输入指令..."} className={`cc-input ${pendingRefinement ? 'refining' : ''}`} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }} />
                        </div>

                        <button onClick={handleSend} disabled={!input.trim() || state.isProcessing} className="cc-send-btn"><Send size={18} /></button>
                    </div>
                </div>
            </div>

            <div className="cc-canvas-panel">
                <div className="cc-top-controls">
                    <button className="cc-tab" style={{ width: 'auto', padding: '0 12px' }} onClick={() => importInputRef.current?.click()}><Upload size={14} style={{ marginRight: 6 }} /> 导入文件</button>
                    <input type="file" ref={importInputRef} style={{ display: 'none' }} accept=".txt,.md,.docx" onChange={handleImportToCanvas} />
                    <div className="cc-divider"></div>
                    <button className="cc-tab" style={{ width: 'auto', padding: '0 12px' }} onClick={handleExport}><Download size={14} style={{ marginRight: 6 }} /> 导出 Markdown</button>
                </div>
                <MenuBar editor={editor} />
                <div className="cc-editor-container tiptap-wrapper" onClick={() => editor?.commands.focus()}>
                    <EditorContent editor={editor} className="cc-editor-content" />
                </div>
            </div>
        </div>
        );
};
