import { useState, useEffect } from 'react'
import { Card, Table, Button, Space, Modal, message } from 'antd'
import { ReloadOutlined, SyncOutlined, DatabaseOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons'
import { datasetsApi } from '@/api/datasets'
import { Dataset } from '@/types'
import type { ColumnsType } from 'antd/es/table'
import DatasetInstancesModal from './DatasetInstancesModal'

export default function DatasetList() {
  const [loading, setLoading] = useState(false)
  const [scanLoading, setScanLoading] = useState(false)
  const [importLoading, setImportLoading] = useState(false)
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [importModalVisible, setImportModalVisible] = useState(false)
  const [instancesModalVisible, setInstancesModalVisible] = useState(false)
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await datasetsApi.list({ page, page_size: pageSize })
      setDatasets(res.items)
      setTotal(res.total)
    } catch (error) {
      console.error('Failed to fetch datasets:', error)
      message.error('获取数据集列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [page, pageSize])

  const handleScan = async () => {
    setScanLoading(true)
    try {
      const res = await datasetsApi.scan()
      const skippedText = typeof res.skipped_existing === 'number' ? `，跳过已存在 ${res.skipped_existing} 个` : ''
      message.success(`扫描完成，新增 ${res.newly_registered || 0} 个数据集${skippedText}`)
      fetchData()
    } catch (error) {
      console.error('Failed to scan datasets:', error)
      message.error('扫描数据目录失败，请检查后端数据目录配置')
    } finally {
      setScanLoading(false)
    }
  }

  const handleImport = async () => {
    if (!selectedDataset) return

    setImportLoading(true)
    try {
      const res = await datasetsApi.importInstances(selectedDataset.id)
      message.success(`成功导入 ${res.imported} 条实例${res.failed > 0 ? `，失败 ${res.failed} 条` : ''}`)
      setImportModalVisible(false)
      setSelectedDataset(null)
      fetchData()
    } catch (error) {
      console.error('Failed to import instances:', error)
      message.error('导入实例失败，请检查后端数据文件是否存在')
    } finally {
      setImportLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '删除数据集将同时删除其所有实例数据，此操作不可恢复，是否继续？',
      okText: '确认',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          await datasetsApi.delete(id)
          message.success('删除成功')
          fetchData()
        } catch (error) {
          console.error('Failed to delete dataset:', error)
          message.error('后端当前未提供删除数据集接口')
        }
      },
    })
  }

  const columns: ColumnsType<Dataset> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '文件名',
      dataIndex: 'file_name',
      key: 'file_name',
      render: (text) => text || '-',
    },
    {
      title: '格式',
      dataIndex: 'format',
      key: 'format',
      width: 90,
      render: (text) => text || '-',
    },
    {
      title: '实例数',
      key: 'instances',
      render: (_, record) => `${record.imported_instances || 0} / ${record.total_instances || 0}`,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 260,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedDataset(record)
              setInstancesModalVisible(true)
            }}
          >
            查看实例
          </Button>
          <Button
            type="link"
            size="small"
            icon={<DatabaseOutlined />}
            onClick={() => {
              setSelectedDataset(record)
              setImportModalVisible(true)
            }}
          >
            导入实例
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
      <Card
        title="数据集列表"
        extra={
          <Space>
            <Button type="primary" icon={<SyncOutlined />} loading={scanLoading} onClick={handleScan}>
              扫描数据目录
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
              刷新列表
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={datasets}
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
        />
      </Card>

      <Modal
        title="导入实例"
        open={importModalVisible}
        confirmLoading={importLoading}
        onCancel={() => {
          setImportModalVisible(false)
          setSelectedDataset(null)
        }}
        onOk={handleImport}
        okText="开始导入"
        cancelText="取消"
      >
        <p>
          将从后端已扫描的数据文件中读取实例并导入数据库。
        </p>
        <p style={{ color: '#666' }}>
          数据集：{selectedDataset?.name || '-'}；文件：{selectedDataset?.file_name || '-'}
        </p>
      </Modal>

      {selectedDataset && (
        <DatasetInstancesModal
          dataset={selectedDataset}
          visible={instancesModalVisible}
          onClose={() => {
            setInstancesModalVisible(false)
            setSelectedDataset(null)
          }}
        />
      )}
    </>
  )
}
