// Definición declarativa de rutas con React Router v6/v7.

import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from '../components/layout/AppLayout.jsx'
import DashboardView from '../views/DashboardView.jsx'
import MinorProcurementView from '../views/MinorProcurementView.jsx'
import BuscadorView from '../views/BuscadorView.jsx'
import TenderDetailView from '../views/TenderDetailView.jsx'
import { AnalyticsView } from '../components/analytics/AnalyticsView.jsx'
import AlertsView from '../components/alerts/AlertsView.jsx'
import ConfigView from '../components/config/ConfigView.jsx'
import NotFoundView from '../views/NotFoundView.jsx'
import ProtectedRoute from '../components/auth/ProtectedRoute.jsx'

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        {/* Redirección raíz a Dashboard */}
        <Route index element={<Navigate to="/dashboard" replace />} />
        
        {/* Rutas principales de la plataforma */}
        <Route path="dashboard" element={<DashboardView />} />
        <Route path="menores" element={<MinorProcurementView />} />
        <Route path="buscador" element={<BuscadorView />} />
        <Route path="licitaciones/:ocid" element={<TenderDetailView />} />
        <Route path="analitica" element={<AnalyticsView />} />

        {/* Rutas privadas: requieren sesión activa (JWT) */}
        <Route element={<ProtectedRoute />}>
          <Route path="alertas" element={<AlertsView />} />
          <Route path="config" element={<ConfigView />} />
        </Route>

        {/* Fallback 404 */}
        <Route path="*" element={<NotFoundView />} />
      </Route>
    </Routes>
  )
}
