# UI Components

## BaseCard

`BaseCard` is the shared wrapper for card-style components. It standardizes the card shell, adds a required `header` region that is always visible, and provides built-in collapsed/expanded behavior.

### Key behavior

- Cards **default to collapsed** on initial render.
- Clicking the header toggles between collapsed and expanded states.
- The header is keyboard-accessible (`Enter`/`Space`) and exposes `aria-expanded` + `aria-controls` for screen readers.
- Card content is wrapped with a smooth height/opacity transition and uses `data-state="collapsed|expanded"` for test hooks.
- Interactive elements inside the header (buttons, inputs, labels, etc.) do **not** trigger a collapse toggle.
- Cards can optionally render a drag handle to support drag-and-drop reordering when collapsed.

### Usage

```tsx
<BaseCard
  header={<h3 className="text-lg font-display">Recent tactics</h3>}
  className="p-4"
  contentClassName="pt-3"
>
  <p>Body content goes here.</p>
</BaseCard>
```

### Drag-and-drop ordering

To enable drag-and-drop reordering, pass the drag handle props from your DnD library and a label for accessibility. The drag handle only appears when the card is collapsed.

```tsx
<BaseCard
  header={<h3 className="text-lg font-display">Practice queue</h3>}
  dragHandleProps={dragHandleProps}
  dragHandleLabel="Reorder practice queue"
  onCollapsedChange={setIsCollapsed}
>
  <p>Body content goes here.</p>
</BaseCard>
```

### Existing card components

All card-like components in `client/src/_components` now compose `BaseCard` so they inherit the same collapsed behavior and accessibility defaults.
