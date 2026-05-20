import { useState, useEffect } from 'react'
import { Card, Table, Button, Space, message, Tag } from 'antd'
import { ReloadOutlined, SyncOutlined } from '@ant-design/icons'
import { scriptsApi } from '@/api/scripts'
import { Script } from '@/types'
import type { ColumnsType } from 'antd/es/table'

export default function ScriptList() {
  const [loading, setLoading] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [scripts, setScripts] = useState<Script[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await scriptsApi.list({ page, page_size: pageSize })
      setScripts(res.items)
      setTotal(res.total)
    } catch (error) {
      console.error('Failed to fetch scripts:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [page, pageSize])

  const handleScan = async () => {
    setScanning(true)
    try {
      const res = await scriptsApi.scan()
      message.success(`扫描完成，新增 ${res.registered_count} 个脚本，更新 ${res.updated_count} 个脚本，删除 ${res.deleted_count} 个失效脚本`)
      fetchData()
    } catch (error) {
      console.error('Failed to scan scripts:', error)
    } finally {
      setScanning(false)
    }
  }

  const columns: ColumnsType<Script> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '名称',
      key: 'file_name',
      render: (_, record) => record.file_name || record.name || '-',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (text) => text || '-',
    },
    {
      title: '参数数',
      key: 'argument_count',
      width: 90,
      render: (_, record) => record.argument_schema?.length || 0,
    },
    {
      title: '文件路径',
      dataIndex: 'file_path',
      key: 'file_path',
      render: (path) => <Tag color="blue">{path}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
  ]

  return (
    <Card
      title="脚本列表"
      extra={
        <Space>
          <Button type="primary" icon={<SyncOutlined />} loading={scanning} onClick={handleScan}>
            扫描脚本
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchData}>
            刷新
          </Button>
        </Space>
      }
    >
      <div style={{ marginBottom: 16, color: '#999' }}>
        脚本文件存放在 backend/data/scripts 目录下，点击"扫描脚本"自动导入
      </div>
      <Table
        columns={columns}
        dataSource={scripts}
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
  )
}
