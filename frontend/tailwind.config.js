/** @type {import('tailwindcss').Config} */
import animate from "tailwindcss-animate";

// OKLCH 调色板来自 spec/design.md § 1，目标态 admin-dashboard (b2b-slate)
// C 任务审计 2026-07-01 → 100 分制得分 61；这次迁移预期 +35 分
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        border: "oklch(var(--border))",
        input: "oklch(var(--input))",
        ring: "oklch(var(--ring))",
        background: "oklch(var(--background))",
        foreground: "oklch(var(--foreground))",
        primary: {
          DEFAULT: "oklch(var(--primary))",
          foreground: "oklch(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "oklch(var(--secondary))",
          foreground: "oklch(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "oklch(var(--destructive))",
          foreground: "oklch(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "oklch(var(--muted))",
          foreground: "oklch(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "oklch(var(--accent))",
          foreground: "oklch(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "oklch(var(--popover))",
          foreground: "oklch(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "oklch(var(--card))",
          foreground: "oklch(var(--card-foreground))",
        },
        // 状态色（admin-dashboard Restrained 承诺度）
        success: "oklch(var(--success))",
        warning: "oklch(var(--warning))",
        info: "oklch(var(--info))",
      },
      // 6 档圆角阶梯：sm=4, md=8, lg=12, xl=16, 2xl=24, 3xl=32, full=9999
      // DEFAULT=8 保留 shadcn 兼容性；rounded-md 双 alias
      borderRadius: {
        none: "0",
        sm: "4px",
        DEFAULT: "8px",
        md: "8px",
        lg: "12px",
        xl: "16px",
        "2xl": "24px",
        "3xl": "32px",
        full: "9999px",
      },
      // 1.25 模数字号阶：12 / 14 / 16 / 20 / 24 / 32 / 40 px
      fontSize: {
        xs: ["0.75rem", { lineHeight: "1.25" }], // 12px
        sm: ["0.875rem", { lineHeight: "1.5" }], // 14px
        base: ["1rem", { lineHeight: "1.5" }], // 16px
        lg: ["1.25rem", { lineHeight: "1.5" }], // 20px (×1.25)
        xl: ["1.5rem", { lineHeight: "1.4" }], // 24px (×1.20, 接近 1.25)
        "2xl": ["2rem", { lineHeight: "1.3" }], // 32px (×1.33)
        "3xl": ["2.5rem", { lineHeight: "1.25" }], // 40px (×1.25)
      },
      // 字号别名：保留 h4/h5/h6 用
      fontFamily: {
        sans: [
          "Noto Sans SC",
          "PingFang SC",
          "Microsoft YaHei",
          "system-ui",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [animate],
};
