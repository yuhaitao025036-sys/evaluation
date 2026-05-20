import { useState, useEffect } from 'react'
import { Modal, Table, Button, message, Drawer, Descriptions, Tabs, Typography, Space, Tag } from 'antd'
import { ReloadOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons'
import { datasetsApi } from '@/api/datasets'
import { Dataset, DatasetInstance } from '@/types'
import type { ColumnsType } from 'antd/es/table'

interface Props {
  dataset: Dataset
  visible: boolean
  onClose: () => void
}

const formatValue = (value: any) => {
  if (value === null) return 'null'
  if (value === undefined) return 'undefined'
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

const getValueType = (value: any) => {
  if (value === null) return 'null'
  if (Array.isArray(value)) return 'array'
  return typeof value
}

export default function DatasetInstancesModal({ dataset, visible, onClose }: Props) {
  const [loading, setLoading] = useState(false)
  const [instances, setInstances] = useState<DatasetInstance[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [detailVisible, setDetailVisible] = useState(false)
  const [selectedInstance, setSelectedInstance] = useState<DatasetInstance | null>(null)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await datasetsApi.getInstances(dataset.id, { page, page_size: pageSize })
      setInstances(res.items)
      setTotal(res.total)
    } catch (error) {
      console.error('Failed to fetch instances:', error)
      message.error('获取实例列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (visible) {
      fetchData()
    }
  }, [visible, page, pageSize])

  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '此操作不可恢复，是否继续？',
      okText: '确认',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          await datasetsApi.deleteInstance(dataset.id, id)
          message.success('删除成功')
          fetchData()
        } catch (error) {
          console.error('Failed to delete instance:', error)
          message.error('后端当前未提供删除数据实例接口')
        }
      },
    })
  }

  const fieldRows = selectedInstance
    ? Object.entries(selectedInstance.data || {}).map(([field, value]) => ({
        field,
        type: getValueType(value),
        value,
      }))
    : []

  const fieldColumns: ColumnsType<{ field: string; type: string; value: any }> = [
    {
      title: '字段名',
      dataIndex: 'field',
      key: 'field',
      width: 180,
      fixed: 'left',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type) => <Tag>{type}</Tag>,
    },
    {
      title: '值预览',
      dataIndex: 'value',
      key: 'value',
      render: (value) => (
        <Typography.Paragraph
          copyable
          ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
          style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}
        >
          {formatValue(value)}
        </Typography.Paragraph>
      ),
    },
  ]

  const columns: ColumnsType<DatasetInstance> = [
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
      width: 220,
      ellipsis: true,
    },
    {
      title: '语言',
      dataIndex: 'repo_language',
      key: 'repo_language',
      width: 100,
      render: (value) => value || '-',
    },
    {
      title: '数据预览',
      dataIndex: 'data',
      key: 'data',
      render: (data) => (
        <div style={{ maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {JSON.stringify(data)}
        </div>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedInstance(record)
              setDetailVisible(true)
            }}
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <>
      <Modal
        title={`数据集实例：${dataset.name}`}
        open={visible}
        onCancel={onClose}
        width={1100}
        footer={null}
      >
        <div style={{ marginBottom: 16, textAlign: 'right' }}>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
            刷新
          </Button>
        </div>
        <Table
          columns={columns}
          dataSource={instances}
          loading={loading}
          rowKey="id"
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => {
              setPage(page)
              setPageSize(pageSize)
            },
          }}
          scroll={{ x: 950 }}
        />
      </Modal>

      <Drawer
        title="实例详情"
        open={detailVisible}
        onClose={() => {
          setDetailVisible(false)
          setSelectedInstance(null)
        }}
        width={760}
      >
        {selectedInstance && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="ID">{selectedInstance.id}</Descriptions.Item>
              <Descriptions.Item label="Dataset ID">{selectedInstance.dataset_id}</Descriptions.Item>
              <Descriptions.Item label="Instance ID">{selectedInstance.instance_id}</Descriptions.Item>
              <Descriptions.Item label="语言">{selectedInstance.repo_language || '-'}</Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {selectedInstance.created_at ? new Date(selectedInstance.created_at).toLocaleString('zh-CN') : '-'}
              </Descriptions.Item>
            </Descriptions>

            <Tabs
              items={[
                {
                  key: 'fields',
                  label: '字段预览',
                  children: (
                    <Table
                      columns={fieldColumns}
                      dataSource={fieldRows}
                      rowKey="field"
                      pagination={false}
                      size="small"
                      scroll={{ x: 650 }}
                    />
                  ),
                },
                {
                  key: 'json',
                  label: '完整 JSON',
                  children: (
                    <Typography.Paragraph copyable style={{ marginBottom: 0 }}>
                      <pre style={{ maxHeight: 520, overflow: 'auto', background: '#f5f5f5', padding: 12 }}>
                        {JSON.stringify(selectedInstance.data || {}, null, 2)}
                      </pre>
                    </Typography.Paragraph>
                  ),
                },
              ]}
            />
          </Space>
        )}
      </Drawer>
    </>
  )
}
