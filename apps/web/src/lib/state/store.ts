import { create } from "zustand";

import type {
  HitTestCandidate,
  IRPage,
  PatchOp,
  PatchsetRecord,
  PatchsetInput
} from "@/lib/api";
import { commitPatch, getCompositeIR, getIR, getPatches, planPatch, revertLastPatch } from "@/lib/api";

type PatchVisibility = Record<string, boolean>;

interface SelectionState {
  irPages: Record<number, IRPage>;
  basePages: Record<number, IRPage>;
  selectedId: string | null;
  hoveredId: string | null;
  candidates: HitTestCandidate[];
  activeCandidateIndex: number;
  activePageIndex: number | null;
  patchsets: PatchsetRecord[];
  pendingProposal: {
    patchset_id: string;
    ops: PatchOp[];
    rationale_short: string;
    page_index: number;
  } | null;
  patchVisibility: PatchVisibility;
  setIRPage: (pageIndex: number, page: IRPage) => void;
  setBasePage: (pageIndex: number, page: IRPage) => void;
  setHoveredId: (id: string | null) => void;
  setCandidates: (pageIndex: number, candidates: HitTestCandidate[]) => void;
  cycleCandidate: () => void;
  clearSelection: () => void;
  setPatchsets: (patchsets: PatchsetRecord[]) => void;
  loadPatchsets: (docId: string) => Promise<void>;
  togglePatchVisibility: (docId: string, pageIndex: number, patchsetId: string) => Promise<void>;
  proposePatch: (docId: string, instruction: string) => Promise<void>;
  clearProposal: () => void;
  applyProposal: (docId: string) => Promise<void>;
  commitManualPatch: (docId: string, patchset: PatchsetInput) => Promise<void>;
  refreshComposite: (docId: string, pageIndex: number) => Promise<void>;
  undoLastPatch: (docId: string) => Promise<void>;
  previewComposite: (docId: string, pageIndex: number) => Promise<void>;
}

const applyPatchsets = (
  basePage: IRPage,
  patchsets: PatchsetRecord[],
  visibility: PatchVisibility,
  pageIndex: number
): IRPage => {
  const composite = structuredClone(basePage);
  const primitiveMap = new Map(composite.primitives.map((primitive) => [primitive.id, primitive]));

  patchsets
    .filter((patchset) => patchset.page_index === pageIndex)
    .filter((patchset) => visibility[patchset.patchset_id] !== false)
    .forEach((patchset) => {
      const resultsById = new Map(patchset.results.map((result) => [result.target_id, result]));
      patchset.ops.forEach((op) => {
        const target = primitiveMap.get(op.target_id);
        if (!target) {
          return;
        }
        if (op.op === "set_style" && target.kind === "path") {
          if (op.stroke_color !== undefined) {
            target.style.stroke_color = op.stroke_color;
          }
          if (op.stroke_width_pt !== undefined) {
            target.style.stroke_width = op.stroke_width_pt;
          }
          if (op.fill_color !== undefined) {
            target.style.fill_color = op.fill_color;
          }
          if (op.opacity !== undefined) {
            target.style.opacity = op.opacity;
          }
        }
        if (op.op === "replace_text" && target.kind === "text") {
          target.text = op.new_text;
          const result = resultsById.get(op.target_id);
          if (result?.applied_font_size_pt) {
            target.style.size = result.applied_font_size_pt;
          }
          if (result?.overflow !== undefined) {
            target.patch_meta = {
              overflow: result.overflow
            };
          }
        }
      });
    });

  return composite;
};

export const useSelectionStore = create<SelectionState>((set, get) => ({
  irPages: {},
  basePages: {},
  selectedId: null,
  hoveredId: null,
  candidates: [],
  activeCandidateIndex: 0,
  activePageIndex: null,
  patchsets: [],
  pendingProposal: null,
  patchVisibility: {},
  setIRPage: (pageIndex, page) =>
    set((state) => ({
      irPages: {
        ...state.irPages,
        [pageIndex]: page
      }
    })),
  setBasePage: (pageIndex, page) =>
    set((state) => ({
      basePages: {
        ...state.basePages,
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
    }),
  setPatchsets: (patchsets) =>
    set(() => ({
      patchsets,
      patchVisibility: patchsets.reduce<PatchVisibility>((acc, patchset) => {
        acc[patchset.patchset_id] = true;
        return acc;
      }, {})
    })),
  loadPatchsets: async (docId) => {
    const response = await getPatches(docId);
    set((state) => {
      const nextVisibility = { ...state.patchVisibility };
      response.patchsets.forEach((patchset) => {
        if (!(patchset.patchset_id in nextVisibility)) {
          nextVisibility[patchset.patchset_id] = true;
        }
      });
      return {
        patchsets: response.patchsets,
        patchVisibility: nextVisibility
      };
    });
  },
  togglePatchVisibility: async (docId, pageIndex, patchsetId) => {
    set((state) => ({
      patchVisibility: {
        ...state.patchVisibility,
        [patchsetId]: !state.patchVisibility[patchsetId]
      }
    }));
    await get().previewComposite(docId, pageIndex);
  },
  proposePatch: async (docId, instruction) => {
    const { selectedId, activePageIndex } = get();
    if (!selectedId || activePageIndex === null) {
      throw new Error("Select a primitive first");
    }
    const response = await planPatch({
      doc_id: docId,
      page_index: activePageIndex,
      selected_ids: [selectedId],
      user_instruction: instruction
    });
    set({ pendingProposal: response.proposed_patchset });
  },
  clearProposal: () => set({ pendingProposal: null }),
  applyProposal: async (docId) => {
    const { pendingProposal } = get();
    if (!pendingProposal) {
      return;
    }
    await commitPatch(docId, {
      ops: pendingProposal.ops,
      page_index: pendingProposal.page_index,
      selected_ids: pendingProposal.ops.map((op) => op.target_id),
      rationale_short: pendingProposal.rationale_short
    });
    set({ pendingProposal: null });
    await get().loadPatchsets(docId);
    await get().previewComposite(docId, pendingProposal.page_index);
  },
  commitManualPatch: async (docId, patchset) => {
    await commitPatch(docId, patchset);
    await get().loadPatchsets(docId);
    await get().previewComposite(docId, patchset.page_index);
  },
  refreshComposite: async (docId, pageIndex) => {
    const page = await getCompositeIR(docId, pageIndex);
    set((state) => ({
      irPages: {
        ...state.irPages,
        [pageIndex]: page
      }
    }));
  },
  undoLastPatch: async (docId) => {
    await revertLastPatch(docId);
    await get().loadPatchsets(docId);
    const { activePageIndex } = get();
    if (activePageIndex !== null) {
      await get().previewComposite(docId, activePageIndex);
    }
  },
  previewComposite: async (docId, pageIndex) => {
    const basePage = await getIR(docId, pageIndex);
    const { patchsets, patchVisibility } = get();
    const composite = applyPatchsets(basePage, patchsets, patchVisibility, pageIndex);
    set((state) => ({
      basePages: {
        ...state.basePages,
        [pageIndex]: basePage
      },
      irPages: {
        ...state.irPages,
        [pageIndex]: composite
      }
    }));
  }
}));
