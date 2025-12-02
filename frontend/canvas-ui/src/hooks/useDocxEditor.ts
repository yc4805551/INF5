import { useState } from 'react';
import axios from 'axios';
import type { DocxEditorState, ModelConfig } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5431';

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
        try {
            const res = await axios.post(`${API_URL}/confirm`);
            updateState({
                previewData: res.data.preview,
                isPendingConfirmation: false
            });
        } catch (error) {
            console.error("Confirm failed", error);
            alert("Failed to confirm changes");
        }
    };

    const handleDiscard = async () => {
        try {
            const res = await axios.post(`${API_URL}/discard`);
            updateState({
                previewData: res.data.preview,
                isPendingConfirmation: false
            });
        } catch (error) {
            console.error("Discard failed", error);
            alert("Failed to discard changes");
        }
    };

    const handleFormat = async (modelConfig: ModelConfig, scope: 'all' | 'layout' | 'body' = 'all') => {
        updateState({ isProcessing: true });
        try {
            const res = await axios.post(`${API_URL}/format_official`, {
                model_config: modelConfig,
                scope
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

    return {
        state,
        handleFileUpload,
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
