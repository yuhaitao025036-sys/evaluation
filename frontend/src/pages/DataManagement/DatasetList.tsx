import { useState, useEffect } from 'react'
import { Card, Table, Button, Space, Modal, Form, Input, message, Upload } from 'antd'
import { PlusOutlined, ReloadOutlined, UploadOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons'
import { datasetsApi } from '@/api/datasets'
import { Dataset } from '@/types'
import type { ColumnsType } from 'antd/es/table'
import type { UploadFile } from 'antd/es/upload/interface'
import DatasetInstancesModal from './DatasetInstancesModal'

export default function DatasetList() {
  const [loading, setLoading] = useState(false)
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [importModalVisible, setImportModalVisible] = useState(false)
  const [instancesModalVisible, setInstancesModalVisible] = useState(false)
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null)
  const [form] = Form.useForm()
  const [importForm] = Form.useForm()

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await datasetsApi.list({ page, page_size: pageSize })
      setDatasets(res.items)
      setTotal(res.total)
    } catch (error) {
      console.error('Failed to fetch datasets:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [page, pageSize])

  const handleCreate = async (values: { name: string; description?: string }) => {
    try {
      await datasetsApi.create(values)
      message.success('创建成功')
      setCreateModalVisible(false)
      form.resetFields()
      fetchData()
    } catch (error) {
      console.error('Failed to create dataset:', error)
    }
  }

  const handleImport = async (values: { file: UploadFile[] }) => {
    if (!selectedDataset || !values.file || values.file.length === 0) return
    
    try {
      const file = values.file[0].originFileObj as File
      const res = await datasetsApi.importInstances(selectedDataset.id, file)
      message.success(`成功导入 ${res.imported} 条数据${res.failed > 0 ? `，失败 ${res.failed} 条` : ''}`)
      setImportModalVisible(false)
      importForm.resetFields()
      fetchData()
    } catch (error) {
      console.error('Failed to import instances:', error)
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
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (text) => text || '-',
    },
    {
      title: '实例数',
      dataIndex: 'instance_count',
      key: 'instance_count',
      render: (count) => count || 0,
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
      width: 250,
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
            icon={<UploadOutlined />}
            onClick={() => {
              setSelectedDataset(record)
              setImportModalVisible(true)
            }}
          >
            导入数据
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
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
              新建数据集
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchData}>
              刷新
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
        title="新建数据集"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false)
          form.resetFields()
        }}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入数据集名称' }]}
          >
            <Input placeholder="请输入数据集名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="请输入数据集描述" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="导入数据"
        open={importModalVisible}
        onCancel={() => {
          setImportModalVisible(false)
          importForm.resetFields()
        }}
        onOk={() => importForm.submit()}
      >
        <Form form={importForm} layout="vertical" onFinish={handleImport}>
          <Form.Item
            name="file"
            label="JSONL 文件"
            valuePropName="fileList"
            getValueFromEvent={(e) => {
              if (Array.isArray(e)) return e
              return e?.fileList
            }}
            rules={[{ required: true, message: '请选择文件' }]}
          >
            <Upload
              accept=".jsonl"
              maxCount={1}
              beforeUpload={() => false}
            >
              <Button icon={<UploadOutlined />}>选择文件</Button>
            </Upload>
          </Form.Item>
          <div style={{ color: '#999', fontSize: 12 }}>
            文件格式：每行一个 JSON 对象，需包含 instance_id 字段
          </div>
        </Form>
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
