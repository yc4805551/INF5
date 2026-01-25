/**
 * 统一前端配置服务
 * 集中管理所有模型配置，确保全局一致性
 */

import { frontendApiConfig, MODEL_DISPLAY_NAMES } from './ai';

export interface ModelConfig {
    provider: string;
    apiKey?: string;
    endpoint?: string;
    model?: string;
}

/**
 * 获取指定 provider 的完整配置
 * 优先级：运行时覆盖 > frontendApiConfig > 默认值
 */
export const getModelConfig = (provider: string, overrides?: Partial<ModelConfig>): ModelConfig => {
    const baseConfig = frontendApiConfig[provider] || {};

    return {
        provider,
        apiKey: overrides?.apiKey || baseConfig.apiKey || '',
        endpoint: overrides?.endpoint || baseConfig.endpoint || '',
        model: overrides?.model || baseConfig.model || ''
    };
};

/**
 * 获取可用的模型列表
 */
export const getAvailableProviders = (): string[] => {
    return Object.keys(frontendApiConfig).filter(key => {
        const config = frontendApiConfig[key];
        if (key === 'gemini') return !!config.apiKey;
        return !!config.model;
    });
};

/**
 * 获取模型显示名称
 */
export const getProviderDisplayName = (provider: string): string => {
    return MODEL_DISPLAY_NAMES[provider] || provider;
};

/**
 * 验证配置是否完整
 */
export const validateConfig = (config: ModelConfig): { valid: boolean; errors: string[] } => {
    const errors: string[] = [];

    if (!config.provider) {
        errors.push('Provider is required');
    }

    if (!config.apiKey) {
        errors.push(`API Key is missing for ${config.provider}`);
    }

    if (!config.model && config.provider !== 'gemini') {
        errors.push(`Model name is missing for ${config.provider}`);
    }

    return {
        valid: errors.length === 0,
        errors
    };
};
