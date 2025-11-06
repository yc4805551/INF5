// FIX: Removed the reference to "vite/client" which was causing a "Cannot find type definition file" error.
// The custom ImportMeta and ImportMetaEnv interfaces below provide the necessary types for the project.

interface ImportMetaEnv {
  // FIX: Added the PROD property to match Vite's built-in environment variables and fix the error in index.tsx.
  readonly PROD: boolean;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_GEMINI_API_KEY?: string;
  readonly VITE_OPENAI_API_KEY?: string;
  readonly VITE_OPENAI_TARGET_URL?: string;
  readonly VITE_OPENAI_MODEL?: string;
  readonly VITE_DEEPSEEK_API_KEY?: string;
  readonly VITE_DEEPSEEK_ENDPOINT?: string;
  readonly VITE_DEEPSEEK_MODEL?: string;
  readonly VITE_ALI_API_KEY?: string;
  readonly VITE_ALI_TARGET_URL?: string;
  readonly VITE_ALI_ENDPOINT?: string;
  readonly VITE_ALI_MODEL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module 'mammoth' {
  interface MammothResult {
    value: string;
    messages: any[];
  }

  const mammoth: {
    extractRawText(options: { arrayBuffer: ArrayBuffer }): Promise<MammothResult>;
  };

  export default mammoth;
}
