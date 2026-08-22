import { useContext } from 'react';
import { AuthContext } from '../components/AuthContext';
import type { AuthContextValue } from '../components/AuthContext';

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth має використовуватись усередині <AuthProvider>');
  }
  return ctx;
}
