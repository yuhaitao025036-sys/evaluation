import { useEffect, useState } from 'react'
import { Button, Card, Form, InputNumber, message, Select, Space, Switch } from 'antd'
import { comparisonsApi } from '@/api/comparisons'
import type { ComparisonMetadata, ComparisonResponse } from '@/types'
import ComparisonResultView from './ComparisonResultView'

export default function TagComparison() {
  const [form] = Form.useForm()
  const [metadata, setMetadata] = useState<ComparisonMetadata | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ComparisonResponse | null>(null)

  useEffect(() => {
    comparisonsApi.getMetadata()
      .then(setMetadata)
      .catch((error: any) => message.error(error.response?.data?.detail || '获取对比元信息失败'))
  }, [])

  const handleCompare = async (values: any) => {
    setLoading(true)
    try {
      const data = await comparisonsApi.compareByTags({
        tags: values.tags,
        dataset_id: values.dataset_id,
        model: values.model,
        only_common_instances: values.only_common_instances ?? true,
        instance_limit: values.instance_limit || 200,
        include_instances: true,
      })
      setResult(data)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '标签对比失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card title="标签对比配置">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCompare}
          initialValues={{ only_common_instances: true, instance_limit: 200 }}
        >
          <Form.Item name="tags" label="Tag" rules={[{ required: true, message: '请选择至少两个 tag' }]}>
            <Select mode="multiple" placeholder="请选择要对比的 tag" options={(metadata?.tags || []).map(tag => ({ value: tag, label: tag }))} />
          </Form.Item>
          <Space wrap align="end">
            <Form.Item name="dataset_id" label="数据集">
              <Select allowClear placeholder="可选" style={{ width: 220 }} options={(metadata?.datasets || []).map(dataset => ({ value: dataset.id, label: dataset.name }))} />
            </Form.Item>
            <Form.Item name="model" label="模型">
              <Select allowClear placeholder="可选" style={{ width: 220 }} options={(metadata?.models || []).map(model => ({ value: model, label: model }))} />
            </Form.Item>
            <Form.Item name="only_common_instances" label="只看共同实例" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="instance_limit" label="实例行数上限">
              <InputNumber min={1} max={2000} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading}>开始对比</Button>
            </Form.Item>
          </Space>
        </Form>
      </Card>

      {result && <ComparisonResultView result={result} />}
    </Space>
  )
}
