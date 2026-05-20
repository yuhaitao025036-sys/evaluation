import { useState, useEffect } from 'react'
import { Card, Form, Input, InputNumber, Select, Button, message, Space } from 'antd'
import { useNavigate } from 'react-router-dom'
import { datasetsApi } from '@/api/datasets'
import { scriptsApi } from '@/api/scripts'
import { modelsApi } from '@/api/models'
import { taskGroupsApi } from '@/api/taskGroups'
import { Dataset, Script } from '@/types'
import JsonEditor from './JsonEditor'

export default function TaskCreate() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [scripts, setScripts] = useState<Script[]>([])
  const [models, setModels] = useState<string[]>([])
  const [filterConditions, setFilterConditions] = useState<Record<string, any> | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [datasetsRes, scriptsRes, modelsRes] = await Promise.all([
        datasetsApi.list({ page: 1, page_size: 1000 }),
        scriptsApi.list({ page: 1, page_size: 1000 }),
        modelsApi.list(),
      ])
      setDatasets(datasetsRes.items)
      setScripts(scriptsRes.items)
      setModels(modelsRes)
    } catch (error) {
      console.error('Failed to fetch data:', error)
    }
  }

  const handleSubmit = async (values: any) => {
    setLoading(true)
    try {
      const data = {
        ...values,
        filter_conditions: filterConditions,
      }
      const res = await taskGroupsApi.create(data)
      message.success('任务创建成功')
      navigate(`/task/${res.id}`)
    } catch (error) {
      console.error('Failed to create task:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="创建评测任务">
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          concurrency: 1,
        }}
      >
        <Form.Item
          name="name"
          label="任务名称"
          rules={[{ required: true, message: '请输入任务名称' }]}
        >
          <Input placeholder="请输入任务名称" />
        </Form.Item>

        <Form.Item name="description" label="任务描述">
          <Input.TextArea rows={3} placeholder="请输入任务描述" />
        </Form.Item>

        <Form.Item
          name="dataset_id"
          label="数据集"
          rules={[{ required: true, message: '请选择数据集' }]}
        >
          <Select placeholder="请选择数据集">
            {datasets.map((dataset) => (
              <Select.Option key={dataset.id} value={dataset.id}>
                {dataset.name}
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
            {scripts.map((script) => (
              <Select.Option key={script.id} value={script.id}>
                {script.file_name || script.name || script.file_path}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="tag"
          label="标签"
          rules={[{ required: true, message: '请输入标签' }]}
          extra="用于区分不同批次的实验，如 baseline、experiment-v1 等"
        >
          <Input placeholder="请输入标签，如 baseline" />
        </Form.Item>

        <Form.Item
          name="model"
          label="模型"
          extra="可选，用于对比不同模型的效果"
        >
          <Select placeholder="请选择模型" allowClear>
            {models.map((model) => (
              <Select.Option key={model} value={model}>
                {model}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="concurrency"
          label="并发数"
          rules={[{ required: true, message: '请输入并发数' }]}
          extra="任务将被自动拆分为多个子任务并发执行"
        >
          <InputNumber min={1} max={100} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item
          label="过滤条件"
          extra="可选，用于筛选数据集中的特定实例，支持 JSON 格式"
        >
          <JsonEditor
            value={filterConditions}
            onChange={setFilterConditions}
            placeholder='例如：{"category": "bug_fix", "difficulty": "hard"}'
          />
        </Form.Item>

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={loading}>
              创建任务
            </Button>
            <Button onClick={() => navigate('/dashboard')}>
              取消
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  )
}
