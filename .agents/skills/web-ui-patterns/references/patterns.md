# Pattern checklist

**Tokens (CSS custom properties):** `--space-1..5` (4/8/12/16/24px), `--radius`, `--bg`, `--surface`, `--text`, `--muted`, `--accent`, `--ok`, `--err`; system font stack; body 14-16px, one heading step up. Define once, use everywhere.

**Dashboard shell:** CSS grid `grid-template-columns: 220px 1fr`; sidebar `<nav aria-label="Main">` with current item `aria-current="page"`; top bar for title/search/user; below 760px collapse the sidebar into a top row or toggle. KPI cards row (`auto-fit, minmax(160px, 1fr)`) above the main table or chart.

**Table:** real `<table>` with `<th scope="col">`; search input filters rows client-side or via query; sort by clicking header buttons (`aria-sort`); filters as `<select>`; show result count; wrap in `overflow-x:auto` for narrow screens; right-align numbers.

**Form:** every input has a `<label for>`; validate on submit and blur; error text in an element linked by `aria-describedby`, `aria-invalid="true"`; disable submit while pending; show success message and refresh the list from the server; keep entered values on server error.

**Modal:** `<dialog>` with `showModal()` gives focus trap and Esc; return focus to the opener; close button labeled.

**Status messages:** one region `role="status"` (polite) for success/info, `role="alert"` for errors; message names what happened and what to do.

**Async states per region:** loading (text or skeleton, not blank), empty ("No results for 'x'" with clear-filter action), error (message plus retry), disabled, success.

**Responsive:** mobile-first, one breakpoint around 760px, no fixed widths over 100%, `min-width:0` on grid children, tap targets >= 40px.

**Accessibility/keyboard:** semantic elements before ARIA, visible `:focus-visible` outline, logical tab order, contrast >= 4.5:1, no color-only status, `prefers-reduced-motion` respected.

## Plain HTML sketch

```html
<div class="shell"><nav aria-label="Main">...</nav><main>
  <header><h1>Orders</h1><input type="search" aria-label="Search orders"></header>
  <p id="msg" role="status"></p>
  <div class="table-wrap"><table>...</table></div>
</main></div>
```
```js
async function load() {
  setState("loading");
  try {
    const rows = await (await fetch("/api/orders")).json();
    render(rows.filter(matchesFilter)); setState(rows.length ? "ready" : "empty");
  } catch (e) { setState("error", "Could not load orders. Retry?"); }
}
```
