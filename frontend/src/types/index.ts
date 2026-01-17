export interface NoteAnalysis {
    organizedText: string;
    userThoughts: string;
}

export interface AuditIssue {
    problematicText: string;
    suggestion: string;
    checklistItem: string; // The rule from the checklist that was violated
    explanation: string; // Explanation of the issue
}

export interface WritingSuggestion {
    originalText: string;
    revisedText: string;
    explanation: string;
}

export interface Source {
    source_file: string;
    content_chunk: string;
    score: number;
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
}

export interface RoamingResultItem {
    source: string;
    relevantText: string;
    conclusion: string;
}

export type NoteChatMessage = {
    role: 'user' | 'model';
    text: string;
    isError?: boolean;
    sources?: Source[];
    isComplete?: boolean;
};

export type ModelProvider = 'gemini' | 'openai' | 'deepseek' | 'ali' | 'depOCR' | 'doubao' | 'anything';

export type ChatMessage = {
    role: 'user' | 'model';
    parts: { text: string }[];
    resultType?: 'notes';
    resultData?: NoteAnalysis;
};

export type ExecutionMode = 'backend' | 'frontend';

export interface AuditResult {
    issues: AuditIssue[];
    error?: string;
    rawResponse?: string;
    report?: string; // For AnythingLLM Agent text report
}

export type AuditResults = {
    [key in ModelProvider]?: AuditResult
};

export interface ModelConfig {
    [key: string]: any;
}
