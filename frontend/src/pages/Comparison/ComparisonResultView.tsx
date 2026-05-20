import { useState } from 'react'
import { Button, Card, Col, Drawer, Empty, message, Progress, Row, Space, Statistic, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { comparisonsApi } from '@/api/comparisons'
import type { ComparisonInstanceCell, ComparisonInstanceRow, ComparisonResponse } from '@/types'

const { Text } = Typography

function pct(value: number | null | undefined) {
  return value == null ? '-' : `${Math.round(value * 100)}%`
}

function outcomeTag(outcome: string) {
  const map: Record<string, { color: string; text: string }> = {
    all_success: { color: 'success', text: '全部通过' },
    all_failed: { color: 'error', text: '全部失败' },
    regression: { color: 'error', text: '回退' },
    improvement: { color: 'success', text: '提升' },
    mixed: { color: 'warning', text: '不一致' },
    missing: { color: 'default', text: '缺失' },
  }
  const item = map[outcome] || { color: 'default', text: outcome }
  return <Tag color={item.color}>{item.text}</Tag>
}

function validationTag(value: boolean | null) {
  if (value === true) return <Tag color="success">通过</Tag>
  if (value === false) return <Tag color="error">未通过</Tag>
  return <Tag>未知</Tag>
}

function keyLabel(key: string, cell?: ComparisonInstanceCell | null) {
  if (cell?.batch_name) return cell.batch_name
  return key.replace(/^batch:/, '#').replace(/^model:/, '').replace(/^tag:/, '')
}

interface Props {
  result: ComparisonResponse
}

export default function ComparisonResultView({ result }: Props) {
  const [patchOpen, setPatchOpen] = useState(false)
  const [patchTitle, setPatchTitle] = useState('')
  const [patchContent, setPatchContent] = useState('')

  const showPatch = async (instanceId: string, cell: ComparisonInstanceCell) => {
    try {
      const data = await comparisonsApi.getPatchContent(cell.batch_id, instanceId)
      setPatchTitle(`${cell.batch_name} / ${instanceId}`)
      setPatchContent(data.content)
      setPatchOpen(true)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '读取 patch 失败')
    }
  }

  const columns: ColumnsType<ComparisonInstanceRow> = [
    {
      title: 'Instance ID',
      dataIndex: 'instance_id',
      key: 'instance_id',
      width: 260,
      fixed: 'left',
      render: (value: string) => <Text copyable>{value}</Text>,
    },
    {
      title: '结果',
      dataIndex: 'outcome',
      key: 'outcome',
      width: 110,
      render: outcomeTag,
      filters: [
        { text: '全部通过', value: 'all_success' },
        { text: '全部失败', value: 'all_failed' },
        { text: '回退', value: 'regression' },
        { text: '提升', value: 'improvement' },
        { text: '不一致', value: 'mixed' },
        { text: '缺失', value: 'missing' },
      ],
      onFilter: (value, record) => record.outcome === value,
    },
    ...result.keys.map(key => ({
      title: keyLabel(key, result.instance_rows.find(row => row.results[key])?.results[key]),
      key,
      width: 220,
      render: (_: unknown, record: ComparisonInstanceRow) => {
        const cell = record.results[key]
        if (!cell) return <Tag>无结果</Tag>
        return (
          <Space direction="vertical" size={2}>
            <Space size="small" wrap>
              {validationTag(cell.validation_success)}
              <Tag>{cell.model}</Tag>
              <Tag>{cell.tag}</Tag>
            </Space>
            <Text type="secondary">测试：{cell.tests_passed}/{cell.tests_failed}/{cell.tests_total}</Text>
            <Text type="secondary">耗时：{cell.duration_seconds == null ? '-' : `${cell.duration_seconds.toFixed(2)}s`}</Text>
            {cell.has_patch && <Button size="small" onClick={() => showPatch(record.instance_id, cell)}>Patch</Button>}
          </Space>
        )
      },
    })),
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Row gutter={[16, 16]}>
        <Col xs={12} md={6}><Card><Statistic title="共同实例" value={result.common_instances} /></Card></Col>
        <Col xs={12} md={6}><Card><Statistic title="对比实例" value={result.compared_instances} /></Card></Col>
        <Col xs={12} md={6}><Card><Statistic title="总实例并集" value={result.total_union_instances} /></Card></Col>
        <Col xs={12} md={6}><Card><Statistic title="展示行数" value={result.instance_rows.length} /></Card></Col>
      </Row>

      <Row gutter={[16, 16]}>
        {result.keys.map(key => {
          const summary = result.summaries[key]
          return (
            <Col xs={24} md={12} xl={8} key={key}>
              <Card title={summary.batch_name || key.replace(/^model:/, '').replace(/^tag:/, '')}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text>{summary.model} / {summary.tag}</Text>
                  <Row gutter={12}>
                    <Col span={8}><Statistic title="总数" value={summary.total} /></Col>
                    <Col span={8}><Statistic title="完成" value={summary.completed} /></Col>
                    <Col span={8}><Statistic title="失败" value={summary.failed} /></Col>
                  </Row>
                  <Text>正确率：{summary.validation_success}/{summary.completed}（{pct(summary.accuracy)}）</Text>
                  <Progress percent={summary.accuracy == null ? 0 : Math.round(summary.accuracy * 100)} status="success" />
                  <Text>测试通过率：{pct(summary.test_pass_rate)}</Text>
                  <Text type="secondary">平均耗时：{summary.avg_duration_seconds == null ? '-' : `${summary.avg_duration_seconds.toFixed(2)}s`}</Text>
                </Space>
              </Card>
            </Col>
          )
        })}
      </Row>

      <Card title="实例对比明细">
        {result.instance_rows.length ? (
          <Table
            rowKey="instance_id"
            columns={columns}
            dataSource={result.instance_rows}
            scroll={{ x: 520 + result.keys.length * 220 }}
            pagination={{ pageSize: 20, showSizeChanger: true, showTotal: total => `共 ${total} 个实例` }}
          />
        ) : <Empty description="没有可展示的实例" />}
      </Card>

      <Drawer title={patchTitle} open={patchOpen} onClose={() => setPatchOpen(false)} width="70%">
        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{patchContent}</pre>
      </Drawer>
    </Space>
  )
}
