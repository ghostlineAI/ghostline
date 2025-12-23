import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  billing_plan_id?: string;
  token_balance: number;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setAuth: (user: User, token: string) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
  updateTokenBalance: (balance: number) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      
      setAuth: (user: User, token: string) => set({
        user,
        token,
        isAuthenticated: true,
        isLoading: false,
      }),
      
      logout: () => set({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      }),
      
      setLoading: (loading: boolean) => set({ isLoading: loading }),
      
      updateTokenBalance: (balance: number) => set((state) => ({
        user: state.user ? { ...state.user, token_balance: balance } : null,
      })),
    }),
    {
      name: 'auth-storage',
      partialize: (state: AuthState) => ({ 
        user: state.user, 
        token: state.token,
        isAuthenticated: state.isAuthenticated 
      }),
    }
  )
); 