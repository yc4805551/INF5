// Fast Canvas 数据类型定义

/**
 * 快速画布文档数据结构
 */
export interface FastDocument {
    id: string;
    title: string;
    created: number;
    updated: number;
    content: ContentBlock[];
    metadata: DocumentMetadata;
}

/**
 * 内容块（段落）
 */
export interface ContentBlock {
    id: string;
    type: BlockType;
    text: string;
    style?: BlockStyle;
    order: number;
}

export type BlockType =
    | 'paragraph'
    | 'heading1'
    | 'heading2'
    | 'heading3'
    | 'list'
    | 'quote';

export interface BlockStyle {
    bold?: boolean;
    italic?: boolean;
    underline?: boolean;
    align?: 'left' | 'center' | 'right';
}

export interface DocumentMetadata {
    wordCount: number;
    characterCount: number;
    lastSync?: number;
    version: number;
}

/**
 * 智能建议类型
 */
export interface AISuggestion {
    id: string;
    blockId: string;
    type: 'proofread' | 'polish' | 'logic' | 'format' | 'style' | 'terminology';
    severity: 'critical' | 'high' | 'medium' | 'low';
    original: string;
    suggestion: string;
    reason: string;
    confidence?: 'high' | 'medium' | 'low'; // AI 反思机制：对修改建议的信心等级
    position?: {
        start: number;
        end: number;
    };
}

/**
 * 审核结果
 */
export interface AuditResult {
    status: 'PASS' | 'WARNING' | 'FAIL';
    score: number;
    issues: AISuggestion[];
    summary: string;
    timestamp: number;
}

/**
 * 统一助手模式
 */
export type AssistantMode = 'realtime' | 'audit' | 'chat';

export interface AssistantState {
    mode: AssistantMode;
    isAnalyzing: boolean;
    suggestions: AISuggestion[];
    auditResult: AuditResult | null;
    history: AISuggestion[];
}

/**
 * 聊天消息结构
 */
export interface ChatMessage {
    role: 'user' | 'model';
    parts: { text: string }[];
}
