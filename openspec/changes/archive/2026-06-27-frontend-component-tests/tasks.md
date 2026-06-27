# Tasks — Frontend Component Tests

## 1. Button tests (new file)

- [x] 1.1 Create `frontend/src/components/ui/button.test.tsx`
- [x] 1.2 Test default variant renders with `bg-primary` token
- [x] 1.3 Test destructive variant renders with `bg-destructive` token
- [x] 1.4 Test outline variant renders with `border border-input` token
- [x] 1.5 Test size "sm" / "icon" / "default" apply different height tokens
- [x] 1.6 Test className prop is merged into final button class
- [x] 1.7 Test disabled button does not invoke onClick
- [x] 1.8 Test enabled button invokes onClick exactly once
- [x] 1.9 Test ref is forwarded to the underlying `<button>` element

## 2. HealthPage tests (new file)

- [x] 2.1 Create `frontend/src/pages/HealthPage.test.tsx`
- [x] 2.2 In `beforeEach`, reset `useHealthStore` and `vi.restoreAllMocks()`
- [x] 2.3 Test initial render shows the section heading
- [x] 2.4 Test mount triggers exactly one `apiGet("/health")` call
- [x] 2.5 Test loading state shows "检测中..." button text and is disabled (mock never-resolving promise)
- [x] 2.6 Test ok state shows JSON data in a `<pre>` block
- [x] 2.7 Test error state shows the error message
- [x] 2.8 Test clicking retry button triggers a second `apiGet` call
- [x] 2.9 Test successful response transitions store to ok
- [x] 2.10 Test failed response transitions store to error

## 3. Layout tests (new file)

- [x] 3.1 Create `frontend/src/layouts/Layout.test.tsx` (use `MemoryRouter` + `Routes`)
- [x] 3.2 Test renders 4 NavLinks with correct labels
- [x] 3.3 Test active link is marked with `aria-current="page"`
- [x] 3.4 Test non-matching link does NOT have `aria-current="page"`
- [x] 3.5 Test header title "A 股 ETF 动量策略系统" is rendered
- [x] 3.6 Test child route renders via `<Outlet />`

## 4. Verification

- [x] 4.1 `npx vitest run` → 190 passed (was 165, +25)
- [x] 4.2 `npx tsc --noEmit` → 0 errors
- [x] 4.3 `npx vite build` → OK (596 KB JS, 5.79s)
- [x] 4.4 `git diff --stat` shows only 3 new `.test.tsx` files + openspec artifacts