import { useState, useCallback, useRef } from 'react';

export type CoCreationState = {
    content: string;
    messages: Array<{ role: 'user' | 'model'; text: string }>;
    isProcessing: boolean;
};

export const useCoCreation = () => {
    const [state, setState] = useState<CoCreationState>({
        content: '# Untitled Document\n\nStart writing here...',
        messages: [{ role: 'model', text: 'Hi! I\'m your co-creation partner. We can write this document together.' }],
        isProcessing: false,
    });

    const setContent = useCallback((newContent: string) => {
        setState(prev => ({ ...prev, content: newContent }));
    }, []);

    const addMessage = useCallback((role: 'user' | 'model', text: string) => {
        setState(prev => ({
            ...prev,
            messages: [...prev.messages, { role, text }]
        }));
    }, []);

    const handleSendMessage = useCallback(async (text: string, provider: string, apiKey: string | undefined, endpoint: string | undefined, model: string | undefined) => {
        if (!text.trim()) return;

        addMessage('user', text);
        setState(prev => ({ ...prev, isProcessing: true }));

        try {
            // Prepare context
            const systemPrompt = `You are a collaborative writing assistant. 
The user is writing a document in Markdown format.
Current Document Content:
\`\`\`markdown
${state.content}
\`\`\`

If the user asks to write/update/rewrite content, provide the NEW Markdown content inside a code block tagged with \`markdown\`.
If the user asks a question, just answer.
`;

            // Construct API call (Simplified adapting from index.tsx logic)
            // Note: This is a duplicate of the logic in index.tsx, ideally we pass a 'generate' function prop.
            // But for now, we'll let the View handle the actual API call or use a passed callback.
            // Returning control to View to execute exact API call to avoid code duplication in hook if possible.
            // However, to keep this hook self-contained, we might need a fetcher.
            // Let's assume the View passes the properly constructed 'callAI' function.

        } catch (error) {
            console.error(error);
            addMessage('model', 'Error processing request.');
        } finally {
            setState(prev => ({ ...prev, isProcessing: false }));
        }
    }, [state.content, addMessage]);

    return {
        state,
        setContent,
        addMessage,
        setProcessing: (isProcessing: boolean) => setState(prev => ({ ...prev, isProcessing }))
    };
};
