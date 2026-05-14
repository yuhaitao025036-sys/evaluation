import { useState, useEffect } from 'react'
import { Form, Select, Radio, Alert, Button, Space, Divider, message, Card, Descriptions } from 'antd'
import { batchesApi } from '@/api/batches'
import type { Batch, BatchAddTasksRequest, BatchCreateRequest } from '@/types'
import InstanceSelector from './InstanceSelector'

interface Props {
  initialBatchId?: string | null
  onSubmit: (data: BatchCreateRequest) => void
  loading: boolean
  onCancel: () => void
}

export default function AppendBatchForm({ initialBatchId, onSubmit, loading, onCancel }: Props) {
  const [form] = Form.useForm()
  const [batches, setBatches] = useState<Batch[]>([])
  const [selectedBatch, setSelectedBatch] = useState<Batch | null>(null)
  const [overwriteMode, setOverwriteMode] = useState<boolean>(false)

  useEffect(() => {
    fetchBatches()
  }, [])

  useEffect(() => {
    if (initialBatchId && batches.length > 0) {
      const batchId = parseInt(initialBatchId)
      form.setFieldValue('batch_id', batchId)
      handleBatchSelect(batchId)
    }
  }, [initialBatchId, batches])

  const fetchBatches = async () => {
    try {
      const data = await batchesApi.list({ limit: 1000 })
      setBatches(data)
    } catch (error) {
      console.error('获取批次列表失败:', error)
      message.error('获取批次列表失败')
    }
  }

  const handleBatchSelect = async (batchId: number) => {
    try {
      const batch = await batchesApi.get(batchId)
      setSelectedBatch(batch)
    } catch (error) {
      console.error('获取批次详情失败:', error)
      message.error('获取批次详情失败')
    }
  }

  const handleSubmit = async (values: any) => {
    if (!selectedBatch) return

    const data: BatchCreateRequest = {
      batch_name: selectedBatch.batch_name,
      dataset_id: selectedBatch.dataset_id,
      script_id: selectedBatch.script_id,
      model: selectedBatch.model,
      tag: selectedBatch.tag,
      append_to_existing: true,
      overwrite_existing: overwriteMode,
      ...values.instance_selection
    }

    onSubmit(data)
  }

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSubmit}
    >
      <Divider orientation="left">选择目标批次</Divider>

      <Form.Item
        name="batch_id"
        label="目标批次"
        rules={[{ required: true, message: '请选择目标批次' }]}
      >
        <Select
          placeholder="请选择要追加任务的批次"
          showSearch
          optionFilterProp="children"
          onChange={handleBatchSelect}
        >
          {batches.map(batch => (
            <Select.Option key={batch.id} value={batch.id}>
              {batch.batch_name} ({batch.status} - {batch.total_tasks} 个任务)
            </Select.Option>
          ))}
        </Select>
      </Form.Item>

      {selectedBatch && (
        <Card size="small" style={{ marginBottom: 24 }}>
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="批次名称">{selectedBatch.batch_name}</Descriptions.Item>
            <Descriptions.Item label="状态">{selectedBatch.status}</Descriptions.Item>
            <Descriptions.Item label="数据集">
              {selectedBatch.dataset?.name || `#${selectedBatch.dataset_id}`}
            </Descriptions.Item>
            <Descriptions.Item label="脚本">
              {selectedBatch.script?.name || `#${selectedBatch.script_id}`}
            </Descriptions.Item>
            <Descriptions.Item label="模型">{selectedBatch.model}</Descriptions.Item>
            <Descriptions.Item label="标签">{selectedBatch.tag}</Descriptions.Item>
            <Descriptions.Item label="已有实例">{selectedBatch.total_tasks} 个</Descriptions.Item>
            <Descriptions.Item label="并发数">{selectedBatch.max_concurrency}</Descriptions.Item>
          </Descriptions>
          
          <Alert
            message="注意"
            description="追加的实例将使用该批次的配置（模型、标签、脚本）进行评测"
            type="warning"
            showIcon
            style={{ marginTop: 16 }}
          />
        </Card>
      )}

      <Divider orientation="left">选择要追加的数据实例</Divider>

      <Form.Item
        name="instance_selection"
        rules={[{ required: true, message: '请选择数据实例' }]}
      >
        <InstanceSelector datasetId={selectedBatch?.dataset_id || null} />
      </Form.Item>

      <Divider orientation="left">重复处理策略</Divider>

      <Form.Item label="当实例已存在于批次中时">
        <Radio.Group value={overwriteMode} onChange={e => setOverwriteMode(e.target.value)}>
          <Space direction="vertical">
            <Radio value={false}>
              <div>
                <div style={{ fontWeight: 500 }}>跳过已存在的实例（推荐）</div>
                <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>
                  不会重新执行，保留原有结果
                </div>
              </div>
            </Radio>
            <Radio value={true}>
              <div>
                <div style={{ fontWeight: 500 }}>覆盖已存在的实例</div>
                <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>
                  重新执行评测，覆盖原有结果
                </div>
              </div>
            </Radio>
          </Space>
        </Radio.Group>
      </Form.Item>

      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={loading} size="large">
            追加任务
          </Button>
          <Button onClick={onCancel} size="large">
            取消
          </Button>
        </Space>
      </Form.Item>
    </Form>
  )
}
