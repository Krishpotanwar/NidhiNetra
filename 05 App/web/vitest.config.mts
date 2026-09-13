import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'

// Per Next.js 16's own bundled guide (node_modules/next/dist/docs/01-app/
// 02-guides/testing/vitest.md): async Server Components aren't supported by
// Vitest yet, so this covers synchronous Client Components only. Nothing in
// components/ is an async Server Component today (confirmed by grep before
// this file was written), so that limitation doesn't currently cut anything.
export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: 'jsdom',
    // vitest.setup.ts imports '@testing-library/jest-dom/vitest', whose
    // runtime half patches the GLOBAL `expect` -- it errors ("expect is not
    // defined") without this, since this config otherwise follows Next.js's
    // own vitest guide, which imports `test`/`expect` explicitly per file
    // rather than relying on globals. Test files still import them
    // explicitly too; this only exists to give jest-dom's runtime matchers
    // somewhere to attach at module-load time.
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
    },
  },
})
