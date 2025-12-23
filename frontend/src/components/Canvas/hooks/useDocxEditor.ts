import { useState } from 'react';
import axios from 'axios';
import type { DocxEditorState, ModelConfig } from '../types';

const API_URL = import.meta.env.PROD
    ? `${(import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')}/api/canvas`
    : '/proxy-api/canvas';

export const useDocxEditor = () => {
    const [state, setState] = useState<DocxEditorState>({
        previewData: [],
        isUploading: false,
        isProcessing: false,
        hasFile: false,
        isPendingConfirmation: false,
        showBodyFormatDialog: false,
        messages: [],
        selectionContext: null
    });

    const updateState = (updates: Partial<DocxEditorState>) => {
        setState(prev => ({ ...prev, ...updates }));
    };

    const handleFileUpload = async (file: File) => {
        updateState({ isUploading: true });
        const formData = new FormData();
        formData.append('file', file);
        try {
            const res = await axios.post(`${API_URL}/upload`, formData);
            updateState({
                previewData: res.data.preview,
                hasFile: true,
                isPendingConfirmation: false,
                messages: [] // Reset chat on new file
            });
        } catch (error) {
            console.error("Upload failed", error);
            alert("Upload failed");
        } finally {
            updateState({ isUploading: false });
        }
    };

    const handleSendMessage = async (message: string, modelConfig: ModelConfig) => {
        // Optimistic update
        const userMsg = { role: 'user', content: message } as const;
        setState(prev => ({
            ...prev,
            isProcessing: true,
            messages: [...prev.messages, userMsg]
        }));

        try {
            const res = await axios.post(`${API_URL}/chat`, {
                message,
                model_config: modelConfig,
                history: state.messages, // Pass history
                selection_context: state.selectionContext ? state.selectionContext.ids : [] // Pass selection IDs
            });

            const assistantMsg = { role: 'assistant', content: res.data.reply } as const;

            updateState({
                previewData: res.data.preview || [],
                isPendingConfirmation: res.data.intent === 'MODIFY',
                messages: [...state.messages, userMsg, assistantMsg]
            });
        } catch (error) {
            console.error("Chat failed", error);
            alert("Failed to process instruction");
            // Remove user message on failure? Or just show error?
        } finally {
            updateState({ isProcessing: false });
        }
    };

    const handleConfirm = async () => {
        if (state.isProcessing) return;
        updateState({ isProcessing: true });
        try {
            const res = await axios.post(`${API_URL}/confirm`);
            updateState({
                previewData: res.data.preview,
                isPendingConfirmation: false
            });
        } catch (error) {
            console.error("Confirm failed", error);
            alert("Failed to confirm changes");
        } finally {
            updateState({ isProcessing: false });
        }
    };

    const handleDiscard = async () => {
        if (state.isProcessing) return;
        updateState({ isProcessing: true });
        try {
            const res = await axios.post(`${API_URL}/discard`);
            updateState({
                previewData: res.data.preview,
                isPendingConfirmation: false
            });
        } catch (error) {
            console.error("Discard failed", error);
            alert("Failed to discard changes");
        } finally {
            updateState({ isProcessing: false });
        }
    };

    const handleFormat = async (modelConfig: ModelConfig, scope: 'all' | 'layout' | 'body' = 'all', processor: 'local' | 'ai' = 'local') => {
        updateState({ isProcessing: true });
        try {
            const res = await axios.post(`${API_URL}/format_official`, {
                model_config: modelConfig,
                scope,
                processor
            });

            // If layout only, show dialog for body
            const showDialog = scope === 'layout';

            updateState({
                previewData: res.data.preview,
                isPendingConfirmation: true, // Always pending confirmation after format
                showBodyFormatDialog: showDialog,
                lastModelConfig: modelConfig
            });
        } catch (error) {
            console.error("Format failed", error);
            alert("Failed to format document");
        } finally {
            updateState({ isProcessing: false });
        }
    };

    const handleBodyFormatConfirm = async () => {
        if (!state.lastModelConfig) return;

        // Close dialog immediately to show processing state
        updateState({ showBodyFormatDialog: false });

        // Call format with body scope
        await handleFormat(state.lastModelConfig, 'body');
    };

    const handleBodyFormatCancel = () => {
        updateState({ showBodyFormatDialog: false });
    };

    const reset = () => {
        setState({
            previewData: [],
            isUploading: false,
            isProcessing: false,
            hasFile: false,
            isPendingConfirmation: false,
            showBodyFormatDialog: false,
            messages: [],
            selectionContext: null
        });
    };

    const handleDownload = () => {
        window.open(`${API_URL}/download`, '_blank');
    };

    const handleSelectionEdit = (text: string, ids: number[]) => {
        updateState({ selectionContext: { text, ids } });
    };

    const handleClearSelection = () => {
        updateState({ selectionContext: null });
    };

    const handleReferenceUpload = async (file: File) => {
        updateState({ isUploading: true });
        const formData = new FormData();
        formData.append('file', file);
        try {
            // Use smart_canvas/upload for backend processing (images, etc)
            // Note: backend endpoint is /api/smart_canvas/upload
            // If proxy is working, we can hit it relatively.
            // But API_URL currently points to /api/canvas. 
            // Let's deduce base API url.
            const baseUrl = API_URL.replace(/\/canvas$/, '');
            const res = await axios.post(`${baseUrl}/smart_canvas/upload`, formData);

            // Add reference to chat context or just display it?
            // For now, let's treat it as a system message or user context injection.
            const refMsg = {
                role: 'user',
                content: `[参考资料: ${file.name}]\n\n${res.data.markdown}`
            } as const;

            setState(prev => ({
                ...prev,
                messages: [...prev.messages, refMsg]
            }));

        } catch (error: any) {
            console.error("Reference upload failed", error);
            const errMsg = error.response?.data?.error || error.message;
            alert(`Reference upload error: ${errMsg}`);
        } finally {
            updateState({ isUploading: false });
        }
    };

    return {
        state,
        handleFileUpload,
        handleReferenceUpload,
        handleSendMessage,
        handleConfirm,
        handleDiscard,
        handleFormat,
        handleDownload,
        reset,
        handleBodyFormatConfirm,
        handleBodyFormatCancel,
        handleSelectionEdit,
        handleClearSelection,
        updateState
    };
};
