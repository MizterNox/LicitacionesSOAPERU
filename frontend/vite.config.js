import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // 0.0.0.0 — visible en el preview
    port: 8080,
    strictPort: true,
    // El preview proxya a través de un host externo ({port}-{sandboxId}.e2b.app):
    // permitir cualquier host para que la vista previa cargue.
    allowedHosts: true,
  },
})
