/**
 * Application router configuration
 * Uses React Router with lazy loading for code splitting
 */

import { createBrowserRouter, Navigate } from 'react-router-dom';
import { MainLayout } from '@/components/layout';
import {
  DashboardPage,
  RequirementInputPage,
  ProjectVisualizationPage,
  DocumentViewerPage,
} from '@/pages';

/**
 * Router configuration
 */
export const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: 'dashboard',
        element: <Navigate to="/" replace />,
      },
      {
        path: 'new',
        element: <RequirementInputPage />,
      },
      {
        path: 'sessions/:sessionId',
        element: <ProjectVisualizationPage />,
      },
      {
        path: 'sessions/:sessionId/documents',
        element: <DocumentViewerPage />,
      },
      {
        path: 'sessions/:sessionId/documents/:artifactId',
        element: <DocumentViewerPage />,
      },
      {
        path: 'sessions',
        element: <DashboardPage />,
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);

export default router;
