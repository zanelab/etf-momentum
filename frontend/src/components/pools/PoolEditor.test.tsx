import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { EtfItem } from "@/api/etfs";
import { PoolEditor } from "@/components/pools/PoolEditor";

const SAMPLE_ETFS: EtfItem[] = [
  { code: "510300", name: "沪深300ETF", market: "SH", category: "宽基" },
  { code: "510500", name: "中证500ETF", market: "SH", category: "宽基" },
  { code: "510880", name: "红利ETF", market: "SH", category: "红利" },
];

describe("PoolEditor", () => {
  describe("create mode", () => {
    it("renders the empty form with the create title", () => {
      render(
        <PoolEditor
          mode="create"
          etfs={SAMPLE_ETFS}
          etfsLoading={false}
          etfsError={null}
          submitStatus="idle"
          submitError={null}
          onSave={vi.fn()}
          onCancel={vi.fn()}
        />,
      );
      expect(screen.getByTestId("pool-editor-name")).toHaveValue("");
      expect(screen.getByTestId("pool-editor-save")).toHaveTextContent("创建");
    });

    it("blocks save with empty name and shows the inline error", () => {
      const onSave = vi.fn();
      render(
        <PoolEditor
          mode="create"
          etfs={SAMPLE_ETFS}
          etfsLoading={false}
          etfsError={null}
          submitStatus="idle"
          submitError={null}
          onSave={onSave}
          onCancel={vi.fn()}
        />,
      );
      fireEvent.click(screen.getByTestId("pool-editor-picker-510300"));
      fireEvent.click(screen.getByTestId("pool-editor-save"));

      expect(onSave).not.toHaveBeenCalled();
      expect(screen.getByTestId("pool-editor-error-name")).toHaveTextContent(
        "池名称不能为空",
      );
    });

    it("blocks save with empty pool and shows the inline error", () => {
      const onSave = vi.fn();
      render(
        <PoolEditor
          mode="create"
          etfs={SAMPLE_ETFS}
          etfsLoading={false}
          etfsError={null}
          submitStatus="idle"
          submitError={null}
          onSave={onSave}
          onCancel={vi.fn()}
        />,
      );
      fireEvent.change(screen.getByTestId("pool-editor-name"), {
        target: { value: "宽基核心" },
      });
      fireEvent.click(screen.getByTestId("pool-editor-save"));

      expect(onSave).not.toHaveBeenCalled();
      expect(screen.getByTestId("pool-editor-error-etf_codes")).toHaveTextContent(
        "请至少选择一只 ETF",
      );
    });

    it("submits a trimmed payload when valid", () => {
      const onSave = vi.fn();
      render(
        <PoolEditor
          mode="create"
          etfs={SAMPLE_ETFS}
          etfsLoading={false}
          etfsError={null}
          submitStatus="idle"
          submitError={null}
          onSave={onSave}
          onCancel={vi.fn()}
        />,
      );
      fireEvent.change(screen.getByTestId("pool-editor-name"), {
        target: { value: "  宽基核心  " },
      });
      fireEvent.change(screen.getByTestId("pool-editor-description"), {
        target: { value: "  沪深300+中证500  " },
      });
      fireEvent.click(screen.getByTestId("pool-editor-picker-510300"));
      fireEvent.click(screen.getByTestId("pool-editor-picker-510500"));
      fireEvent.click(screen.getByTestId("pool-editor-save"));

      expect(onSave).toHaveBeenCalledWith({
        name: "宽基核心",
        description: "沪深300+中证500",
        etf_codes: ["510300", "510500"],
      });
    });

    it("sends null description when the field is empty after trim", () => {
      const onSave = vi.fn();
      render(
        <PoolEditor
          mode="create"
          etfs={SAMPLE_ETFS}
          etfsLoading={false}
          etfsError={null}
          submitStatus="idle"
          submitError={null}
          onSave={onSave}
          onCancel={vi.fn()}
        />,
      );
      fireEvent.change(screen.getByTestId("pool-editor-name"), {
        target: { value: "宽基核心" },
      });
      fireEvent.click(screen.getByTestId("pool-editor-picker-510300"));
      fireEvent.click(screen.getByTestId("pool-editor-save"));

      expect(onSave).toHaveBeenCalledWith({
        name: "宽基核心",
        description: null,
        etf_codes: ["510300"],
      });
    });

    it("shows the summary chip when at least one ETF is selected", () => {
      render(
        <PoolEditor
          mode="create"
          etfs={SAMPLE_ETFS}
          etfsLoading={false}
          etfsError={null}
          submitStatus="idle"
          submitError={null}
          onSave={vi.fn()}
          onCancel={vi.fn()}
        />,
      );
      fireEvent.click(screen.getByTestId("pool-editor-picker-510300"));
      fireEvent.click(screen.getByTestId("pool-editor-picker-510500"));

      expect(screen.getByTestId("pool-editor-summary")).toHaveTextContent(
        "将创建包含 2 只 ETF 的策略池",
      );
    });
  });

  describe("edit mode", () => {
    it("prefills name, description, and selection from initial values", () => {
      render(
        <PoolEditor
          mode="edit"
          initialName="宽基核心"
          initialDescription="沪深300+中证500"
          initialCodes={["510300", "510500"]}
          etfs={SAMPLE_ETFS}
          etfsLoading={false}
          etfsError={null}
          submitStatus="idle"
          submitError={null}
          onSave={vi.fn()}
          onCancel={vi.fn()}
        />,
      );
      expect(screen.getByTestId("pool-editor-name")).toHaveValue("宽基核心");
      expect(screen.getByTestId("pool-editor-description")).toHaveValue(
        "沪深300+中证500",
      );
      expect(screen.getByTestId("pool-editor-picker-510300")).toBeChecked();
      expect(screen.getByTestId("pool-editor-picker-510500")).toBeChecked();
      expect(screen.getByTestId("pool-editor-save")).toHaveTextContent("保存");
    });

    it("does not show the diff summary when selection is unchanged", () => {
      render(
        <PoolEditor
          mode="edit"
          initialName="宽基核心"
          initialCodes={["510300", "510500"]}
          etfs={SAMPLE_ETFS}
          etfsLoading={false}
          etfsError={null}
          submitStatus="idle"
          submitError={null}
          onSave={vi.fn()}
          onCancel={vi.fn()}
        />,
      );
      expect(screen.queryByTestId("pool-editor-diff")).not.toBeInTheDocument();
    });

    it("renders the diff summary with added and removed codes", () => {
      render(
        <PoolEditor
          mode="edit"
          initialName="宽基核心"
          initialCodes={["510300", "510500"]}
          etfs={SAMPLE_ETFS}
          etfsLoading={false}
          etfsError={null}
          submitStatus="idle"
          submitError={null}
          onSave={vi.fn()}
          onCancel={vi.fn()}
        />,
      );
      fireEvent.click(screen.getByTestId("pool-editor-picker-510300"));
      fireEvent.click(screen.getByTestId("pool-editor-picker-510880"));

      const diff = screen.getByTestId("pool-editor-diff");
      expect(diff).toHaveTextContent("新增 1 只");
      expect(diff).toHaveTextContent("510880");
      expect(diff).toHaveTextContent("移除 1 只");
      expect(diff).toHaveTextContent("510300");
    });
  });

  describe("formErrors from server", () => {
    it("surfaces a 409 name conflict error under the name field", () => {
      render(
        <PoolEditor
          mode="create"
          etfs={SAMPLE_ETFS}
          etfsLoading={false}
          etfsError={null}
          submitStatus="error"
          submitError="Pool '宽基核心' already exists"
          formErrors={{ name: "Pool '宽基核心' already exists" }}
          onSave={vi.fn()}
          onCancel={vi.fn()}
        />,
      );
      const error = screen.getByTestId("pool-editor-error-name");
      expect(error).toHaveTextContent("already exists");
    });

    it("surfaces a 422 unknown-etf error under the etf_codes field", () => {
      render(
        <PoolEditor
          mode="create"
          etfs={SAMPLE_ETFS}
          etfsLoading={false}
          etfsError={null}
          submitStatus="error"
          submitError="Unknown ETF codes: ['999999']"
          formErrors={{ etf_codes: "Unknown ETF codes: ['999999']" }}
          onSave={vi.fn()}
          onCancel={vi.fn()}
        />,
      );
      const error = screen.getByTestId("pool-editor-error-etf_codes");
      expect(error).toHaveTextContent("999999");
    });
  });

  describe("cancel", () => {
    it("triggers onCancel when the cancel button is clicked", () => {
      const onCancel = vi.fn();
      render(
        <PoolEditor
          mode="create"
          etfs={SAMPLE_ETFS}
          etfsLoading={false}
          etfsError={null}
          submitStatus="idle"
          submitError={null}
          onSave={vi.fn()}
          onCancel={onCancel}
        />,
      );
      fireEvent.click(screen.getByTestId("pool-editor-cancel"));
      expect(onCancel).toHaveBeenCalledTimes(1);
    });
  });
});
