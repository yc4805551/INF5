import { useState, useEffect } from 'react';
import axios from 'axios';
import type { ModelConfig, CanvasState, ChatMessage } from '../types';

// Reuse types from existing canvas if appropriate or define new ones

const API_URL = import.meta.env.PROD
    ? (import.meta.env.VITE_API_BASE_URL ? `${import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '')}/api/canvas` : '/api/canvas')
    : '/proxy-api/canvas';

export const useWordCanvas = () => {
    const [state, setState] = useState<CanvasState>({
        htmlPreview: '',
        isUploading: false,
        isProcessing: false,
        hasFile: false,
        messages: [],
        selectionContext: null,
        // Pagination
        page: 1,
        totalParagraphs: 0,
        pageSize: 100,
        structure: [],
        activeScope: null,
        referenceFiles: [],
        isChatLoading: false // Init
    });

    const updateState = (newState: Partial<CanvasState>) => {
        setState(prev => ({ ...prev, ...newState }));
    };

    const loadPage = async (page: number, append: boolean = false) => {
        if (!state.hasFile) return;
        try {
            updateState({ isProcessing: true });
            const response = await axios.get(`${API_URL}/preview_html`, {
                params: {
                    page,
                    page_size: state.pageSize,
                    _t: Date.now() // Cache busting
                }
            });

            updateState({
                htmlPreview: append ? state.htmlPreview + response.data.html : response.data.html,
                page: page,
                totalParagraphs: response.data.total_paragraphs,
                isProcessing: false
            });
        } catch (error) {
            console.error("Load page failed", error);
            updateState({ isProcessing: false });
        }
    };

    const fetchReferences = async () => {
        try {
            const res = await axios.get(`${API_URL}/references`);
            if (res.data.references) {
                updateState({ referenceFiles: res.data.references });
            }
        } catch (error) {
            console.error("Failed to fetch references", error);
        }
    };

    useEffect(() => {
        const fetchPreview = async () => {
            try {
                const res = await axios.get(`${API_URL}/preview_html`, { params: { _t: Date.now() } });
                if (res.data.html) {
                    const isRealDoc = !res.data.html.includes('No document loaded');
                    updateState({
                        htmlPreview: res.data.html,
                        hasFile: isRealDoc,
                        structure: res.data.structure || [] // Capture structure on reload
                    });
                }
                // Also fetch references
                fetchReferences();

            } catch (error) {
                console.error("Failed to fetch initial preview", error);
            }
        };
        fetchPreview();
    }, []);

    const handleFileUpload = async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        try {
            updateState({ isUploading: true });
            const res = await axios.post(`${API_URL}/upload`, formData);
            updateState({
                htmlPreview: res.data.html_preview,
                hasFile: true,
                messages: [],
                page: 1,
                totalParagraphs: res.data.total_paragraphs || 0,
                pageSize: res.data.page_size || 100,
                structure: res.data.structure || [] // Capture structure
            });
            // Fetch refs too in case they persist? Or clear?
            // Usually new upload clears engine?
            // Yes, docx_engine reset() clears refs!
            // So we should clear refs in state or fetch.
            updateState({ referenceFiles: [] });

        } catch (error) {
            console.error("Upload failed", error);
            alert("Upload failed");
        } finally {
            updateState({ isUploading: false });
        }
    };

    const loadFromText = async (text: string) => {
        try {
            updateState({ isProcessing: true });
            const res = await axios.post(`${API_URL}/create_with_text`, { text });
            updateState({
                htmlPreview: res.data.html_preview,
                hasFile: true,
                messages: [],
                page: 1,
                totalParagraphs: res.data.total_paragraphs || 0,
                pageSize: res.data.page_size || 100,
                structure: res.data.structure || []
            });
            updateState({ referenceFiles: [] });
        } catch (error) {
            console.error("Load from text failed", error);
        } finally {
            updateState({ isProcessing: false });
        }
    };

    const handleSendMessage = async (text: string, modelConfig: ModelConfig) => {
        const newMessage: ChatMessage = { role: 'user', content: text };
        const updatedMessages = [...state.messages, newMessage];
        updateState({ messages: updatedMessages, isChatLoading: true }); // Use separate loading for chat

        try {
            const response = await axios.post(`${API_URL}/chat`, {
                message: text,
                model_config: modelConfig,
                history: updatedMessages.map(m => ({ role: m.role, content: m.content })), // Send history
                selection_context: state.selectionContext ? [state.selectionContext.id] : [],
                // Send scope_range if activeScope is set, otherwise send page info context helper
                scope_range: state.activeScope ? [state.activeScope.start, state.activeScope.end] : null,
                page: state.page,
                page_size: state.pageSize
            });

            const aiReply = response.data.reply;
            updateState({
                messages: [...updatedMessages, { role: 'ai', content: aiReply }],
                isChatLoading: false,
                isPendingConfirmation: response.data.is_staging,
                htmlPreview: response.data.html_preview || state.htmlPreview
            });

            // Reload page or jump to scope?
            if (response.data.intent === 'MODIFY') {
                // If scoped, maybe jump to start of scope?
                // For now, keep current page or reload active page
                loadPage(state.page);
            }
        } catch (error) {
            console.error(error);
            updateState({
                messages: [...updatedMessages, { role: 'ai', content: '抱歉，处理消息时出错。' }],
                isChatLoading: false
            });
        }
    };

    const toggleScope = (item: { id: number, end_id?: number, title: string } | null) => {
        if (!item) {
            updateState({ activeScope: null });
            return;
        }
        // Toggle off if clicking same
        if (state.activeScope && state.activeScope.start === item.id) {
            updateState({ activeScope: null });
        } else {
            updateState({
                activeScope: {
                    start: item.id,
                    end: item.end_id || item.id + 100, // Fallback 
                    title: item.title
                }
            });
        }
    };

    const handleReferenceUpload = async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        try {
            const res = await axios.post(`${API_URL}/upload_reference`, formData);
            if (res.data.references) {
                updateState({ referenceFiles: res.data.references });
            }
        } catch (error: any) {
            console.error("Reference upload failed", error);
            const msg = error.response?.data?.error || error.message || "未知错误";
            alert(`上传参考文件失败: ${msg}`);
        }
    };

    const handleRemoveReference = async (filename: string) => {
        try {
            const res = await axios.post(`${API_URL}/remove_reference`, { filename });
            if (res.data.references) {
                updateState({ referenceFiles: res.data.references });
            }
        } catch (error) {
            console.error("Remove reference failed", error);
        }
    };

    const handleConfirm = async () => {
        if (state.isProcessing) return;
        updateState({ isProcessing: true });
        try {
            const res = await axios.post(`${API_URL}/confirm`);
            updateState({
                htmlPreview: res.data.html_preview, // Real-time update
                isPendingConfirmation: false
            });
        } catch (error) {
            console.error("Confirm failed", error);
            alert("确认修改失败");
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
                htmlPreview: res.data.html_preview, // Real-time revert
                isPendingConfirmation: false
            });
        } catch (error) {
            console.error("Discard failed", error);
            alert("取消修改失败");
        } finally {
            updateState({ isProcessing: false });
        }
    };

    const reset = async () => {
        if (!confirm("确定要重置画布吗？所有未保存的更改和参考文件将被清除。")) return;

        try {
            await axios.post(`${API_URL}/reset`);
            setState({
                htmlPreview: '',
                isUploading: false,
                isProcessing: false,
                hasFile: false,
                messages: [],
                selectionContext: null,
                page: 1,
                totalParagraphs: 0,
                pageSize: 100,
                structure: [],
                activeScope: null,
                referenceFiles: [],
                isChatLoading: false
            });
        } catch (error) {
            console.error("Reset failed", error);
            alert("重置失败");
        }
    };

    const handleFormat = async (modelConfig: ModelConfig, scope: 'all' | 'layout' | 'body' = 'all', processor: 'local' | 'ai' = 'local', forceUnbold: boolean = false) => {
        updateState({ isProcessing: true });
        try {
            const res = await axios.post(`${API_URL}/format_official`, {
                model_config: modelConfig,
                scope,
                processor,
                force_unbold: forceUnbold
            });

            updateState({
                htmlPreview: res.data.html_preview,
                isPendingConfirmation: true,
            });

        } catch (error) {
            console.error("Format failed", error);
            alert("格式处理失败");
        } finally {
            updateState({ isProcessing: false });
        }
    };

    const handleSelection = (id: number, text: string) => {
        updateState({ selectionContext: { id, text } });
    };

    const clearSelection = () => {
        updateState({ selectionContext: null });
    };

    const handleDownload = async () => {
        try {
            const response = await axios.get(`${API_URL}/download`, {
                responseType: 'blob',
            });

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'modified_document.docx');
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error("Download failed", error);
            alert("下载失败");
        }
    };

    return {
        state,
        updateState,
        handleConfirm,
        handleDiscard,
        handleFileUpload,
        handleReferenceUpload,
        handleSendMessage,
        handleSelection,
        clearSelection,
        reset,
        handleDownload,
        loadPage,
        toggleScope,
        handleRemoveReference,
        handleFormat,
        loadFromText
    };
};



