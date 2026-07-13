/**
 * LayoutManager — core page-shell for the REMOTE-AGENTS dashboard.
 *
 * Design token contract (from tailwind.config.js + index.css):
 *   canvas-950 #070A12 | canvas-900 #0B1020 | canvas-800 #101A34
 *   neon-cyan  #22D3EE | neon-amber #F59E0B  | neon-crimson #FB7185
 *   shadow-glass | backdrop-blur-glass (14px)
 *
 * Responsive breakpoints:
 *   mobile  < 768 px  → sidebar hidden (drawer-style, toggled via header button)
 *   desktop ≥ 768 px  → sidebar always visible (fixed left column)
 *
 * ARIA roles:
 *   banner      → global Header
 *   navigation  → Sidebar
 *   main        → Grid Canvas content area
 *   complementary → Sidebar panels
 *
 * Hook for AI skill injection: see `./layoutContext` → `useLayout()`
 */

import { useState, type ReactNode } from 'react'
import { LayoutContext, type WidgetDescriptor } from './layoutContext'

// Re-export so callers can import types from LayoutManager as before.
export type { WidgetDescriptor } from './layoutContext'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Navigation item rendered in the Sidebar. */
export interface NavItem {
  id: string
  label: string
  icon?: ReactNode
  onClick?: () => void
  active?: boolean
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface HeaderProps {
  title?: string
  /** Called on mobile to toggle the sidebar drawer. */
  onMenuToggle: () => void
  sidebarOpen: boolean
}

function Header({ title = 'REMOTE-AGENTS', onMenuToggle, sidebarOpen }: HeaderProps) {
  return (
    <header
      role="banner"
      className="
        fixed left-0 right-0 top-0 z-30 flex h-14 items-center gap-4
        border-b border-white/10 bg-canvas-900/80 px-4 shadow-glass backdrop-blur-glass
      "
    >
      {/* Mobile menu toggle */}
      <button
        type="button"
        aria-label={sidebarOpen ? 'Close navigation' : 'Open navigation'}
        aria-expanded={sidebarOpen}
        aria-controls="sidebar-nav"
        className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-white/70 transition hover:bg-white/10 md:hidden"
        onClick={onMenuToggle}
      >
        <span aria-hidden="true" className="text-lg leading-none">
          {sidebarOpen ? '✕' : '☰'}
        </span>
      </button>

      {/* Brand */}
      <span className="text-sm font-semibold uppercase tracking-widest text-neon-cyan">
        {title}
      </span>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Status badge */}
      <span className="rounded-full border border-neon-cyan/30 bg-neon-cyan/10 px-2.5 py-0.5 text-xs text-neon-cyan">
        Control Plane
      </span>
    </header>
  )
}

// ---------------------------------------------------------------------------

interface SidebarProps {
  navItems?: NavItem[]
  open: boolean
  onClose: () => void
}

function Sidebar({ navItems = [], open, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          aria-hidden="true"
          className="fixed inset-0 z-20 bg-black/60 md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        id="sidebar-nav"
        role="complementary"
        aria-label="Sidebar navigation"
        className={[
          'fixed left-0 top-14 z-20 flex h-[calc(100vh-3.5rem)] w-56 flex-col',
          'border-r border-white/10 bg-canvas-900/90 shadow-glass backdrop-blur-glass',
          'transition-transform duration-200',
          open ? 'translate-x-0' : '-translate-x-full',
          'md:translate-x-0', // always visible on desktop
        ].join(' ')}
      >
        <nav aria-label="Primary navigation" className="flex-1 overflow-y-auto p-3 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={item.onClick}
              aria-current={item.active ? 'page' : undefined}
              className={[
                'flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition',
                item.active
                  ? 'bg-neon-cyan/15 text-neon-cyan'
                  : 'text-white/70 hover:bg-white/5 hover:text-white/90',
              ].join(' ')}
            >
              {item.icon && (
                <span aria-hidden="true" className="h-4 w-4 flex-shrink-0">
                  {item.icon}
                </span>
              )}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        {/* Sidebar footer — system info */}
        <div className="border-t border-white/10 p-3 text-xs text-white/40">
          <div>REMOTE-AGENTS v0</div>
          <div className="mt-0.5">Advisory Control Plane</div>
        </div>
      </aside>
    </>
  )
}

// ---------------------------------------------------------------------------
// Grid Canvas — the main widget surface
// ---------------------------------------------------------------------------

/** Explicit Tailwind col-span classes (JIT requires complete class strings). */
const COL_SPAN: Record<number, string> = {
  1: 'col-span-1', 2: 'col-span-2', 3: 'col-span-3', 4: 'col-span-4',
  5: 'col-span-5', 6: 'col-span-6', 7: 'col-span-7', 8: 'col-span-8',
  9: 'col-span-9', 10: 'col-span-10', 11: 'col-span-11', 12: 'col-span-12',
}

/** Explicit Tailwind row-span classes (JIT requires complete class strings). */
const ROW_SPAN: Record<number, string> = {
  1: 'row-span-1', 2: 'row-span-2', 3: 'row-span-3',
  4: 'row-span-4', 5: 'row-span-5', 6: 'row-span-6',
}

interface GridCanvasProps {
  widgets: WidgetDescriptor[]
}

function GridCanvas({ widgets }: GridCanvasProps) {
  return (
    <div
      role="region"
      aria-label="Dashboard canvas"
      className="
        grid auto-rows-auto grid-cols-12 gap-4
        p-4
      "
    >
      {widgets.map((w) => {
        const colClass = COL_SPAN[w.colSpan ?? 4] ?? 'col-span-4'
        const rowClass = ROW_SPAN[w.rowSpan ?? 1] ?? ''
        return (
          <div
            key={w.id}
            className={[
              colClass,
              rowClass,
              'rounded-2xl border border-white/10 bg-white/5 shadow-glass backdrop-blur-glass',
            ]
              .filter(Boolean)
              .join(' ')}
          >
            {w.component}
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// LayoutManager — top-level export
// ---------------------------------------------------------------------------

export interface LayoutManagerProps {
  /** Page / app title shown in the header. */
  title?: string
  /** Navigation items for the sidebar. */
  navItems?: NavItem[]
  /**
   * Static children rendered inside the main content area, below the widget
   * grid.  Pass AI skill trees here so they can call `useLayout()` to inject
   * widgets dynamically.
   */
  children?: ReactNode
  /** Initial widget set (optional; skills may also inject via `useLayout()`). */
  initialWidgets?: WidgetDescriptor[]
}

/**
 * LayoutManager wraps the full page shell:
 *   - Global sticky Header (role="banner")
 *   - Collapsible Sidebar (role="navigation" / "complementary")
 *   - Dynamic 12-column Grid Canvas (role="main")
 *
 * Children can call `useLayout()` to register or unregister canvas widgets at
 * any time, enabling AI skills to dynamically compose the dashboard surface.
 */
export default function LayoutManager({
  title,
  navItems = [],
  children,
  initialWidgets = [],
}: LayoutManagerProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [widgets, setWidgets] = useState<WidgetDescriptor[]>(initialWidgets)

  const registerWidget = (widget: WidgetDescriptor) => {
    setWidgets((prev) => {
      const filtered = prev.filter((w) => w.id !== widget.id)
      return [...filtered, widget]
    })
  }

  const unregisterWidget = (id: string) => {
    setWidgets((prev) => prev.filter((w) => w.id !== id))
  }

  return (
    <LayoutContext.Provider value={{ registerWidget, unregisterWidget }}>
      {/* Global header */}
      <Header
        title={title}
        onMenuToggle={() => setSidebarOpen((v) => !v)}
        sidebarOpen={sidebarOpen}
      />

      {/* Sidebar */}
      <Sidebar
        navItems={navItems}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main content — offset for header (h-14) + sidebar (w-56 on md+) */}
      <main
        role="main"
        aria-label="Main content"
        className="
          min-h-screen pt-14
          transition-all duration-200
          md:pl-56
        "
      >
        {/* Widget grid canvas */}
        <GridCanvas widgets={widgets} />

        {/* Skill children / static page content */}
        {children && (
          <div className="px-4 pb-8">{children}</div>
        )}
      </main>
    </LayoutContext.Provider>
  )
}
