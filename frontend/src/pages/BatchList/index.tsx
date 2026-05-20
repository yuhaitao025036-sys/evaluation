import { useState, useEffect } from 'react'
import { 
  Card, 
  Table, 
  Button, 
  Space, 
  Tag, 
  Progress, 
  Select, 
  Input, 
  message,
  Popconfirm,
  Typography 
} from 'antd'
import { 
  PlusOutlined, 
  PlayCircleOutlined, 
  PauseCircleOutlined, 
  ReloadOutlined,
  DeleteOutlined,
  EyeOutlined,
  PlusCircleOutlined 
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { batchesApi } from '@/api/batches'
import type { Batch } from '@/types'
import './index.css'

const { Search } = Input
const { Text } = Typography

export default function BatchList() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [batches, setBatches] = useState<Batch[]>([])
  const [filteredBatches, setFilteredBatches] = useState<Batch[]>([])
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [modelFilter, setModelFilter] = useState<string | undefined>()
  const [tagFilter, setTagFilter] = useState<string | undefined>()
  const [searchText, setSearchText] = useState('')

  useEffect(() => {
    fetchBatches()
  }, [])

  useEffect(() => {
    filterBatches()
  }, [batches, statusFilter, modelFilter, tagFilter, searchText])

  const fetchBatches = async () => {
    setLoading(true)
    try {
      const data = await batchesApi.list({ limit: 1000 })
      setBatches(data)
    } catch (error) {
      console.error('获取批次列表失败:', error)
      message.error('获取批次列表失败')
    } finally {
      setLoading(false)
    }
  }

  const filterBatches = () => {
    let filtered = [...batches]

    if (statusFilter) {
      filtered = filtered.filter(b => b.status === statusFilter)
    }
    if (modelFilter) {
      filtered = filtered.filter(b => b.model === modelFilter)
    }
    if (tagFilter) {
      filtered = filtered.filter(b => b.tag === tagFilter)
    }
    if (searchText) {
      filtered = filtered.filter(b => 
        b.batch_name.toLowerCase().includes(searchText.toLowerCase()) ||
        b.dataset?.name.toLowerCase().includes(searchText.toLowerCase())
      )
    }

    setFilteredBatches(filtered)
  }

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

  const handleDelete = async (batch: Batch) => {
    try {
      await batchesApi.delete(batch.id)
      message.success(`批次 "${batch.batch_name}" 已删除`)
      fetchBatches()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败')
    }
  }

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      created: { color: 'default', text: '已创建' },
      running: { color: 'processing', text: '运行中' },
      paused: { color: 'warning', text: '已暂停' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' }
    }
    const config = statusMap[status] || { color: 'default', text: status }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  const getCompletionRate = (batch: Batch) => {
    if (batch.total_tasks === 0) return 0
    const terminalTasks = batch.completed_tasks + batch.failed_tasks
    return Math.round((terminalTasks / batch.total_tasks) * 100)
  }

  const columns = [
    {
      title: '批次名称',
      dataIndex: 'batch_name',
      key: 'batch_name',
      width: 250,
      render: (text: string, record: Batch) => (
        <div>
          <div style={{ fontWeight: 500, marginBottom: 4 }}>{text}</div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.dataset?.name || `数据集 #${record.dataset_id}`}
          </Text>
        </div>
      )
    },
    {
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      width: 150,
      render: (text: string) => <Tag color="blue">{text}</Tag>
    },
    {
      title: '标签',
      dataIndex: 'tag',
      key: 'tag',
      width: 120,
      render: (text: string) => <Tag>{text}</Tag>
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status)
    },
    {
      title: '任务进度',
      key: 'progress',
      width: 350,
      render: (_: any, record: Batch) => {
        const terminalTasks = record.completed_tasks + record.failed_tasks
        const activeTasks = record.queued_tasks + record.running_tasks
        const completionRate = getCompletionRate(record)
        return (
          <div>
            <div style={{ marginBottom: 8 }}>
              <Progress
                percent={completionRate}
                success={{ percent: record.total_tasks ? Math.round((record.completed_tasks / record.total_tasks) * 100) : 0 }}
                status={record.failed_tasks > 0 ? 'exception' : undefined}
              />
            </div>
            <Space size="large" wrap>
              <Text type="secondary" style={{ fontSize: 12 }}>
                已结束 {terminalTasks}/{record.total_tasks}
              </Text>
              <Text type="success" style={{ fontSize: 12 }}>
                执行成功 {record.completed_tasks}
              </Text>
              {record.failed_tasks > 0 && (
                <Text type="danger" style={{ fontSize: 12 }}>
                  执行失败 {record.failed_tasks}
                </Text>
              )}
              {activeTasks > 0 && (
                <Text type="warning" style={{ fontSize: 12 }}>
                  运行中 {activeTasks}
                </Text>
              )}
              {record.pending_tasks > 0 && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  待执行 {record.pending_tasks}
                </Text>
              )}
            </Space>
          </div>
        )
      }
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => new Date(text).toLocaleString('zh-CN')
    },
    {
      title: '操作',
      key: 'actions',
      width: 280,
      fixed: 'right' as const,
      render: (_: any, record: Batch) => (
        <Space size="small" wrap>
          <Button 
            size="small" 
            icon={<EyeOutlined />}
            onClick={() => navigate(`/batches/${record.id}`)}
          >
            详情
          </Button>
          
          {record.status === 'created' && (
            <Button 
              size="small" 
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => handleStart(record)}
            >
              启动
            </Button>
          )}
          
          {record.status === 'running' && (
            <Button 
              size="small"
              icon={<PauseCircleOutlined />}
              onClick={() => handlePause(record)}
            >
              暂停
            </Button>
          )}
          
          {record.status === 'paused' && (
            <Button 
              size="small"
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => handleResume(record)}
            >
              恢复
            </Button>
          )}
          
          {record.failed_tasks > 0 && (
            <Button 
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleRetry(record)}
            >
              重试失败
            </Button>
          )}
          
          <Button 
            size="small"
            icon={<PlusCircleOutlined />}
            onClick={() => navigate(`/batches/create?append_to=${record.id}`)}
          >
            追加
          </Button>
          
          <Popconfirm
            title="确认删除"
            description={`确定要删除批次 "${record.batch_name}" 吗？此操作不可恢复。`}
            onConfirm={() => handleDelete(record)}
            okText="确认"
            cancelText="取消"
          >
            <Button 
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ]

  // 提取唯一的模型和标签列表
  const models = Array.from(new Set(batches.map(b => b.model)))
  const tags = Array.from(new Set(batches.map(b => b.tag)))

  return (
    <div className="batch-list-page">
      <Card>
        <div className="page-header">
          <div className="page-title">
            <h2>批次管理</h2>
            <Text type="secondary">管理和监控评测批次</Text>
          </div>
          <Button 
            type="primary" 
            icon={<PlusOutlined />}
            onClick={() => navigate('/batches/create')}
          >
            创建批次
          </Button>
        </div>

        <div className="filter-bar">
          <Space size="middle" wrap>
            <Select
              style={{ width: 150 }}
              placeholder="状态筛选"
              allowClear
              value={statusFilter}
              onChange={setStatusFilter}
            >
              <Select.Option value="created">已创建</Select.Option>
              <Select.Option value="running">运行中</Select.Option>
              <Select.Option value="paused">已暂停</Select.Option>
              <Select.Option value="completed">已完成</Select.Option>
              <Select.Option value="failed">失败</Select.Option>
            </Select>

            <Select
              style={{ width: 180 }}
              placeholder="模型筛选"
              allowClear
              value={modelFilter}
              onChange={setModelFilter}
            >
              {models.map(model => (
                <Select.Option key={model} value={model}>{model}</Select.Option>
              ))}
            </Select>

            <Select
              style={{ width: 150 }}
              placeholder="标签筛选"
              allowClear
              value={tagFilter}
              onChange={setTagFilter}
            >
              {tags.map(tag => (
                <Select.Option key={tag} value={tag}>{tag}</Select.Option>
              ))}
            </Select>

            <Search
              placeholder="搜索批次名称或数据集"
              style={{ width: 300 }}
              allowClear
              onSearch={setSearchText}
              onChange={e => setSearchText(e.target.value)}
            />
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={filteredBatches}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1500 }}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个批次`,
            defaultPageSize: 20,
            pageSizeOptions: ['10', '20', '50', '100']
          }}
        />
      </Card>
    </div>
  )
}
