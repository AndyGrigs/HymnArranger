/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_FLAT_APP_ID: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module 'html-midi-player';