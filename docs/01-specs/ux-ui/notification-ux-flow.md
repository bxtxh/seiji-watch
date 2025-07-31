# Notification UX Flow Specification

## User Journey Flows

### A. Issue Detail Page Watch Flow

```mermaid
sequenceDiagram
    participant U as User
    participant P as Issue Page
    participant B as Watch Button
    participant M as Confirmation Modal
    participant T as Toast

    U->>P: Visit issue detail page
    P->>B: Render watch button (not watched)
    U->>B: Click "この法案をウォッチする"
    B->>M: Show email input modal
    U->>M: Enter email & confirm
    M->>T: Show success toast
    T->>P: Update button to "ウォッチ中"
```

### B. Header Quick-Watch Flow

```mermaid
sequenceDiagram
    participant U as User
    participant H as Header
    participant S as Search Bar
    participant Q as Quick-Watch Modal
    participant L as Watch List

    U->>H: Click "+" quick-watch icon
    H->>Q: Open quick-watch modal
    Q->>S: Show issue search bar
    U->>S: Type issue keywords
    S->>Q: Show search results
    U->>Q: Click "ウォッチ" on result
    Q->>L: Add to user's watch list
    Q->>Q: Show confirmation animation
```

## Component States

### Watch Button States

```typescript
type WatchButtonState =
  | "not_watching" // Default: "この法案をウォッチする"
  | "loading" // "送信中..."
  | "watching" // "ウォッチ中 ✓" + unwatch option
  | "error"; // "エラーが発生しました" + retry
```

### Modal States

```typescript
type ModalState =
  | "email_input" // Email form
  | "confirming" // "確認メールを送信しています..."
  | "confirmed" // "ウォッチリストに追加されました"
  | "already_exists"; // "既にウォッチ中です"
```

## Accessibility Requirements

### ARIA Implementation

```tsx
<button
  aria-label={isWatching ? "法案のウォッチを停止" : "法案をウォッチする"}
  aria-pressed={isWatching}
  aria-describedby="watch-button-help"
>
  {buttonText}
</button>

<div id="watch-button-help" className="sr-only">
  この法案の進展状況を毎日メールで受け取ります
</div>
```

### Focus Management

```typescript
// Modal open: trap focus within modal
const focusTrap = createFocusTrap("#watch-modal", {
  initialFocus: "#email-input",
  fallbackFocus: "#modal-close-button",
});

// Modal close: return focus to trigger button
onModalClose(() => {
  document.getElementById("watch-button")?.focus();
});
```

### Keyboard Navigation

- **Tab**: Navigate between interactive elements
- **Enter**: Activate watch button or submit form
- **Escape**: Close modal and return focus
- **Arrow Keys**: Navigate search results in quick-watch

## Visual Design Patterns

### Watch Button Design

```css
.watch-button {
  /* Primary state */
  background: var(--primary-green);
  border-radius: 8px;
  padding: 12px 24px;

  /* Watching state */
  &.watching {
    background: var(--success-green);
    border: 2px solid var(--primary-green);
  }

  /* Loading state */
  &.loading {
    opacity: 0.7;
    cursor: not-allowed;
  }
}
```

### Toast Notifications

```typescript
const toastConfig = {
  success: {
    icon: "✓",
    duration: 4000,
    color: "var(--success-green)",
  },
  error: {
    icon: "⚠️",
    duration: 6000,
    color: "var(--error-red)",
  },
};
```

---

**Document Version**: 1.0  
**Created**: 2025-07-13  
**UX Review**: Weekly during implementation
