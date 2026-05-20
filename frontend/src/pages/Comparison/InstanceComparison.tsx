import { useEffect, useState } from 'react'
import { Button, Card, Drawer, Form, Input, message, Select, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { comparisonsApi } from '@/api/comparisons'
import type { ComparisonInstanceCell, ComparisonMetadata, InstanceComparisonResponse } from '@/types'

const { Text } = Typography

function validationTag(value: boolean | null) {
  if (value === true) return <Tag color="success">通过</Tag>
  if (value === false) return <Tag color="error">未通过</Tag>
  return <Tag>未知</Tag>
}

export default function InstanceComparison() {
  const [form] = Form.useForm()
  const [metadata, setMetadata] = useState<ComparisonMetadata | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<InstanceComparisonResponse | null>(null)
  const [patchOpen, setPatchOpen] = useState(false)
  const [patchTitle, setPatchTitle] = useState('')
  const [patchContent, setPatchContent] = useState('')

  useEffect(() => {
    comparisonsApi.getMetadata()
      .then(setMetadata)
      .catch((error: any) => message.error(error.response?.data?.detail || '获取对比元信息失败'))
  }, [])

  const handleCompare = async (values: any) => {
    setLoading(true)
    try {
      const data = await comparisonsApi.compareInstance({
        instance_id: values.instance_id,
        batch_ids: values.batch_ids,
        models: values.models,
        tags: values.tags,
        dataset_id: values.dataset_id,
      })
      setResult(data)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '实例对比失败')
    } finally {
      setLoading(false)
    }
  }

  const showPatch = async (cell: ComparisonInstanceCell) => {
    if (!result) return
    try {
      const data = await comparisonsApi.getPatchContent(cell.batch_id, result.instance_id)
      setPatchTitle(`${cell.batch_name} / ${result.instance_id}`)
      setPatchContent(data.content)
      setPatchOpen(true)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '读取 patch 失败')
    }
  }

  const columns: ColumnsType<ComparisonInstanceCell> = [
    { title: '批次', dataIndex: 'batch_name', key: 'batch_name', width: 220, render: (value: string, record) => <Text copyable={{ text: String(record.batch_id) }}>{value}</Text> },
    { title: '模型', dataIndex: 'model', key: 'model', width: 180, render: (value: string) => <Tag>{value}</Tag> },
    { title: 'Tag', dataIndex: 'tag', key: 'tag', width: 160, render: (value: string) => <Tag color="blue">{value}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (value: string) => <Tag>{value}</Tag> },
    { title: '评测', dataIndex: 'validation_success', key: 'validation_success', width: 100, render: validationTag },
    { title: '测试', key: 'tests', width: 140, render: (_, record) => `${record.tests_passed}/${record.tests_failed}/${record.tests_total}` },
    { title: '耗时', dataIndex: 'duration_seconds', key: 'duration_seconds', width: 100, render: (value: number | null) => value == null ? '-' : `${value.toFixed(2)}s` },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_, record) => record.has_patch ? <Button size="small" onClick={() => showPatch(record)}>Patch</Button> : '-',
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card title="实例对比配置">
        <Form form={form} layout="vertical" onFinish={handleCompare}>
          <Form.Item name="instance_id" label="Instance ID" rules={[{ required: true, message: '请输入 Instance ID' }]}>
            <Input placeholder="请输入要对比的 Instance ID" />
          </Form.Item>
          <Form.Item name="batch_ids" label="批次">
            <Select
              mode="multiple"
              allowClear
              placeholder="可选，限制到指定批次"
              optionFilterProp="label"
              options={(metadata?.batches || []).map(batch => ({
                value: batch.id,
                label: `#${batch.id} ${batch.batch_name} | ${batch.model} | ${batch.tag}`,
              }))}
            />
          </Form.Item>
          <Space wrap align="end">
            <Form.Item name="dataset_id" label="数据集">
              <Select allowClear placeholder="可选" style={{ width: 220 }} options={(metadata?.datasets || []).map(dataset => ({ value: dataset.id, label: dataset.name }))} />
            </Form.Item>
            <Form.Item name="models" label="模型">
              <Select mode="multiple" allowClear placeholder="可选" style={{ width: 260 }} options={(metadata?.models || []).map(model => ({ value: model, label: model }))} />
            </Form.Item>
            <Form.Item name="tags" label="Tag">
              <Select mode="multiple" allowClear placeholder="可选" style={{ width: 260 }} options={(metadata?.tags || []).map(tag => ({ value: tag, label: tag }))} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading}>开始对比</Button>
            </Form.Item>
          </Space>
        </Form>
      </Card>

      {result && (
        <Card title={`实例结果：${result.instance_id}`}>
          <Table
            rowKey={record => `${record.batch_id}-${record.model}-${record.tag}`}
            columns={columns}
            dataSource={result.results}
            scroll={{ x: 1100 }}
            pagination={{ pageSize: 20, showSizeChanger: true, showTotal: total => `共 ${total} 条结果` }}
          />
        </Card>
      )}

      <Drawer title={patchTitle} open={patchOpen} onClose={() => setPatchOpen(false)} width="70%">
        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{patchContent}</pre>
      </Drawer>
    </Space>
  )
}
