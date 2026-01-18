import { create } from "zustand";

import type { HitTestCandidate, IRPage } from "@/lib/api";

interface SelectionState {
  irPages: Record<number, IRPage>;
  selectedId: string | null;
  hoveredId: string | null;
  candidates: HitTestCandidate[];
  activeCandidateIndex: number;
  activePageIndex: number | null;
  setIRPage: (pageIndex: number, page: IRPage) => void;
  setHoveredId: (id: string | null) => void;
  setCandidates: (pageIndex: number, candidates: HitTestCandidate[]) => void;
  cycleCandidate: () => void;
  clearSelection: () => void;
}

export const useSelectionStore = create<SelectionState>((set, get) => ({
  irPages: {},
  selectedId: null,
  hoveredId: null,
  candidates: [],
  activeCandidateIndex: 0,
  activePageIndex: null,
  setIRPage: (pageIndex, page) =>
    set((state) => ({
      irPages: {
        ...state.irPages,
        [pageIndex]: page
      }
    })),
  setHoveredId: (id) => set({ hoveredId: id }),
  setCandidates: (pageIndex, candidates) =>
    set({
      candidates,
      activeCandidateIndex: 0,
      selectedId: candidates[0]?.id ?? null,
      activePageIndex: pageIndex
    }),
  cycleCandidate: () => {
    const { candidates, activeCandidateIndex } = get();
    if (!candidates.length) {
      return;
    }
    const nextIndex = (activeCandidateIndex + 1) % candidates.length;
    set({
      activeCandidateIndex: nextIndex,
      selectedId: candidates[nextIndex]?.id ?? null
    });
  },
  clearSelection: () =>
    set({
      candidates: [],
      activeCandidateIndex: 0,
      selectedId: null,
      activePageIndex: null
    })
}));
