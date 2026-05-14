import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Button, Space, Table, Progress, message, Tabs } from 'antd'
import { useParams, useNavigate } from 'react-router-dom'
import { PlayCircleOutlined, StopOutlined, RedoOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { taskGroupsApi } from '@/api/taskGroups'
import { taskInstancesApi } from '@/api/taskInstances'
import { TaskGroup, Task, TaskInstance } from '@/types'
import type { ColumnsType } from 'antd/es/table'

const statusColors: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
  timeout: 'warning',
}

const statusLabels: Record<string, string> = {
  pending: '待执行',
  running: '执行中',
  completed: '已完成',
  failed: '失败',
  timeout: '超时',
}

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [taskGroup, setTaskGroup] = useState<TaskGroup | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [instances, setInstances] = useState<TaskInstance[]>([])
  const [instancesTotal, setInstancesTotal] = useState(0)
  const [instancesPage, setInstancesPage] = useState(1)
  const [instancesPageSize, setInstancesPageSize] = useState(10)
  const [stats, setStats] = useState<any>(null)

  const fetchData = async () => {
    if (!id) return
    setLoading(true)
    try {
      const [groupRes, tasksRes, instancesRes, statsRes] = await Promise.all([
        taskGroupsApi.get(Number(id)),
        taskGroupsApi.getTasks(Number(id)),
        taskInstancesApi.list({ page: instancesPage, page_size: instancesPageSize, task_id: Number(id) }),
        taskInstancesApi.stats({ task_id: Number(id) }),
      ])
      setTaskGroup(groupRes)
      setTasks(tasksRes.items)
      setInstances(instancesRes.items)
      setInstancesTotal(instancesRes.total)
      setStats(statsRes)
    } catch (error) {
      console.error('Failed to fetch task detail:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [id, instancesPage, instancesPageSize])

  const handleAction = async (action: 'start' | 'stop' | 'retry') => {
    if (!id) return
    try {
      if (action === 'start') {
        await taskGroupsApi.start(Number(id))
        message.success('任务已启动')
      } else if (action === 'stop') {
        await taskGroupsApi.stop(Number(id))
        message.success('任务已停止')
      } else if (action === 'retry') {
        await taskGroupsApi.retry(Number(id))
        message.success('失败任务已重试')
      }
      fetchData()
    } catch (error) {
      console.error(`Failed to ${action} task:`, error)
    }
  }

  const handleRetryInstance = async (instanceId: number) => {
    try {
      await taskInstancesApi.retry(instanceId)
      message.success('实例已重试')
      fetchData()
    } catch (error) {
      console.error('Failed to retry instance:', error)
    }
  }

  const taskColumns: ColumnsType<Task> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '批次索引',
      dataIndex: 'batch_index',
      key: 'batch_index',
    },
    {
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      render: (model: string | null) => model ? <Tag color="green">{model}</Tag> : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={statusColors[status]}>{statusLabels[status]}</Tag>
      ),
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (time: string | null) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      render: (time: string | null) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
  ]

  const instanceColumns: ColumnsType<TaskInstance> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: 'Instance ID',
      dataIndex: 'instance_id',
      key: 'instance_id',
    },
    {
      title: '标签',
      dataIndex: 'tag',
      key: 'tag',
      render: (tag: string) => <Tag color="blue">{tag}</Tag>,
    },
    {
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      render: (model: string | null) => model ? <Tag color="green">{model}</Tag> : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={statusColors[status]}>{statusLabels[status]}</Tag>
      ),
    },
    {
      title: '耗时',
      dataIndex: 'duration',
      key: 'duration',
      render: (duration: number | null) => duration ? `${duration.toFixed(2)}s` : '-',
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      key: 'error_message',
      render: (error: string | null) => error ? (
        <div style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#ff4d4f' }}>
          {error}
        </div>
      ) : '-',
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 100,
      render: (_, record) => (
        record.status === 'failed' || record.status === 'timeout' ? (
          <Button
            type="link"
            size="small"
            icon={<RedoOutlined />}
            onClick={() => handleRetryInstance(record.id)}
          >
            重试
          </Button>
        ) : null
      ),
    },
  ]

  if (!taskGroup) {
    return <Card loading={loading}>加载中...</Card>
  }

  const progress = taskGroup.total_tasks > 0
    ? Math.round((taskGroup.completed_tasks / taskGroup.total_tasks) * 100)
    : 0

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboard')}>
          返回
        </Button>
        {taskGroup.status === 'pending' && (
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => handleAction('start')}
          >
            启动任务
          </Button>
        )}
        {taskGroup.status === 'running' && (
          <Button
            danger
            icon={<StopOutlined />}
            onClick={() => handleAction('stop')}
          >
            停止任务
          </Button>
        )}
        {taskGroup.failed_tasks > 0 && (
          <Button
            icon={<RedoOutlined />}
            onClick={() => handleAction('retry')}
          >
            重试失败任务
          </Button>
        )}
      </Space>

      <Card title="任务详情" style={{ marginBottom: 16 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="任务名称">{taskGroup.name}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={statusColors[taskGroup.status]}>{statusLabels[taskGroup.status]}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="数据集">{taskGroup.dataset?.name}</Descriptions.Item>
          <Descriptions.Item label="脚本">{taskGroup.script?.name}</Descriptions.Item>
          <Descriptions.Item label="标签">
            <Tag color="blue">{taskGroup.tag}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="模型">
            {taskGroup.model ? <Tag color="green">{taskGroup.model}</Tag> : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="并发数">{taskGroup.concurrency}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {new Date(taskGroup.created_at).toLocaleString('zh-CN')}
          </Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>
            {taskGroup.description || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="过滤条件" span={2}>
            {taskGroup.filter_conditions ? (
              <pre style={{ margin: 0 }}>{JSON.stringify(taskGroup.filter_conditions, null, 2)}</pre>
            ) : '-'}
          </Descriptions.Item>
        </Descriptions>

        <div style={{ marginTop: 24 }}>
          <div style={{ marginBottom: 8 }}>
            执行进度：{taskGroup.completed_tasks} / {taskGroup.total_tasks}
            {taskGroup.failed_tasks > 0 && (
              <span style={{ color: '#ff4d4f', marginLeft: 16 }}>
                失败：{taskGroup.failed_tasks}
              </span>
            )}
          </div>
          <Progress
            percent={progress}
            status={taskGroup.status === 'failed' ? 'exception' : taskGroup.status === 'completed' ? 'success' : 'active'}
          />
        </div>

        {stats && (
          <div style={{ marginTop: 24 }}>
            <Space size="large">
              <span>成功率：<strong>{stats.success_rate.toFixed(1)}%</strong></span>
              <span>平均耗时：<strong>{stats.avg_duration ? `${stats.avg_duration.toFixed(2)}s` : '-'}</strong></span>
              <span>待执行：<strong>{stats.pending}</strong></span>
              <span>执行中：<strong style={{ color: '#1890ff' }}>{stats.running}</strong></span>
              <span>已完成：<strong style={{ color: '#52c41a' }}>{stats.completed}</strong></span>
              <span>失败：<strong style={{ color: '#ff4d4f' }}>{stats.failed}</strong></span>
              <span>超时：<strong style={{ color: '#faad14' }}>{stats.timeout}</strong></span>
            </Space>
          </div>
        )}
      </Card>

      <Card>
        <Tabs
          items={[
            {
              key: 'instances',
              label: '任务实例',
              children: (
                <Table
                  columns={instanceColumns}
                  dataSource={instances}
                  loading={loading}
                  rowKey="id"
                  pagination={{
                    current: instancesPage,
                    pageSize: instancesPageSize,
                    total: instancesTotal,
                    showSizeChanger: true,
                    showTotal: (total) => `共 ${total} 条`,
                    onChange: (page, pageSize) => {
                      setInstancesPage(page)
                      setInstancesPageSize(pageSize)
                    },
                  }}
                  scroll={{ x: 1200 }}
                />
              ),
            },
            {
              key: 'tasks',
              label: '子任务',
              children: (
                <Table
                  columns={taskColumns}
                  dataSource={tasks}
                  loading={loading}
                  rowKey="id"
                  pagination={false}
                />
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}
