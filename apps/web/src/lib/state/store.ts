import { create } from "zustand";

interface EditorState {
  zoom: number;
  selectedPage: number;
  setZoom: (zoom: number) => void;
  setSelectedPage: (page: number) => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  zoom: 1.0,
  selectedPage: 1,
  setZoom: (zoom) => set({ zoom }),
  setSelectedPage: (page) => set({ selectedPage: page }),
}));
