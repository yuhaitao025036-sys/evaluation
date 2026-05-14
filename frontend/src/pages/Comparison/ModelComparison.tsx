import { useState, useEffect } from 'react'
import { Card, Form, Select, Button, Space, Table, Statistic, Row, Col } from 'antd'
import { comparisonsApi } from '@/api/comparisons'
import { modelsApi } from '@/api/models'
import { ModelComparisonSummary } from '@/types'

export default function ModelComparison() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [tags, setTags] = useState<string[]>([])
  const [models, setModels] = useState<string[]>([])
  const [result, setResult] = useState<ModelComparisonSummary | null>(null)

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
      const res = await comparisonsApi.compareByModels({
        tag: values.tag,
        models: values.models,
      })
      setResult(res)
    } catch (error) {
      console.error('Failed to compare models:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title="模型对比配置" style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline" onFinish={handleCompare}>
          <Form.Item
            name="tag"
            label="标签"
            rules={[{ required: true, message: '请选择标签' }]}
          >
            <Select placeholder="请选择标签" style={{ width: 200 }}>
              {tags.map((tag) => (
                <Select.Option key={tag} value={tag}>
                  {tag}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="models"
            label="模型"
            rules={[{ required: true, message: '请选择模型' }]}
          >
            <Select
              mode="multiple"
              placeholder="请选择要对比的模型"
              style={{ width: 400 }}
            >
              {models.map((model) => (
                <Select.Option key={model} value={model}>
                  {model}
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
          <Card title="对比概览" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={8}>
                <Statistic title="总实例数" value={result.total_instances} />
              </Col>
              <Col span={8}>
                <Statistic title="已对比实例" value={result.compared_instances} />
              </Col>
              <Col span={8}>
                <Statistic
                  title="对比覆盖率"
                  value={(result.compared_instances / result.total_instances * 100).toFixed(1)}
                  suffix="%"
                />
              </Col>
            </Row>
            <div style={{ marginTop: 16 }}>
              <strong>对比模型：</strong>
              {result.models.join('、')}
            </div>
          </Card>

          <Card title="详细指标">
            <pre style={{ maxHeight: 600, overflow: 'auto' }}>
              {JSON.stringify(result.metrics, null, 2)}
            </pre>
          </Card>
        </>
      )}
    </div>
  )
}
