import { useState, useEffect } from 'react'
import { Modal, Table, Button, Space, message } from 'antd'
import { ReloadOutlined, DeleteOutlined } from '@ant-design/icons'
import { datasetsApi } from '@/api/datasets'
import { Dataset, DatasetInstance } from '@/types'
import type { ColumnsType } from 'antd/es/table'

interface Props {
  dataset: Dataset
  visible: boolean
  onClose: () => void
}

export default function DatasetInstancesModal({ dataset, visible, onClose }: Props) {
  const [loading, setLoading] = useState(false)
  const [instances, setInstances] = useState<DatasetInstance[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await datasetsApi.getInstances(dataset.id, { page, page_size: pageSize })
      setInstances(res.items)
      setTotal(res.total)
    } catch (error) {
      console.error('Failed to fetch instances:', error)
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
        }
      },
    })
  }

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
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 100,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          danger
          icon={<DeleteOutlined />}
          onClick={() => handleDelete(record.id)}
        >
          删除
        </Button>
      ),
    },
  ]

  return (
    <Modal
      title={`数据集实例：${dataset.name}`}
      open={visible}
      onCancel={onClose}
      width={1000}
      footer={null}
    >
      <div style={{ marginBottom: 16, textAlign: 'right' }}>
        <Button icon={<ReloadOutlined />} onClick={fetchData}>
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
        scroll={{ x: 800 }}
      />
    </Modal>
  )
}
