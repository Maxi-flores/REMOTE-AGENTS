/**
 * Layout context and hook — imported by LayoutManager and AI skill components.
 * Kept in a separate file so LayoutManager.tsx can export only components.
 */

import { createContext, useContext, type ReactNode } from 'react'

/** A single widget slot that AI skills can inject into the canvas grid. */
export interface WidgetDescriptor {
  /** Unique key — used as React key and for deduplication. */
  id: string
  /** Column span on the 12-column desktop grid (1–12). Defaults to 4. */
  colSpan?: number
  /** Row span. Defaults to 1. */
  rowSpan?: number
  /** The component to render inside the slot. */
  component: ReactNode
}

export interface LayoutContextValue {
  /** Register a widget into the canvas grid. Replaces any existing widget with the same id. */
  registerWidget: (widget: WidgetDescriptor) => void
  /** Remove a widget by id. */
  unregisterWidget: (id: string) => void
}

export const LayoutContext = createContext<LayoutContextValue | null>(null)

/** Hook for AI skill components to inject / remove canvas widgets. */
export function useLayout(): LayoutContextValue {
  const ctx = useContext(LayoutContext)
  if (!ctx) {
    throw new Error('useLayout must be used inside a LayoutManager')
  }
  return ctx
}
