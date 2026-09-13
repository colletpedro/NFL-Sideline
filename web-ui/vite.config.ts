import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { runtimeClientModule } from './build/runtime-client-mode'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => ({
  plugins: [react()],
  resolve: {
    alias: {
      '#runtime-client': decodeURIComponent(new URL(
        runtimeClientModule(command, mode),
        (import.meta as ImportMeta & { url: string }).url,
      ).pathname),
    },
  },
}))
