/**
 * `display.details_mode` / `display.sections.<name>` / `display.show_reasoning`
 * — per-profile visibility for the four detail scaffolds a turn can grow:
 * reasoning ("thinking"), ordinary tool-call rows ("tools"), the subagent
 * roster ("subagents"), and ambient progress meta ("activity").
 *
 * Precedence mirrors the reference resolver the TUI backend already ships
 * (`ui-tui/src/domain/details.ts`, read by every `tui_gateway` client): an
 * explicit `display.sections.<name>` override wins, else a built-in
 * per-section default (thinking/tools default open so a live turn reads like
 * a transcript; activity defaults closed as ambient noise; subagents has no
 * built-in default and falls through), else the global `display.details_mode`.
 * `show_reasoning` is evaluated on top of that: it is the CLI/TUI's long-
 * standing reasoning on/off switch and a profile can set it alone (no
 * `sections` block at all) to turn reasoning off everywhere, so `thinking`
 * resolves hidden whenever EITHER signal says hidden.
 */

import { atom } from 'nanostores'

export type SectionName = 'thinking' | 'tools' | 'subagents' | 'activity'
export type DetailsMode = 'hidden' | 'collapsed' | 'expanded'
export type SectionVisibility = Partial<Record<SectionName, DetailsMode>>

const MODES: readonly DetailsMode[] = ['hidden', 'collapsed', 'expanded']
const SECTION_NAMES: readonly SectionName[] = ['thinking', 'tools', 'subagents', 'activity']

const SECTION_DEFAULTS: SectionVisibility = {
  thinking: 'expanded',
  tools: 'expanded',
  activity: 'hidden'
}

const norm = (v: unknown): string =>
  String(v ?? '')
    .trim()
    .toLowerCase()

const parseDetailsMode = (v: unknown): DetailsMode | null => MODES.find(m => m === norm(v)) ?? null

const isSectionName = (v: unknown): v is SectionName => typeof v === 'string' && SECTION_NAMES.includes(v as SectionName)

const resolveDetailsMode = (v: unknown): DetailsMode => parseDetailsMode(v) ?? 'collapsed'

const resolveSections = (raw: unknown): SectionVisibility =>
  raw && typeof raw === 'object' && !Array.isArray(raw)
    ? (Object.fromEntries(
        Object.entries(raw as Record<string, unknown>)
          .map(([k, v]) => [k, parseDetailsMode(v)] as const)
          .filter((entry): entry is [SectionName, DetailsMode] => !!entry[1] && isSectionName(entry[0]))
      ) as SectionVisibility)
    : {}

const sectionMode = (name: SectionName, globalMode: DetailsMode, sections: SectionVisibility): DetailsMode =>
  sections[name] ?? SECTION_DEFAULTS[name] ?? globalMode

export interface DisplaySectionsVisibility {
  activity: DetailsMode
  subagents: DetailsMode
  thinking: DetailsMode
  tools: DetailsMode
}

const DEFAULT_VISIBILITY: DisplaySectionsVisibility = {
  activity: 'hidden',
  subagents: 'collapsed',
  thinking: 'expanded',
  tools: 'expanded'
}

export const $displaySections = atom<DisplaySectionsVisibility>(DEFAULT_VISIBILITY)

const sameVisibility = (a: DisplaySectionsVisibility, b: DisplaySectionsVisibility): boolean =>
  a.thinking === b.thinking && a.tools === b.tools && a.subagents === b.subagents && a.activity === b.activity

/** Read from the profile-scoped config payload (`getHermesConfig().display`) — never cached across profiles. */
export function setDisplaySectionsFromConfig(
  display: { details_mode?: unknown; sections?: unknown; show_reasoning?: unknown } | null | undefined
): void {
  const globalMode = resolveDetailsMode(display?.details_mode)
  const sections = resolveSections(display?.sections)
  const showReasoning = display?.show_reasoning !== false // default true, matches tui_gateway's server.py fallback

  const next: DisplaySectionsVisibility = {
    activity: sectionMode('activity', globalMode, sections),
    subagents: sectionMode('subagents', globalMode, sections),
    thinking: showReasoning ? sectionMode('thinking', globalMode, sections) : 'hidden',
    tools: sectionMode('tools', globalMode, sections)
  }

  if (!sameVisibility($displaySections.get(), next)) {
    $displaySections.set(next)
  }
}

export const isSectionHidden = (mode: DetailsMode): boolean => mode === 'hidden'
