import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Streamlit nạp component qua iframe trỏ tới thư mục `dist/`, nên `base` phải
 * là "./" để mọi asset dùng đường dẫn tương đối.
 *
 * Toàn bộ dependency (three.js, font, icon) đều được bundle — không có request
 * nào ra CDN, đúng yêu cầu của bài.
 */
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    cors: true,
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false,
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        // Tách three.js ra chunk riêng để phần chat hiển thị trước, scene 3D
        // được nạp sau (lazy) mà không chặn tương tác.
        manualChunks: {
          three: ["three", "@react-three/fiber", "@react-three/drei"],
        },
      },
    },
  },
});
