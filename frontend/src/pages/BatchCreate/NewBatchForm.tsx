import { useState, useEffect } from 'react'
import { Form, Input, Select, InputNumber, Button, Space, Divider, message } from 'antd'
import { datasetsApi } from '@/api/datasets'
import { scriptsApi } from '@/api/scripts'
import type { Dataset, Script, BatchCreateRequest } from '@/types'
import InstanceSelector from './InstanceSelector'

interface Props {
  onSubmit: (data: BatchCreateRequest) => void
  loading: boolean
  onCancel: () => void
}

export default function NewBatchForm({ onSubmit, loading, onCancel }: Props) {
  const [form] = Form.useForm()
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [scripts, setScripts] = useState<Script[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [datasetsRes, scriptsRes] = await Promise.all([
        datasetsApi.list({ page: 1, page_size: 1000 }),
        scriptsApi.list({ page: 1, page_size: 1000 })
      ])
      setDatasets(datasetsRes.items)
      setScripts(scriptsRes.items)
    } catch (error) {
      console.error('获取数据失败:', error)
      message.error('获取数据失败')
    }
  }

  const handleSubmit = async (values: any) => {
    const data: BatchCreateRequest = {
      batch_name: values.batch_name,
      dataset_id: values.dataset_id,
      script_id: values.script_id,
      model: values.model,
      tag: values.tag,
      max_concurrency: values.max_concurrency || 10,
      max_retries: values.max_retries || 3,
      priority: values.priority || 0,
      ...values.instance_selection,
      append_to_existing: false
    }

    onSubmit(data)
  }

  // 常用模型列表
  const commonModels = [
    'gpt-4-turbo',
    'gpt-4',
    'gpt-3.5-turbo',
    'claude-3.5-sonnet',
    'claude-3-opus',
    'claude-3-sonnet',
    'gemini-1.5-pro',
    'gemini-1.0-pro'
  ]

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSubmit}
      initialValues={{
        max_concurrency: 10,
        max_retries: 3,
        priority: 0
      }}
    >
      <Divider orientation="left">基本信息</Divider>
      
      <Form.Item
        name="batch_name"
        label="批次名称"
        rules={[{ required: true, message: '请输入批次名称' }]}
        extra="建议命名格式：{模型}-{数据集}-{标签}，例如：gpt4-swebench-baseline"
      >
        <Input placeholder="例如：gpt4-swebench-baseline" />
      </Form.Item>

      <Divider orientation="left">评测配置</Divider>

      <Form.Item
        name="dataset_id"
        label="数据集"
        rules={[{ required: true, message: '请选择数据集' }]}
      >
        <Select 
          placeholder="请选择数据集"
          showSearch
          optionFilterProp="children"
          onChange={setSelectedDatasetId}
        >
          {datasets.map(dataset => (
            <Select.Option key={dataset.id} value={dataset.id}>
              {dataset.name}
              {dataset.instance_count && ` (${dataset.instance_count} 个实例)`}
            </Select.Option>
          ))}
        </Select>
      </Form.Item>

      <Form.Item
        name="script_id"
        label="评测脚本"
        rules={[{ required: true, message: '请选择评测脚本' }]}
      >
        <Select placeholder="请选择评测脚本">
          {scripts.map(script => (
            <Select.Option key={script.id} value={script.id}>
              {script.name || script.file_path}
            </Select.Option>
          ))}
        </Select>
      </Form.Item>

      <Form.Item
        name="model"
        label="模型"
        rules={[{ required: true, message: '请输入模型名称' }]}
        extra="选择或输入模型名称，用于结果对比"
      >
        <Select
          placeholder="选择或输入模型名称"
          showSearch
          allowClear
          mode="tags"
          maxCount={1}
        >
          {commonModels.map(model => (
            <Select.Option key={model} value={model}>
              {model}
            </Select.Option>
          ))}
        </Select>
      </Form.Item>

      <Form.Item
        name="tag"
        label="标签"
        rules={[{ required: true, message: '请输入标签' }]}
        extra="用于区分不同的实验，例如：baseline, experiment-1, optimized"
      >
        <Input placeholder="例如：baseline" />
      </Form.Item>

      <Form.Item
        name="max_concurrency"
        label="最大并发数"
        extra="同时运行的任务数量，建议根据系统资源设置"
      >
        <InputNumber min={1} max={100} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item
        name="max_retries"
        label="最大重试次数"
        extra="任务失败后的自动重试次数"
      >
        <InputNumber min={0} max={10} style={{ width: '100%' }} />
      </Form.Item>

      <Divider orientation="left">选择数据实例</Divider>

      <Form.Item
        name="instance_selection"
        rules={[{ required: true, message: '请选择数据实例' }]}
      >
        <InstanceSelector datasetId={selectedDatasetId} />
      </Form.Item>

      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={loading} size="large">
            创建批次
          </Button>
          <Button onClick={onCancel} size="large">
            取消
          </Button>
        </Space>
      </Form.Item>
    </Form>
  )
}
