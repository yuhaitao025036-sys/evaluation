import { Layout, Typography } from 'antd'

const { Header: AntHeader } = Layout
const { Text } = Typography

export default function Header() {
  return (
    <AntHeader style={{ background: '#fff', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <div />
      <Text type="secondary">DUCC 代码评测任务管理系统</Text>
    </AntHeader>
  )
}
