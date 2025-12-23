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
    role: 'user' | 'assistant' | 'ai' | 'model';
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

export type ChatMessage = Message;

export interface TocItem {
    id: number;
    title: string;
    level: number;
    page: number;
    end_id?: number; // Optional as older docs might not have it initially
}

export interface CanvasState {
    htmlPreview: string;
    isUploading: boolean;
    isProcessing: boolean;
    hasFile: boolean;
    messages: ChatMessage[];
    selectionContext: { id: number; text: string } | null;
    page: number;
    totalParagraphs: number;
    pageSize: number;
    structure: TocItem[];
    activeScope: { start: number; end: number; title: string } | null;
    referenceFiles: string[];
    isChatLoading?: boolean; // Separate chat loading state
}
