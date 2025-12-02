export interface ModelConfig {
    provider: 'gemini' | 'openai' | 'deepseek' | 'aliyun';
    apiKey?: string;
    endpoint?: string;
    model?: string;
}

export interface PreviewItem {
    id: number;
    text: string;
    style: string;
    runs: Array<{
        text: string;
        bold: boolean;
        italic: boolean;
        underline: boolean;
        color: string | null;
        fontSize: number | null;
    }>;
}

export interface Message {
    role: 'user' | 'assistant';
    content: string;
}

export interface DocxEditorState {
    previewData: PreviewItem[];
    isUploading: boolean;
    isProcessing: boolean;
    hasFile: boolean;
    isPendingConfirmation: boolean;
    showBodyFormatDialog?: boolean;
    lastModelConfig?: ModelConfig;
    messages: Message[];
    selectionContext?: { text: string; ids: number[] } | null;
}
