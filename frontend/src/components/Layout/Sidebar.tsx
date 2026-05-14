import { Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  DatabaseOutlined,
  AppstoreOutlined,
  PlusCircleOutlined,
  BarChartOutlined,
} from '@ant-design/icons'
import type { MenuProps } from 'antd'
import Sider from 'antd/es/layout/Sider'

type MenuItem = Required<MenuProps>['items'][number]

const items: MenuItem[] = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '任务面板',
  },
  {
    key: '/batches',
    icon: <AppstoreOutlined />,
    label: '批次管理',
  },
  {
    key: '/data',
    icon: <DatabaseOutlined />,
    label: '数据管理',
  },
  {
    key: '/batches/create',
    icon: <PlusCircleOutlined />,
    label: '创建批次',
  },
  {
    key: '/comparison',
    icon: <BarChartOutlined />,
    label: '结果对比',
  },
]

export default function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    navigate(key)
  }

  return (
    <Sider width={200} theme="dark">
      <div
        style={{
          height: '32px',
          margin: '16px',
          color: '#fff',
          fontSize: '18px',
          fontWeight: 'bold',
          textAlign: 'center',
        }}
      >
        DUCC 评测系统
      </div>
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        style={{ height: '100%', borderRight: 0 }}
        items={items}
        onClick={handleMenuClick}
        theme="dark"
      />
    </Sider>
  )
}
