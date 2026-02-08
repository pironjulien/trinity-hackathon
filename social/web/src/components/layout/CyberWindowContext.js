import { createContext, useContext } from 'react';

// SOTA 2026: CyberWindow Context for Child-Parent Communication (Interceptors)
export const CyberWindowContext = createContext({
    // Method to register a "before close" check
    // Callback should return TRUE to BLOCK closing (or handle confirmation internally)
    registerInterceptor: (callback) => () => { },
});

export const useCyberWindow = () => useContext(CyberWindowContext);
