import { useState, useEffect } from 'react'
import { Card, Form, Input, Select, Button, Descriptions, Tag } from 'antd'
import { comparisonsApi } from '@/api/comparisons'
import { modelsApi } from '@/api/models'
import { ComparisonResult } from '@/types'

export default function InstanceComparison() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [tags, setTags] = useState<string[]>([])
  const [models, setModels] = useState<string[]>([])
  const [result, setResult] = useState<ComparisonResult | null>(null)

  useEffect(() => {
    fetchFilters()
  }, [])

  const fetchFilters = async () => {
    try {
      const [tagsRes, modelsRes] = await Promise.all([
        comparisonsApi.getTags(),
        modelsApi.inUse(),
      ])
      setTags(tagsRes)
      setModels(modelsRes)
    } catch (error) {
      console.error('Failed to fetch filters:', error)
    }
  }

  const handleCompare = async (values: any) => {
    setLoading(true)
    try {
      const res = await comparisonsApi.compareInstance(values.instance_id, {
        baseline_tag: values.baseline_tag,
        comparison_tags: values.comparison_tags,
        model: values.model,
      })
      setResult(res)
    } catch (error) {
      console.error('Failed to compare instance:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title="实例对比配置" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical" onFinish={handleCompare}>
          <Form.Item
            name="instance_id"
            label="Instance ID"
            rules={[{ required: true, message: '请输入 Instance ID' }]}
          >
            <Input placeholder="请输入要对比的 Instance ID" />
          </Form.Item>
          <Form.Item
            name="model"
            label="模型（可选）"
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
            name="baseline_tag"
            label="基线标签"
            rules={[{ required: true, message: '请选择基线标签' }]}
          >
            <Select placeholder="请选择基线标签">
              {tags.map((tag) => (
                <Select.Option key={tag} value={tag}>
                  {tag}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="comparison_tags"
            label="对比标签"
            rules={[{ required: true, message: '请选择对比标签' }]}
          >
            <Select
              mode="multiple"
              placeholder="请选择要对比的标签"
            >
              {tags.map((tag) => (
                <Select.Option key={tag} value={tag}>
                  {tag}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>
              开始对比
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {result && (
        <>
          <Card title="基线结果" style={{ marginBottom: 16 }}>
            <Descriptions column={1} bordered>
              <Descriptions.Item label="Instance ID">
                <Tag color="blue">{result.instance_id}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="结果数据">
                {result.baseline_result ? (
                  <pre style={{ maxHeight: 400, overflow: 'auto', margin: 0 }}>
                    {JSON.stringify(result.baseline_result, null, 2)}
                  </pre>
                ) : '无数据'}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="对比结果" style={{ marginBottom: 16 }}>
            {Object.entries(result.comparison_results).map(([tag, data]) => (
              <Card
                key={tag}
                type="inner"
                title={<Tag color="green">{tag}</Tag>}
                style={{ marginBottom: 16 }}
              >
                {data ? (
                  <pre style={{ maxHeight: 400, overflow: 'auto', margin: 0 }}>
                    {JSON.stringify(data, null, 2)}
                  </pre>
                ) : '无数据'}
              </Card>
            ))}
          </Card>

          <Card title="差异摘要">
            <pre style={{ maxHeight: 400, overflow: 'auto' }}>
              {JSON.stringify(result.diff_summary, null, 2)}
            </pre>
          </Card>
        </>
      )}
    </div>
  )
}
