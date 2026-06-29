import "@testing-library/jest-dom/vitest";

// jsdom does not implement ResizeObserver. recharts' ResponsiveContainer requires it.
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}