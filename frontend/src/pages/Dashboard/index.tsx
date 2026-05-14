import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Space, Statistic, Row, Col, Select, message } from 'antd'
import { ReloadOutlined, PlayCircleOutlined, StopOutlined, RedoOutlined, EyeOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { taskGroupsApi } from '@/api/taskGroups'
import { comparisonsApi } from '@/api/comparisons'
import { modelsApi } from '@/api/models'
import { TaskGroup, TaskGroupStats } from '@/types'
import type { ColumnsType } from 'antd/es/table'

const statusColors: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
}

const statusLabels: Record<string, string> = {
  pending: '待执行',
  running: '执行中',
  completed: '已完成',
  failed: '失败',
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [taskGroups, setTaskGroups] = useState<TaskGroup[]>([])
  const [stats, setStats] = useState<TaskGroupStats | null>(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [filters, setFilters] = useState<{ status?: string; tag?: string; model?: string }>({})
  const [tags, setTags] = useState<string[]>([])
  const [models, setModels] = useState<string[]>([])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [groupsRes, statsRes] = await Promise.all([
        taskGroupsApi.list({ page, page_size: pageSize, ...filters }),
        taskGroupsApi.stats(),
      ])
      setTaskGroups(groupsRes.items)
      setTotal(groupsRes.total)
      setStats(statsRes)
    } catch (error) {
      console.error('Failed to fetch data:', error)
    } finally {
      setLoading(false)
    }
  }

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

  useEffect(() => {
    fetchData()
  }, [page, pageSize, filters])

  useEffect(() => {
    fetchFilters()
  }, [])

  const handleAction = async (id: number, action: 'start' | 'stop' | 'retry') => {
    try {
      if (action === 'start') {
        await taskGroupsApi.start(id)
        message.success('任务已启动')
      } else if (action === 'stop') {
        await taskGroupsApi.stop(id)
        message.success('任务已停止')
      } else if (action === 'retry') {
        await taskGroupsApi.retry(id)
        message.success('失败任务已重试')
      }
      fetchData()
    } catch (error) {
      console.error(`Failed to ${action} task:`, error)
    }
  }

  const columns: ColumnsType<TaskGroup> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '数据集',
      dataIndex: ['dataset', 'name'],
      key: 'dataset',
    },
    {
      title: '脚本',
      dataIndex: ['script', 'name'],
      key: 'script',
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
      title: '进度',
      key: 'progress',
      render: (_, record) => (
        <span>
          {record.completed_tasks} / {record.total_tasks}
          {record.failed_tasks > 0 && (
            <span style={{ color: '#ff4d4f', marginLeft: 8 }}>
              ({record.failed_tasks} 失败)
            </span>
          )}
        </span>
      ),
    },
    {
      title: '并发数',
      dataIndex: 'concurrency',
      key: 'concurrency',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/task/${record.id}`)}
          >
            查看
          </Button>
          {record.status === 'pending' && (
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleAction(record.id, 'start')}
            >
              启动
            </Button>
          )}
          {record.status === 'running' && (
            <Button
              type="link"
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() => handleAction(record.id, 'stop')}
            >
              停止
            </Button>
          )}
          {record.failed_tasks > 0 && (
            <Button
              type="link"
              size="small"
              icon={<RedoOutlined />}
              onClick={() => handleAction(record.id, 'retry')}
            >
              重试
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="总任务数" value={stats?.total || 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="执行中" value={stats?.running || 0} valueStyle={{ color: '#1890ff' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="已完成" value={stats?.completed || 0} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功率"
              value={stats?.success_rate || 0}
              precision={1}
              suffix="%"
              valueStyle={{ color: (stats?.success_rate || 0) > 80 ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="任务列表"
        extra={
          <Space>
            <Select
              placeholder="状态"
              style={{ width: 120 }}
              allowClear
              onChange={(value) => setFilters({ ...filters, status: value })}
            >
              <Select.Option value="pending">待执行</Select.Option>
              <Select.Option value="running">执行中</Select.Option>
              <Select.Option value="completed">已完成</Select.Option>
              <Select.Option value="failed">失败</Select.Option>
            </Select>
            <Select
              placeholder="标签"
              style={{ width: 150 }}
              allowClear
              onChange={(value) => setFilters({ ...filters, tag: value })}
            >
              {tags.map((tag) => (
                <Select.Option key={tag} value={tag}>
                  {tag}
                </Select.Option>
              ))}
            </Select>
            <Select
              placeholder="模型"
              style={{ width: 150 }}
              allowClear
              onChange={(value) => setFilters({ ...filters, model: value })}
            >
              {models.map((model) => (
                <Select.Option key={model} value={model}>
                  {model}
                </Select.Option>
              ))}
            </Select>
            <Button icon={<ReloadOutlined />} onClick={fetchData}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={taskGroups}
          loading={loading}
          rowKey="id"
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => {
              setPage(page)
              setPageSize(pageSize)
            },
          }}
          scroll={{ x: 1400 }}
        />
      </Card>
    </div>
  )
}
