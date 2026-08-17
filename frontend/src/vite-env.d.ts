/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_FLAT_APP_ID?: string;
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module 'html-midi-player';