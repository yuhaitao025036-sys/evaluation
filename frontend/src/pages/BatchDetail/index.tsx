import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Button,
  Card,
  Descriptions,
  Drawer,
  Empty,
  message,
  Progress,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  Row,
  Col,
  Select,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  ArrowLeftOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  PlusCircleOutlined,
} from '@ant-design/icons'
import { batchesApi } from '@/api/batches'
import type { Batch, BatchResult, BatchStats } from '@/types'

const { Text, Title, Paragraph } = Typography

const statusMap: Record<string, { color: string; text: string }> = {
  created: { color: 'default', text: '已创建' },
  pending: { color: 'default', text: '待执行' },
  queued: { color: 'processing', text: '排队中' },
  running: { color: 'processing', text: '运行中' },
  retrying: { color: 'warning', text: '重试中' },
  paused: { color: 'warning', text: '已暂停' },
  completed: { color: 'success', text: '已结束' },
  failed: { color: 'error', text: '失败' },
}

const outcomeMap: Record<string, { color: string; text: string }> = {
  in_progress: { color: 'processing', text: '执行中' },
  completed_successfully: { color: 'success', text: '全部通过' },
  completed_with_failures: { color: 'error', text: '存在失败' },
  paused: { color: 'warning', text: '已暂停' },
  not_started: { color: 'default', text: '未开始' },
  unknown: { color: 'default', text: '未知' },
}

function percent(value?: number | null) {
  return Math.round((value || 0) * 100)
}

function formatTime(value?: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN') : '-'
}

function statusTag(status?: string | null) {
  if (!status) return <Tag>-</Tag>
  const item = statusMap[status] || { color: 'default', text: status }
  return <Tag color={item.color}>{item.text}</Tag>
}

function outcomeTag(outcome?: string | null) {
  if (!outcome) return <Tag>-</Tag>
  const item = outcomeMap[outcome] || { color: 'default', text: outcome }
  return <Tag color={item.color}>{item.text}</Tag>
}

export default function BatchDetail() {
  const navigate = useNavigate()
  const { id } = useParams()
  const batchId = Number(id)
  const [loading, setLoading] = useState(false)
  const [tasksLoading, setTasksLoading] = useState(false)
  const [batch, setBatch] = useState<Batch | null>(null)
  const [stats, setStats] = useState<BatchStats | null>(null)
  const [tasks, setTasks] = useState<BatchResult[]>([])
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [validationFilter, setValidationFilter] = useState<string | undefined>()
  const [artifactOpen, setArtifactOpen] = useState(false)
  const [artifactTitle, setArtifactTitle] = useState('')
  const [artifactContent, setArtifactContent] = useState('')

  const fetchAll = useCallback(async (silent = false) => {
    if (!batchId) return
    if (!silent) setLoading(true)
    try {
      const [batchData, statsData] = await Promise.all([
        batchesApi.get(batchId),
        batchesApi.getStats(batchId),
      ])
      setBatch(batchData)
      setStats(statsData)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '获取批次详情失败')
    } finally {
      if (!silent) setLoading(false)
    }
  }, [batchId])

  const fetchTasks = useCallback(async (silent = false) => {
    if (!batchId) return
    if (!silent) setTasksLoading(true)
    try {
      const data = await batchesApi.getTasks(batchId, { status: statusFilter, limit: 1000 })
      setTasks(data)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '获取任务列表失败')
    } finally {
      if (!silent) setTasksLoading(false)
    }
  }, [batchId, statusFilter])

  const refresh = useCallback(async (silent = false) => {
    await Promise.all([fetchAll(silent), fetchTasks(silent)])
  }, [fetchAll, fetchTasks])

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  useEffect(() => {
    const active =
      batch?.status === 'running' ||
      (stats?.active_tasks || 0) > 0 ||
      ((stats?.pending_tasks || 0) > 0 && batch?.status !== 'paused' && batch?.status !== 'completed')

    if (!active) return

    const interval = window.setInterval(() => refresh(true), 5000)
    return () => window.clearInterval(interval)
  }, [batch?.status, stats?.active_tasks, stats?.pending_tasks, refresh])

  const filteredTasks = tasks.filter(task => {
    if (validationFilter === 'success') return task.validation_success === true
    if (validationFilter === 'failure') return task.validation_success === false
    if (validationFilter === 'unknown') return task.validation_success == null
    return true
  })

  const handleStart = async () => {
    try {
      await batchesApi.start(batchId, batch?.status === 'completed')
      message.success('批次已启动')
      refresh()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '启动失败')
    }
  }

  const handlePause = async () => {
    try {
      await batchesApi.pause(batchId)
      message.success('批次已暂停')
      refresh()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '暂停失败')
    }
  }

  const handleResume = async () => {
    try {
      await batchesApi.resume(batchId)
      message.success('批次已恢复')
      refresh()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '恢复失败')
    }
  }

  const handleRetry = async () => {
    try {
      const result = await batchesApi.retry(batchId, { reset_retry_count: true })
      message.success(`已重试 ${result.retried_count} 个失败任务`)
      refresh()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '重试失败')
    }
  }

  const handleRunTask = async (instanceId: string) => {
    try {
      await batchesApi.runTask(batchId, instanceId)
      message.success('子任务已加入队列')
      refresh()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '执行子任务失败')
    }
  }

  const handleRerunTask = async (instanceId: string) => {
    try {
      await batchesApi.rerunTask(batchId, instanceId, { reset_retry_count: true })
      message.success('子任务已加入重跑队列')
      refresh()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '强制重跑失败')
    }
  }

  const showArtifact = async (title: string, loader: () => Promise<any>) => {
    try {
      const data = await loader()
      setArtifactTitle(title)
      setArtifactContent(typeof data === 'string' ? data : JSON.stringify(data, null, 2))
      setArtifactOpen(true)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '读取任务文件失败')
    }
  }

  const columns: ColumnsType<BatchResult> = [
    {
      title: '实例 ID',
      dataIndex: 'instance_id',
      key: 'instance_id',
      width: 260,
      render: (value: string) => <Text copyable>{value}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      filters: [
        { text: '待执行', value: 'pending' },
        { text: '排队中', value: 'queued' },
        { text: '运行中', value: 'running' },
        { text: '重试中', value: 'retrying' },
        { text: '已完成', value: 'completed' },
        { text: '失败', value: 'failed' },
      ],
      filteredValue: statusFilter ? [statusFilter] : null,
      onFilter: (value, record) => record.status === value,
      render: statusTag,
    },
    {
      title: '评测',
      dataIndex: 'validation_success',
      key: 'validation_success',
      width: 100,
      filters: [
        { text: '通过', value: 'success' },
        { text: '未通过', value: 'failure' },
        { text: '未知', value: 'unknown' },
      ],
      filteredValue: validationFilter ? [validationFilter] : null,
      render: (value: boolean | null) => {
        if (value === true) return <Tag color="success">通过</Tag>
        if (value === false) return <Tag color="error">未通过</Tag>
        return <Tag>未知</Tag>
      },
    },
    {
      title: '测试',
      key: 'tests',
      width: 140,
      sorter: (a, b) => (a.tests_passed - a.tests_failed) - (b.tests_passed - b.tests_failed),
      render: (_, record) => `${record.tests_passed}/${record.tests_failed}/${record.tests_total}`,
    },
    {
      title: '耗时',
      dataIndex: 'duration_seconds',
      key: 'duration_seconds',
      width: 100,
      sorter: (a, b) => (a.duration_seconds || 0) - (b.duration_seconds || 0),
      render: (value: number | null) => value == null ? '-' : `${value.toFixed(2)}s`,
    },
    {
      title: '重试',
      key: 'retry',
      width: 90,
      sorter: (a, b) => a.retry_count - b.retry_count,
      render: (_, record) => `${record.retry_count}/${record.max_retries}`,
    },
    {
      title: 'Worker',
      dataIndex: 'worker_id',
      key: 'worker_id',
      width: 120,
      render: (value: string | null) => value || '-',
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 180,
      render: formatTime,
    },
    {
      title: '错误',
      dataIndex: 'error_message',
      key: 'error_message',
      width: 220,
      ellipsis: true,
      render: (value: string | null) => value || '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small" wrap>
          <Button
            size="small"
            onClick={() => showArtifact(
              `${record.instance_id} patch`,
              async () => (await batchesApi.getTaskPatchContent(batchId, record.instance_id)).content,
            )}
          >
            Patch
          </Button>
          <Button
            size="small"
            onClick={() => showArtifact(
              `${record.instance_id} trace`,
              () => batchesApi.getTaskTrace(batchId, record.instance_id),
            )}
          >
            Trace
          </Button>
          <Button
            size="small"
            onClick={() => showArtifact(
              `${record.instance_id} validation`,
              () => batchesApi.getTaskValidationDetail(batchId, record.instance_id),
            )}
          >
            详情
          </Button>
          <Button
            size="small"
            onClick={() => showArtifact(
              `${record.instance_id} generation stdout`,
              async () => (await batchesApi.getTaskLogContent(batchId, record.instance_id, 'generation_stdout')).content,
            )}
          >
            日志
          </Button>
          {record.status === 'pending' && (
            <Button size="small" type="primary" onClick={() => handleRunTask(record.instance_id)}>
              执行此任务
            </Button>
          )}
          {(['queued', 'running', 'retrying', 'completed', 'failed'].includes(record.status)) && (
            <Button size="small" type="primary" onClick={() => handleRerunTask(record.instance_id)}>
              {['queued', 'running', 'retrying'].includes(record.status) ? '恢复重跑' : '强制重跑'}
            </Button>
          )}
        </Space>
      ),
    },
  ]

  if (!batch && !loading) {
    return <Empty description="批次不存在" />
  }

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card loading={loading}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }} align="start">
              <Space direction="vertical" size={4}>
                <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/batches')}>返回批次列表</Button>
                <Title level={3} style={{ margin: 0 }}>{batch?.batch_name}</Title>
                <Space wrap>
                  {statusTag(stats?.effective_status || batch?.status)}
                  {outcomeTag(stats?.outcome)}
                  <Tag color="blue">{batch?.model}</Tag>
                  <Tag>{batch?.tag}</Tag>
                </Space>
              </Space>
              <Space wrap>
                {batch?.status !== 'running' && (stats?.pending_tasks || 0) > 0 && <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleStart}>开始待执行任务</Button>}
                {batch?.status === 'running' && <Button icon={<PauseCircleOutlined />} onClick={handlePause}>暂停</Button>}
                {batch?.status === 'paused' && <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleResume}>恢复</Button>}
                {!!stats?.failed_tasks && <Button icon={<ReloadOutlined />} onClick={handleRetry}>重试失败任务</Button>}
                <Button icon={<PlusCircleOutlined />} onClick={() => navigate(`/batches/create?append_to=${batchId}`)}>追加任务</Button>
                <Button icon={<ReloadOutlined />} onClick={() => refresh()}>刷新</Button>
              </Space>
            </Space>

            <Descriptions bordered size="small" column={3}>
              <Descriptions.Item label="数据集">{batch?.dataset?.name || `#${batch?.dataset_id}`}</Descriptions.Item>
              <Descriptions.Item label="脚本">{batch?.script?.file_name || `#${batch?.script_id}`}</Descriptions.Item>
              <Descriptions.Item label="最大并发">{batch?.max_concurrency}</Descriptions.Item>
              <Descriptions.Item label="生命周期状态">{statusTag(batch?.status)}</Descriptions.Item>
              <Descriptions.Item label="实时状态">{statusTag(stats?.effective_status)}</Descriptions.Item>
              <Descriptions.Item label="评估结果">{outcomeTag(stats?.outcome)}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{formatTime(batch?.created_at)}</Descriptions.Item>
              <Descriptions.Item label="开始时间">{formatTime(batch?.started_at)}</Descriptions.Item>
              <Descriptions.Item label="完成时间">{formatTime(batch?.completed_at)}</Descriptions.Item>
              <Descriptions.Item label="输出目录" span={3}><Text copyable>{batch?.output_dir || '-'}</Text></Descriptions.Item>
            </Descriptions>
          </Space>
        </Card>

        {stats && (
          <>
            <Row gutter={[16, 16]}>
              <Col xs={12} md={6}><Card><Statistic title="总任务" value={stats.total_tasks} /></Card></Col>
              <Col xs={12} md={6}><Card><Statistic title="活跃任务" value={stats.active_tasks} /></Card></Col>
              <Col xs={12} md={6}><Card><Statistic title="已结束" value={stats.terminal_tasks} /></Card></Col>
              <Col xs={12} md={6}><Card><Statistic title="待执行" value={stats.pending_tasks} /></Card></Col>
              <Col xs={12} md={6}><Card><Statistic title="执行成功" value={stats.completed_tasks} valueStyle={{ color: '#3f8600' }} /></Card></Col>
              <Col xs={12} md={6}><Card><Statistic title="执行失败" value={stats.failed_tasks} valueStyle={{ color: '#cf1322' }} /></Card></Col>
              <Col xs={12} md={6}><Card><Statistic title="评测通过" value={stats.validation_success_count} valueStyle={{ color: '#3f8600' }} /></Card></Col>
              <Col xs={12} md={6}><Card><Statistic title="评测失败" value={stats.validation_failure_count} valueStyle={{ color: '#cf1322' }} /></Card></Col>
            </Row>

            <Card title="整体比例">
              <Row gutter={[24, 16]}>
                <Col xs={24} md={12} lg={8}>
                  <Text>完成进度：{stats.terminal_tasks}/{stats.total_tasks}</Text>
                  <Progress percent={percent(stats.completion_rate)} />
                </Col>
                <Col xs={24} md={12} lg={8}>
                  <Text>执行失败率：{stats.failed_tasks}/{stats.total_tasks}</Text>
                  <Progress percent={percent(stats.task_failure_rate)} status={stats.failed_tasks ? 'exception' : 'normal'} />
                </Col>
                <Col xs={24} md={12} lg={8}>
                  <Text>评测通过率：{stats.validation_success_count}/{stats.total_tasks}（{percent(stats.evaluation_success_rate)}%）</Text>
                  <Progress percent={percent(stats.evaluation_success_rate)} status="success" />
                </Col>
                <Col xs={24} md={12} lg={8}>
                  <Text>评测失败率：{stats.failed_tasks + stats.validation_failure_count}/{stats.total_tasks}</Text>
                  <Progress percent={percent(stats.evaluation_failure_rate)} status={stats.evaluation_failure_rate ? 'exception' : 'normal'} />
                </Col>
                <Col xs={24} md={12} lg={8}>
                  <Text>测试通过率：{stats.tests_passed}/{stats.tests_total}</Text>
                  <Progress percent={percent(stats.test_pass_rate)} />
                </Col>
                <Col xs={24} md={12} lg={8}>
                  <Text>平均耗时：{stats.avg_duration == null ? '-' : `${stats.avg_duration.toFixed(2)}s`}</Text>
                  <Paragraph type="secondary">总耗时：{stats.total_duration == null ? '-' : `${stats.total_duration.toFixed(2)}s`}</Paragraph>
                </Col>
              </Row>
            </Card>
          </>
        )}

        <Card
          title="任务列表"
          extra={(
            <Space>
              <Select
                placeholder="任务状态"
                allowClear
                value={statusFilter}
                onChange={setStatusFilter}
                style={{ width: 140 }}
              >
                <Select.Option value="pending">待执行</Select.Option>
                <Select.Option value="queued">排队中</Select.Option>
                <Select.Option value="running">运行中</Select.Option>
                <Select.Option value="retrying">重试中</Select.Option>
                <Select.Option value="completed">已完成</Select.Option>
                <Select.Option value="failed">失败</Select.Option>
              </Select>
              <Button icon={<FileTextOutlined />} onClick={() => fetchTasks()}>刷新任务</Button>
            </Space>
          )}
        >
          <Table
            rowKey="id"
            columns={columns}
            dataSource={filteredTasks}
            loading={tasksLoading}
            scroll={{ x: 1700 }}
            onChange={(_, filters) => {
              const nextStatus = filters.status?.[0]
              const nextValidation = filters.validation_success?.[0]
              setStatusFilter(typeof nextStatus === 'string' ? nextStatus : undefined)
              setValidationFilter(typeof nextValidation === 'string' ? nextValidation : undefined)
            }}
            pagination={{ pageSize: 20, showSizeChanger: true, showTotal: total => `共 ${total} 个任务` }}
          />
        </Card>
      </Space>

      <Drawer
        title={artifactTitle}
        open={artifactOpen}
        onClose={() => setArtifactOpen(false)}
        width="70%"
      >
        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{artifactContent}</pre>
      </Drawer>
    </div>
  )
}
