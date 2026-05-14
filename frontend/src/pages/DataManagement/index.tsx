import { useState } from 'react'
import { Tabs } from 'antd'
import DatasetList from './DatasetList'
import ScriptList from './ScriptList'

export default function DataManagement() {
  const [activeKey, setActiveKey] = useState('datasets')

  return (
    <Tabs
      activeKey={activeKey}
      onChange={setActiveKey}
      items={[
        {
          key: 'datasets',
          label: '数据集管理',
          children: <DatasetList />,
        },
        {
          key: 'scripts',
          label: '脚本管理',
          children: <ScriptList />,
        },
      ]}
    />
  )
}
