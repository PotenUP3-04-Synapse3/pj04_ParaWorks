import { create } from 'zustand';

type DrawerType =
  | 'decision-detail'
  | 'source-evidence'
  | 'decision-create'
  | 'project-create'
  | null;

interface UIState {
  sidebarOpen: boolean;
  activeDrawer: DrawerType;
  drawerPayload: unknown;
  globalSearchQuery: string;

  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setDrawer: (type: DrawerType, payload?: unknown) => void;
  closeDrawer: () => void;
  setGlobalSearchQuery: (q: string) => void;
}

export const useUIStore = create<UIState>()((set) => ({
  sidebarOpen: true,
  activeDrawer: null,
  drawerPayload: null,
  globalSearchQuery: '',

  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setDrawer: (type, payload = null) => set({ activeDrawer: type, drawerPayload: payload }),
  closeDrawer: () => set({ activeDrawer: null, drawerPayload: null }),
  setGlobalSearchQuery: (q) => set({ globalSearchQuery: q }),
}));
