/**
 * Application entry point
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import './styles/globals.css';

// Get root element
const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Root element not found');
}

// Create React root and render app
createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);
