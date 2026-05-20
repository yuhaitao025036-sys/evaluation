import { useState } from 'react'
import { Tabs } from 'antd'
import BatchComparison from './BatchComparison'
import ModelComparison from './ModelComparison'
import TagComparison from './TagComparison'
import InstanceComparison from './InstanceComparison'

export default function Comparison() {
  const [activeKey, setActiveKey] = useState('batches')

  return (
    <div style={{ padding: 24 }}>
      <Tabs
        activeKey={activeKey}
        onChange={setActiveKey}
        items={[
          {
            key: 'batches',
            label: '批次对比',
            children: <BatchComparison />,
          },
          {
            key: 'models',
            label: '模型对比',
            children: <ModelComparison />,
          },
          {
            key: 'tags',
            label: '标签对比',
            children: <TagComparison />,
          },
          {
            key: 'instance',
            label: '实例对比',
            children: <InstanceComparison />,
          },
        ]}
      />
    </div>
  )
}
