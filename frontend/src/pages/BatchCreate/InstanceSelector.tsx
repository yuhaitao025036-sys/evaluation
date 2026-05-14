import { useState, useEffect } from 'react'
import { Radio, Input, InputNumber, Space, Card, message } from 'antd'
import { datasetsApi } from '@/api/datasets'
import type { RadioChangeEvent } from 'antd'

interface Props {
  datasetId: number | null
  value?: any
  onChange?: (value: any) => void
}

type SelectionMode = 'all' | 'range' | 'ids' | 'filter'

export default function InstanceSelector({ datasetId, value, onChange }: Props) {
  const [mode, setMode] = useState<SelectionMode>('all')
  const [startIndex, setStartIndex] = useState<number>(0)
  const [endIndex, setEndIndex] = useState<number>(100)
  const [instanceIds, setInstanceIds] = useState<string>('')
  const [totalInstances, setTotalInstances] = useState<number>(0)

  useEffect(() => {
    if (datasetId) {
      fetchDatasetInfo(datasetId)
    }
  }, [datasetId])

  useEffect(() => {
    updateValue()
  }, [mode, startIndex, endIndex, instanceIds])

  const fetchDatasetInfo = async (id: number) => {
    try {
      const dataset = await datasetsApi.get(id)
      setTotalInstances(dataset.instance_count || 0)
    } catch (error) {
      console.error('获取数据集信息失败:', error)
    }
  }

  const updateValue = () => {
    let result: any = {}

    switch (mode) {
      case 'all':
        // 全部实例 - 不传任何参数，后端会处理
        break
      case 'range':
        result = { start_index: startIndex, end_index: endIndex }
        break
      case 'ids':
        const ids = instanceIds.split(',').map(id => id.trim()).filter(id => id)
        result = { instance_ids: ids }
        break
      case 'filter':
        // 高级筛选暂不实现，可后续扩展
        break
    }

    onChange?.(result)
  }

  const handleModeChange = (e: RadioChangeEvent) => {
    setMode(e.target.value)
  }

  return (
    <Card>
      <Radio.Group value={mode} onChange={handleModeChange} style={{ width: '100%' }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Radio value="all">
            <div>
              <div style={{ fontWeight: 500 }}>全部实例</div>
              {totalInstances > 0 && (
                <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>
                  共 {totalInstances} 个实例
                </div>
              )}
            </div>
          </Radio>

          <Radio value="range">
            <div style={{ display: 'inline-block' }}>
              <div style={{ fontWeight: 500, marginBottom: 8 }}>指定范围</div>
              {mode === 'range' && (
                <Space>
                  <span>从</span>
                  <InputNumber
                    min={0}
                    max={totalInstances - 1}
                    value={startIndex}
                    onChange={v => setStartIndex(v || 0)}
                    style={{ width: 100 }}
                  />
                  <span>到</span>
                  <InputNumber
                    min={startIndex + 1}
                    max={totalInstances}
                    value={endIndex}
                    onChange={v => setEndIndex(v || 100)}
                    style={{ width: 100 }}
                  />
                  <span style={{ color: '#666' }}>
                    (共 {endIndex - startIndex} 个)
                  </span>
                </Space>
              )}
            </div>
          </Radio>

          <Radio value="ids">
            <div style={{ display: 'inline-block', width: '100%' }}>
              <div style={{ fontWeight: 500, marginBottom: 8 }}>指定 ID 列表</div>
              {mode === 'ids' && (
                <Input.TextArea
                  value={instanceIds}
                  onChange={e => setInstanceIds(e.target.value)}
                  placeholder="请输入实例 ID，多个 ID 用逗号分隔&#10;例如：django__django-11099, requests__requests-123"
                  rows={4}
                  style={{ width: 500 }}
                />
              )}
            </div>
          </Radio>
        </Space>
      </Radio.Group>
    </Card>
  )
}
