import { useEffect, useMemo, useState } from 'react'
import {
  Button,
  Card,
  Col,
  Input,
  message,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  EyeOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  PlusCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { batchesApi } from '@/api/batches'
import type { Batch } from '@/types'

const { Search } = Input
const { Text, Title } = Typography

type QuickFilter = 'running' | 'failed' | 'attention'

const statusMap: Record<string, { color: string; text: string }> = {
  created: { color: 'default', text: '已创建' },
  running: { color: 'processing', text: '运行中' },
  paused: { color: 'warning', text: '已暂停' },
  completed: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
}

function statusTag(status?: string | null) {
  if (!status) return <Tag>-</Tag>
  const config = statusMap[status] || { color: 'default', text: status }
  return <Tag color={config.color}>{config.text}</Tag>
}

function formatTime(value?: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN') : '-'
}

function activeTasks(batch: Batch) {
  return (batch.queued_tasks || 0) + (batch.running_tasks || 0)
}

function terminalTasks(batch: Batch) {
  return (batch.completed_tasks || 0) + (batch.failed_tasks || 0)
}

function completionRate(batch: Batch) {
  if (!batch.total_tasks) return 0
  return Math.round((terminalTasks(batch) / batch.total_tasks) * 100)
}

function successProgress(batch: Batch) {
  if (!batch.total_tasks) return 0
  return Math.round(((batch.completed_tasks || 0) / batch.total_tasks) * 100)
}

function needsAttention(batch: Batch) {
  return (
    batch.failed_tasks > 0 ||
    batch.status === 'failed' ||
    (batch.status === 'paused' && batch.pending_tasks > 0) ||
    (batch.status === 'created' && batch.total_tasks > 0)
  )
}

function attentionReason(batch: Batch) {
  if (batch.failed_tasks > 0) return `${batch.failed_tasks} 个失败任务`
  if (batch.status === 'failed') return '批次失败'
  if (batch.status === 'paused' && batch.pending_tasks > 0) return '暂停且仍有待执行任务'
  if (batch.status === 'created' && batch.total_tasks > 0) return '已创建未启动'
  return '需关注'
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [batches, setBatches] = useState<Batch[]>([])
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [modelFilter, setModelFilter] = useState<string | undefined>()
  const [tagFilter, setTagFilter] = useState<string | undefined>()
  const [quickFilter, setQuickFilter] = useState<QuickFilter | undefined>()
  const [searchText, setSearchText] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchBatches = async () => {
    setLoading(true)
    try {
      const data = await batchesApi.list({ limit: 1000 })
      setBatches(data)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '获取任务面板数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBatches()
  }, [])

  const hasActiveWork = useMemo(
    () => batches.some(batch => batch.status === 'running' || activeTasks(batch) > 0),
    [batches],
  )

  useEffect(() => {
    if (!autoRefresh) return
    const interval = window.setInterval(fetchBatches, hasActiveWork ? 5000 : 15000)
    return () => window.clearInterval(interval)
  }, [autoRefresh, hasActiveWork])

  const models = useMemo(
    () => Array.from(new Set(batches.map(batch => batch.model).filter(Boolean))),
    [batches],
  )

  const tags = useMemo(
    () => Array.from(new Set(batches.map(batch => batch.tag).filter(Boolean))),
    [batches],
  )

  const filteredBatches = useMemo(() => {
    const normalizedSearch = searchText.trim().toLowerCase()
    return batches.filter(batch => {
      if (statusFilter && batch.status !== statusFilter) return false
      if (modelFilter && batch.model !== modelFilter) return false
      if (tagFilter && batch.tag !== tagFilter) return false
      if (quickFilter === 'running' && batch.status !== 'running' && activeTasks(batch) === 0) return false
      if (quickFilter === 'failed' && batch.failed_tasks === 0 && batch.status !== 'failed') return false
      if (quickFilter === 'attention' && !needsAttention(batch)) return false
      if (normalizedSearch) {
        const searchable = [
          batch.batch_name,
          batch.dataset?.name,
          `数据集 #${batch.dataset_id}`,
          batch.model,
          batch.tag,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
        if (!searchable.includes(normalizedSearch)) return false
      }
      return true
    })
  }, [batches, statusFilter, modelFilter, tagFilter, quickFilter, searchText])

  const dashboardStats = useMemo(() => {
    const totalTasks = batches.reduce((sum, batch) => sum + batch.total_tasks, 0)
    const terminal = batches.reduce((sum, batch) => sum + terminalTasks(batch), 0)
    return {
      totalBatches: batches.length,
      runningBatches: batches.filter(batch => batch.status === 'running').length,
      attentionBatches: batches.filter(needsAttention).length,
      activeTaskCount: batches.reduce((sum, batch) => sum + activeTasks(batch), 0),
      pendingTaskCount: batches.reduce((sum, batch) => sum + batch.pending_tasks, 0),
      completedTaskCount: batches.reduce((sum, batch) => sum + batch.completed_tasks, 0),
      failedTaskCount: batches.reduce((sum, batch) => sum + batch.failed_tasks, 0),
      completionRate: totalTasks ? Math.round((terminal / totalTasks) * 100) : 0,
    }
  }, [batches])

  const attentionBatches = useMemo(
    () => batches
      .filter(needsAttention)
      .sort((a, b) => {
        if (b.failed_tasks !== a.failed_tasks) return b.failed_tasks - a.failed_tasks
        return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      })
      .slice(0, 5),
    [batches],
  )

  const handleStart = async (batch: Batch) => {
    try {
      await batchesApi.start(batch.id)
      message.success(`批次 "${batch.batch_name}" 已启动`)
      fetchBatches()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '启动失败')
    }
  }

  const handlePause = async (batch: Batch) => {
    try {
      await batchesApi.pause(batch.id)
      message.success(`批次 "${batch.batch_name}" 已暂停`)
      fetchBatches()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '暂停失败')
    }
  }

  const handleResume = async (batch: Batch) => {
    try {
      await batchesApi.resume(batch.id)
      message.success(`批次 "${batch.batch_name}" 已恢复`)
      fetchBatches()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '恢复失败')
    }
  }

  const handleRetry = async (batch: Batch) => {
    try {
      const result = await batchesApi.retry(batch.id, { reset_retry_count: true })
      message.success(`已重试 ${result.retried_count} 个失败任务`)
      fetchBatches()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '重试失败')
    }
  }

  const columns: ColumnsType<Batch> = [
    {
      title: '批次',
      dataIndex: 'batch_name',
      key: 'batch_name',
      width: 260,
      render: (value: string, record) => (
        <Space direction="vertical" size={2}>
          <Text strong>{value}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.dataset?.name || `数据集 #${record.dataset_id}`}
          </Text>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: statusTag,
    },
    {
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      width: 150,
      render: (value: string) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: '标签',
      dataIndex: 'tag',
      key: 'tag',
      width: 120,
      render: (value: string) => <Tag>{value}</Tag>,
    },
    {
      title: '任务进度',
      key: 'progress',
      width: 360,
      render: (_, record) => (
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          <Progress
            percent={completionRate(record)}
            success={{ percent: successProgress(record) }}
            status={record.failed_tasks > 0 ? 'exception' : undefined}
          />
          <Space size="middle" wrap>
            <Text type="secondary" style={{ fontSize: 12 }}>已结束 {terminalTasks(record)}/{record.total_tasks}</Text>
            <Text type="success" style={{ fontSize: 12 }}>成功 {record.completed_tasks}</Text>
            {record.failed_tasks > 0 && <Text type="danger" style={{ fontSize: 12 }}>失败 {record.failed_tasks}</Text>}
            {activeTasks(record) > 0 && <Text type="warning" style={{ fontSize: 12 }}>活跃 {activeTasks(record)}</Text>}
            {record.pending_tasks > 0 && <Text type="secondary" style={{ fontSize: 12 }}>待执行 {record.pending_tasks}</Text>}
          </Space>
        </Space>
      ),
    },
    {
      title: '并发',
      key: 'concurrency',
      width: 100,
      render: (_, record) => `${record.current_running}/${record.max_concurrency}`,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      render: formatTime,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: formatTime,
    },
    {
      title: '操作',
      key: 'actions',
      fixed: 'right',
      width: 300,
      render: (_, record) => (
        <Space size="small" wrap>
          <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/batches/${record.id}`)}>
            查看
          </Button>
          {record.status === 'created' && (
            <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={() => handleStart(record)}>
              启动
            </Button>
          )}
          {record.status === 'running' && (
            <Button size="small" icon={<PauseCircleOutlined />} onClick={() => handlePause(record)}>
              暂停
            </Button>
          )}
          {record.status === 'paused' && (
            <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={() => handleResume(record)}>
              恢复
            </Button>
          )}
          {record.failed_tasks > 0 && (
            <Button size="small" icon={<ReloadOutlined />} onClick={() => handleRetry(record)}>
              重试失败
            </Button>
          )}
          <Button size="small" icon={<PlusCircleOutlined />} onClick={() => navigate(`/batches/create?append_to=${record.id}`)}>
            追加
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Space style={{ width: '100%', justifyContent: 'space-between' }} align="start">
            <Space direction="vertical" size={4}>
              <Title level={3} style={{ margin: 0 }}>任务面板</Title>
              <Text type="secondary">基于批次和子任务的运行监控面板</Text>
            </Space>
            <Space>
              <Text type="secondary">自动刷新</Text>
              <Switch checked={autoRefresh} onChange={setAutoRefresh} />
              <Button icon={<ReloadOutlined />} onClick={fetchBatches} loading={loading}>刷新</Button>
            </Space>
          </Space>
        </Card>

        <Row gutter={[16, 16]}>
          <Col xs={12} md={6} xl={3}><Card><Statistic title="总批次" value={dashboardStats.totalBatches} /></Card></Col>
          <Col xs={12} md={6} xl={3}><Card><Statistic title="运行中批次" value={dashboardStats.runningBatches} valueStyle={{ color: '#1677ff' }} /></Card></Col>
          <Col xs={12} md={6} xl={3}><Card><Statistic title="需关注批次" value={dashboardStats.attentionBatches} valueStyle={{ color: dashboardStats.attentionBatches ? '#cf1322' : undefined }} /></Card></Col>
          <Col xs={12} md={6} xl={3}><Card><Statistic title="活跃任务" value={dashboardStats.activeTaskCount} valueStyle={{ color: '#faad14' }} /></Card></Col>
          <Col xs={12} md={6} xl={3}><Card><Statistic title="待执行" value={dashboardStats.pendingTaskCount} /></Card></Col>
          <Col xs={12} md={6} xl={3}><Card><Statistic title="执行成功" value={dashboardStats.completedTaskCount} valueStyle={{ color: '#3f8600' }} /></Card></Col>
          <Col xs={12} md={6} xl={3}><Card><Statistic title="执行失败" value={dashboardStats.failedTaskCount} valueStyle={{ color: dashboardStats.failedTaskCount ? '#cf1322' : undefined }} /></Card></Col>
          <Col xs={12} md={6} xl={3}><Card><Statistic title="整体完成率" value={dashboardStats.completionRate} suffix="%" /></Card></Col>
        </Row>

        <Card title="需关注批次">
          <Table
            rowKey="id"
            size="small"
            columns={[
              {
                title: '批次',
                dataIndex: 'batch_name',
                render: (value: string, record: Batch) => <Button type="link" onClick={() => navigate(`/batches/${record.id}`)}>{value}</Button>,
              },
              { title: '状态', dataIndex: 'status', width: 100, render: statusTag },
              { title: '原因', key: 'reason', render: (_: unknown, record: Batch) => attentionReason(record) },
              { title: '失败任务', dataIndex: 'failed_tasks', width: 100 },
              { title: '待执行', dataIndex: 'pending_tasks', width: 100 },
              { title: '更新时间', dataIndex: 'updated_at', width: 180, render: formatTime },
            ]}
            dataSource={attentionBatches}
            pagination={false}
            locale={{ emptyText: '暂无需要关注的批次' }}
          />
        </Card>

        <Card
          title="批次运行列表"
          extra={(
            <Space wrap>
              <Select placeholder="状态" allowClear value={statusFilter} onChange={setStatusFilter} style={{ width: 130 }}>
                <Select.Option value="created">已创建</Select.Option>
                <Select.Option value="running">运行中</Select.Option>
                <Select.Option value="paused">已暂停</Select.Option>
                <Select.Option value="completed">已完成</Select.Option>
                <Select.Option value="failed">失败</Select.Option>
              </Select>
              <Select placeholder="模型" allowClear value={modelFilter} onChange={setModelFilter} style={{ width: 180 }}>
                {models.map(model => <Select.Option key={model} value={model}>{model}</Select.Option>)}
              </Select>
              <Select placeholder="标签" allowClear value={tagFilter} onChange={setTagFilter} style={{ width: 150 }}>
                {tags.map(tag => <Select.Option key={tag} value={tag}>{tag}</Select.Option>)}
              </Select>
              <Select placeholder="快捷筛选" allowClear value={quickFilter} onChange={setQuickFilter} style={{ width: 150 }}>
                <Select.Option value="running">运行中/活跃</Select.Option>
                <Select.Option value="failed">有失败</Select.Option>
                <Select.Option value="attention">需关注</Select.Option>
              </Select>
              <Search
                placeholder="搜索批次/数据集/模型/标签"
                allowClear
                value={searchText}
                onChange={event => setSearchText(event.target.value)}
                onSearch={setSearchText}
                style={{ width: 280 }}
              />
            </Space>
          )}
        >
          <Table
            rowKey="id"
            columns={columns}
            dataSource={filteredBatches}
            loading={loading}
            scroll={{ x: 1700 }}
            pagination={{
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: total => `共 ${total} 个批次`,
              defaultPageSize: 20,
              pageSizeOptions: ['10', '20', '50', '100'],
            }}
          />
        </Card>
      </Space>
    </div>
  )
}
