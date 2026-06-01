import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { App } from './App';
import './index.css';

// Server state lives in TanStack Query. UI state (time range, cohort filter,
// selection) lives in Zustand — see src/store.ts. Keeping the two separate is
// the load-bearing architecture decision (references/18-react-architecture.md).
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Historical panels don't need to refetch on focus; live panels set their
      // own refetchInterval. staleTime keeps navigation cheap.
      staleTime: 15_000,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
