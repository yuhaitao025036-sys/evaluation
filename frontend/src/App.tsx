import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import DataManagement from './pages/DataManagement'
import BatchList from './pages/BatchList'
import BatchCreate from './pages/BatchCreate'
import TaskCreate from './pages/TaskCreate'
import TaskDetail from './pages/TaskDetail'
import Comparison from './pages/Comparison'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/batches" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="data" element={<DataManagement />} />
          
          {/* 批次管理 (v2.0) */}
          <Route path="batches" element={<BatchList />} />
          <Route path="batches/create" element={<BatchCreate />} />
          <Route path="batches/:id" element={<TaskDetail />} /> {/* 暂时复用旧的详情页 */}
          
          {/* 旧路由 (保留兼容) */}
          <Route path="task/create" element={<TaskCreate />} />
          <Route path="task/:id" element={<TaskDetail />} />
          
          <Route path="comparison" element={<Comparison />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
