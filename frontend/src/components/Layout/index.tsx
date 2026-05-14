import { Layout as AntLayout } from 'antd'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import './index.css'

const { Content } = AntLayout

export default function Layout() {
  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sidebar />
      <AntLayout>
        <Header />
        <Content style={{ margin: '16px' }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
