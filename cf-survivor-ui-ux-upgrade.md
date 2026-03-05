# CF Survivor Pool — UI/UX Upgrade Handoff

## 1. Context

CF Survivor Pool is a college football survivor pool web app serving ~26 participants. The frontend is server-rendered Jinja2 templates with Bootstrap 5.3.3 CDN, a single `static/css/style.css`, and no build step. The site works. The design does leaves much to be desired.

Right now the app looks like a Bootstrap scaffold with some gradient accents bolted on. There is no visual identity. Nothing says "college football." Nothing says "survive or die each week" The CSS is a flat list of component-specific rules with no design system, no custom properties, no type hierarchy, and no mobile-first intent. The pick submission flow uses a `<select>` dropdown. The standings page is a plain striped table. The championship banner has floating emoji animations.

This task is a design-forward upgrade with real UX improvement authority. It is not a CSS polish pass. The site should come out of this looking like it was built for college football by someone who cares — memorable, intense, competition-forward. Claude Code and its plugins/skills has full creative latitude on aesthetic direction. Python files, route logic, and template structure are all fair game during off-season if a UX improvement genuinely requires it.

**"Done" looks like:** A participant opens the site on their phone Saturday morning, finds their team in three taps, and thinks "this looks legit." The standings page makes eliminated players wince and surviving players feel something. The whole thing has a visual identity you could describe and feel.

---

## 2. Skills to Activate (Do This First)

Before reading ANY project files, load and internalize these skills:

```
view /mnt/skills/public/frontend-design/SKILL.md
```

Read every word. This skill demands bold, intentional design: distinctive typography, purposeful color, spatial composition, atmospheric backgrounds, and zero generic Bootstrap output. It is the authority on every aesthetic decision and code update you make during this task. If the `frontend-design` skill says one thing and your instinct says another, the skill wins.

Then activate `superpowers` for thorough multi-file analysis and high-quality implementation across the full template set.

These skills are the reason this task is running through Claude Code. If the output could have been produced without them, the task has failed.

---

## 3. Audit Phase — Plan Mode On

**Do not write any code until Brad approves the plan.**

Start by reading every frontend file in the project. Here is what exists:

**CSS:**
- `static/css/style.css` — single stylesheet, ~300+ lines, no CSS custom properties, no design tokens

**Templates:**
- `templates/base.html` — shell: Bootstrap CDN, `bg-dark` navbar, plain footer, flash messages, `{% block content/head/scripts %}`
- `templates/index.html` — standings page (most important page). Has: current week alert, active players table, eliminated players table, championship banner with emoji animations, champion journey timeline
- `templates/pick.html` — pick submission. Uses `<select>` dropdown for team selection, game cards in a grid, locked pick display
- `templates/my_picks.html` — personal pick history. Stats cards row, regular season table, playoff section, used teams by conference accordion, conference championship tracker
- `templates/weekly_results.html` — week results. Summary cards (correct/incorrect/pending counts), eliminations alert, full picks table with color-coded rows, week navigation
- `templates/login.html` — centered card, basic form
- `templates/register.html` — centered card, form with validation hints
- `templates/change_password.html` — centered card, three password fields
- `templates/errors/404.html` — display-1 number, text, back button
- `templates/errors/500.html` — same pattern
- `templates/admin/` — dashboard, create_week, manage_games, mark_results, users (light-touch only)

**Routes serving these templates:**
- `routes/main.py` — `index()`, `make_pick()`, `my_picks()`, `weekly_results()`
- `routes/auth.py` — `login()`, `register()`, `change_password()`
- `routes/admin.py` — all admin views

Read all of these files completely. Then produce a written audit covering:

1. **Color palette** — what's actually in use (hex values, Bootstrap classes, inline gradient definitions)
2. **Typography** — fonts loaded (currently: none custom, system Bootstrap defaults), type hierarchy, heading treatment
3. **Layout patterns** — container widths, grid usage, card vs table patterns, how content is structured
4. **Mobile strategy** — what currently happens on small screens (spoiler: `table-responsive` wrapper and hope)
5. **Component reuse** — what's repeated across templates, what's inconsistent
6. **Data display quality** — for each core surface (standings, picks, results, pick history): what's cluttered, what's hard to scan, what works
7. **Mobile pain points** — specific elements that break or degrade below 768px
8. **UX flow assessment:**
   - Pick submission: user lands on `/pick/<week>` → sees `<select>` dropdown with team names and spreads → submits form → redirect to standings. No visual feedback on what the spread means. No game context visible while choosing. Dropdown is not scannable.
   - Results display: user lands on `/weekly_results` → summary cards → full table with colored rows. Table is dense. On mobile, requires horizontal scroll. No quick way to find "what happened to my pick."
9. **Brand identity** — what currently communicates "college football," "survivor," "competition"? Assess honestly. (The answer is: almost nothing. `bg-dark` navbar, emoji in card headers, a purple gradient championship banner.)

---

## 4. Design Direction Decision — Plan Mode, Checkpoint

Based on the audit and the `frontend-design` skill, commit to a specific aesthetic direction. Present it to Brad for approval before writing any code.

Required decisions:

### A. Name the Aesthetic
Give it a clear label that communicates the vibe. Not a committee name. Something specific: "Press Box at Night," "Rivalry Saturday," "The Jumbotron," etc. The name should immediately tell you what the design feels like. Brad went to University of Wisconsin-Madison, and has said the Wisonsin Badgers could potentially be a starting point, but gives full creative permission to Claude code and its front end skill.

### B. Color Palette (as CSS custom properties)
Define at minimum:
```css
:root {
  /* Core */
  --color-primary: ...;
  --color-secondary: ...;
  --color-accent: ...;        /* CTA / high-attention */

  /* Backgrounds */
  --bg-body: ...;
  --bg-surface: ...;          /* cards, panels */
  --bg-surface-alt: ...;      /* alternating rows, secondary panels */
  --bg-nav: ...;

  /* Text */
  --text-primary: ...;
  --text-secondary: ...;
  --text-muted: ...;

  /* Status */
  --status-alive: ...;        /* active players, correct picks */
  --status-eliminated: ...;   /* eliminated, incorrect picks */
  --status-pending: ...;      /* unresolved, in progress */
  --status-warning: ...;      /* deadline approaching, auto-pick */

  /* Data emphasis */
  --spread-favorite: ...;     /* negative spread */
  --spread-underdog: ...;     /* positive spread */

  /* Spacing, radius, shadows as needed */
}
```

### C. Typography Pairing
- Display font (headings, hero text, brand name) — from Google Fonts CDN
- Body/data font (tables, form labels, body text) — from Google Fonts CDN
- Rationale: why this pairing fits the aesthetic and serves data-heavy pages

### D. Signature Element
One memorable design detail that makes this feel purpose-built for a college football survivor pool. Not a logo. A structural or visual element that recurs and anchors the identity. Examples: a yard-line stripe motif, a scoreboard-style number treatment, a "down and distance" progress metaphor for lives remaining. Pick one. Commit to it.

### E. What It Will NOT Do
Explicit constraints to prevent generic output:
- Will not use Bootstrap's default `bg-dark` / `bg-primary` / `bg-success` colors unmodified
- Will not use `table-striped` as the default table treatment
- Will not produce purple/pink gradients
- Will not look like it could be any sport or generic site

Present the full audit + design direction to Brad for approval. Wait for go-ahead.

---

## 5. UX Flow Assessment & Recommendations

Evaluate these two flows and propose specific improvements. If any require Python/route changes, flag them clearly with rationale.

### Pick Submission Flow (highest-traffic interaction)

**Current state:** `/pick/<week>` renders a `<select>` dropdown containing eligible team names with spread in parentheses. Below it: a grid of game cards showing matchups. The dropdown and the game cards are disconnected — you pick from the dropdown but see context in the cards. On mobile the cards stack but the dropdown is still the interaction point.

**Evaluate:**
- Should team selection be the cards themselves (click/tap a team card to select) instead of a dropdown? This would unify browsing and picking into one gesture.
- How should ineligible teams (already used, over spread cap, game started) be communicated? Currently they're just absent from the dropdown — the user doesn't see what they *can't* pick or why.
- Is the game time / spread / opponent info scannable enough during selection?
- What's the ideal mobile pick submission experience? Think: Saturday morning, phone in one hand, coffee in the other, three taps max.
- **Hard constraint from Brad: no modals or popups for pick submission.** Inline confirmation or similar. His users dislike too many clicks and windows.

### Results Display Flow

**Current state:** `/weekly_results` shows summary stat cards (correct/incorrect/pending counts), an eliminations alert if anyone died, and a full table of every player's pick with color-coded rows (green for correct, red for incorrect).

**Evaluate:**
- Can a user quickly find their own result? (Currently: scan a dense table.)
- Is the "who survived, who died" story told at a glance?
- Are live/in-progress game states communicated? (The `pending` badge exists but it's just a yellow card.)
- Would a "your pick" highlighted section at the top improve the experience?
- On mobile: the table requires horizontal scroll. Cards would be better. What should the card contain?

Propose specific improvements. Flag any Python/route changes required.

---

## 6. Implementation Scope

Once Brad approves direction and plan, upgrade these files.

### Foundation Layer

**`static/css/style.css`** — Full rewrite.
- All design tokens as CSS custom properties at `:root`
- Mobile-first media queries (styles default to mobile, scale up)
- No dead CSS from the old design
- Bootstrap overrides organized at the top, custom components below
- Consistent naming convention for custom classes

**`templates/base.html`** — Structural upgrade.
- Google Fonts CDN link in `<head>`
- Redesigned `<nav>` — brand identity visible, active page indication, mobile hamburger that feels intentional (not default Bootstrap collapse)
- Redesigned `<footer>` — matches new identity
- Flash message styling that matches the design language
- All `{% block %}` patterns must remain intact: `title`, `head`, `content`, `scripts`
- Meta viewport tag stays as-is

### Core Data Surfaces (highest priority — do these first)

**`templates/index.html`** — Standings page. This IS the product.
- Standings table is the centerpiece: rank, player name, lives, cumulative spread, current week pick
- Lives remaining needs a visual treatment (not just a number) — consider icons, pips, a visual metaphor
- Eliminated vs active must be instantly distinguishable
- Current week pick column: show team name + spread, with visual indicator for locked/pending/no pick
- Desktop: proper table. Mobile: card-based rendering (dual-render pattern with `d-none d-md-block` / `d-md-none`)
- Championship banner (if season is complete)
- Current week info block: deadline, user's pick status, CTA to make/change pick

**`templates/weekly_results.html`** — Second most viewed page.
- Summary stats: keep but redesign (not Bootstrap card grid)
- Eliminations callout: make it dramatic. Someone died. Make it feel like it.
- Results: consider "your pick" highlighted at top (may require minor Python change to pass `current_user_pick` separately — flag this)
- Desktop: table. Mobile: cards.
- Color coding: correct/incorrect/pending should use the design system's status colors, not Bootstrap contextual classes

**`templates/pick.html`** — Highest-traffic interaction.
- Replace `<select>` dropdown with tappable team cards (if approved in UX assessment)
- Each card shows: team name, opponent, spread, game time, conference
- Ineligible teams shown but visually disabled with reason (used, over cap, game started)
- Current pick highlighted distinctly
- Submit/update via card tap + inline confirmation (no modal)
- Mobile: single column of team cards, generous touch targets (min 44px), primary action always visible
- **If switching from dropdown to cards:** the `<form>` still needs to POST a `team_id`. Use a hidden input updated by JS on card selection, or individual form-per-card with submit buttons. Keep CSRF token.
- Game schedule section below pick interface: clean, scannable, shows all week's games with times and spreads

### Supporting Pages

**`templates/my_picks.html`** — Season record.
- Stats cards: align to new design
- Pick history table: status badges using design system
- Used teams section: cleaner than current accordion-per-conference (consider a simple grid or tag cloud)
- Conference championship tracker: if it stays, make it match

**`templates/login.html`** and **`templates/register.html`** — First impressions.
- Match new design language
- Welcoming, not corporate
- The brand should be visible even on the login page
- Form styling: inputs, buttons, links all use design tokens

**`templates/change_password.html`** — Match styling, minimal effort.

**`templates/errors/404.html`** and **`templates/errors/500.html`** — Brief polish.
- Match new visual identity
- Replace generic Bootstrap display text with something that has personality

### Admin Templates (light-touch only)

- `templates/admin/dashboard.html`
- `templates/admin/create_week.html`
- `templates/admin/manage_games.html`
- `templates/admin/mark_results.html`
- `templates/admin/users.html`

Align to new palette and card/table styling only. Do not redesign admin layouts. Brad is the only admin user and functionality matters more than aesthetics here.

---

## 7. Mobile-Specific Directives

- **Nav hamburger:** Smooth collapse animation, active page clearly indicated in both collapsed and expanded states. The expanded mobile nav should feel like a designed element, not a dropdown that happened.
- **Data tables:** No horizontal scroll on any page at any screen size. Use the dual-render pattern: `<table>` for desktop (`d-none d-md-block`), cards for mobile (`d-md-none`). Improve the card designs — they should feel like first-class citizens, not table-row refugees.
- **Pick submission:** The pick interface must be the dominant element on mobile. Touch targets minimum 44px height. No modals. The team you're about to pick should be unmistakable. Users that need to submit a pick should always clearly know they need to submit a pick and easily be able to navigate to pick submission.
- **Standings on mobile:** Rank, name, lives, and status must be scannable at a glance. Don't cram desktop column density onto a phone. Cumulative spread can be secondary info (tap to expand, or smaller text).
- **Vertical spacing:** Generous padding between cards and sections on mobile. Content should breathe.
- **Font sizing:** Body text ≥ 16px on mobile (prevents iOS zoom on input focus). Data in tables/cards can be smaller but never below 13px.

---

## 8. Constraints

- **Python files:** May be modified if a UX improvement requires it. Brad must be informed of any `.py` changes before they are made, with clear rationale. Common expected changes:
  - `routes/main.py` — might need to pass `current_user_pick` separately to `weekly_results` template
  - `routes/main.py` — might restructure `make_pick` context to support card-based selection
  - No new routes without justification
- **No new Python dependencies** without explicit Brad approval
- **No JavaScript build step** — vanilla JS or CDN-loaded libraries only. Minimal JS preferred.
- **Bootstrap 5.3.3 CDN stays** — override and extend aggressively via custom properties and specificity, but do not remove the CDN link. The grid system, utility classes, and JS components (collapse, dismiss) are still useful.
- **Jinja2 template logic:** Change only when necessary for UX improvements. Every change to `{% if %}`, `{% for %}`, `{{ variable }}`, `url_for()` calls must be intentional and noted in the plan. Do not break existing conditional logic (playoff detection, elimination checks, pick locking, deadline checks).
- **External fonts:** Google Fonts CDN is allowed and expected.
- **CSRF protection:** Every `<form>` must include `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>`. Do not remove or forget these.
- **Rate limiting, auth, admin patterns:** Do not break `@login_required`, `@admin_required`, `@limiter.limit` decorators or their behavior.
- **Context processor helpers:** These are globally available in all templates and must continue to work: `get_week_display_name()`, `get_week_short_label()`, `is_week_playoff()`, `format_deadline()`, `to_pool_time()`, `get_current_time()`, `timezone`, `entry_fee`

---

## 9. Verification Criteria

The task is complete when:

- [ ] Written audit produced covering all frontend files, with honest assessment of current state
- [ ] UX flow assessment completed for pick submission and results display, with specific proposals
- [ ] Design direction named, color palette defined as CSS custom properties, typography chosen, signature element identified
- [ ] Brad has approved the plan before any implementation began
- [ ] `style.css` is rewritten with CSS custom properties, mobile-first structure, no dead CSS, no leftover old styles
- [ ] `base.html` loads chosen Google Fonts, has redesigned nav with active states, redesigned footer
- [ ] Standings page (`index.html`) is the visual highlight — standings table is the centerpiece, lives are visual, mobile cards work
- [ ] Pick submission (`pick.html`) works without modals, has comfortable mobile touch targets, team selection is scannable
- [ ] Results display (`weekly_results.html`) clearly communicates who survived and who was eliminated, works on mobile without horizontal scroll
- [ ] My picks (`my_picks.html`) matches new design, stats and history are clean
- [ ] Login/register pages match new identity
- [ ] Error pages have personality
- [ ] Admin templates have palette alignment (light-touch)
- [ ] No horizontal scroll on any page at any viewport width
- [ ] All `{% block %}` patterns in `base.html` still work
- [ ] All CSRF tokens present in all forms
- [ ] All `url_for()` calls resolve correctly
- [ ] All Jinja2 template variables and conditionals still function
- [ ] Any Python file changes were flagged, explained, and approved before implementation
- [ ] The site looks like it was designed for college football, not generated by a template engine

---

## 10. Implementation Workflow

After Brad approves the full plan (audit + design direction + UX recommendations)
This should be done with the help of **frontend-design** and **superpowers**. Any .py file changes should utilize **pyright-lsp** plugin:

### Phase A — Foundation
1. Rewrite `static/css/style.css` with CSS custom properties, design tokens, and base styles
2. Update `templates/base.html` — fonts, nav, footer, flash messages
3. Verify base renders cleanly with existing content

Run `code-review` on `style.css` and `base.html`.

### Phase B — Core Data Surfaces (do in this order)
4. `templates/index.html` — standings page (the crown jewel)
5. `templates/weekly_results.html` — results display
6. `templates/pick.html` — pick submission (may involve the most UX changes)

Run `code-review` after each template.

If any Python changes are needed for these templates, implement them here. Flag each change with a comment: `# UI/UX UPGRADE: [rationale]`

### Phase C — Supporting Pages
7. `templates/my_picks.html`
8. `templates/login.html` + `templates/register.html`
9. `templates/change_password.html`
10. `templates/errors/404.html` + `templates/errors/500.html`

Run `code-review` on the batch.

### Phase D — Polish
11. Admin templates — light palette/card alignment pass
12. Cross-page consistency review — nav active states, spacing, color usage, mobile behavior on every page
13. Run `coderabbit` for holistic multi-file analysis
14. Run `code-simplifier` on `style.css` — find redundancy, consolidate

### Phase E - Claude.md
15. Use **claude-md-management** to review and polish Claude.md.

### Phase F — Commit and Push to GitHub Main
16. Run `commit-commands` with message: `feat: complete UI/UX upgrade — [aesthetic name]`
17. List all files changed and summarize what changed in each for Brad's deploy review

---

## 11. Files That Will Be Modified

**Certain to change:**
- `static/css/style.css` (full rewrite)
- `templates/base.html`
- `templates/index.html`
- `templates/pick.html`
- `templates/my_picks.html`
- `templates/weekly_results.html`
- `templates/login.html`
- `templates/register.html`
- `templates/change_password.html`
- `templates/errors/404.html`
- `templates/errors/500.html`

**Likely to change (light-touch):**
- `templates/admin/dashboard.html`
- `templates/admin/create_week.html`
- `templates/admin/manage_games.html`
- `templates/admin/mark_results.html`
- `templates/admin/users.html`

**May change (if UX improvements require it — flag before editing):**
- `routes/main.py`

**Should not change (unless something unexpected surfaces):**
- `models.py`
- `extensions.py`
- `config.py`
- `app.py`
- `routes/auth.py`
- `routes/admin.py`
- `services/*`
- `timezone_utils.py`
- `display_utils.py`
