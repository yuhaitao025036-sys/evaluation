import { useState, useEffect } from 'react'
import { Card, Steps, Button, message } from 'antd'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeftOutlined } from '@ant-design/icons'
import CreateModeSelector from './CreateModeSelector'
import NewBatchForm from './NewBatchForm'
import AppendBatchForm from './AppendBatchForm'
import { batchesApi } from '@/api/batches'
import type { BatchAddTasksRequest, BatchCreateRequest } from '@/types'
import './index.css'

type CreateMode = 'new' | 'append' | null

export default function BatchCreate() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [mode, setMode] = useState<CreateMode>(null)
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  
  // 如果 URL 带有 append_to 参数，直接进入追加模式
  useEffect(() => {
    const appendTo = searchParams.get('append_to')
    if (appendTo) {
      setMode('append')
      setCurrentStep(1)
    }
  }, [searchParams])

  const handleModeSelect = (selectedMode: 'new' | 'append') => {
    setMode(selectedMode)
    setCurrentStep(1)
  }

  const handleBack = () => {
    if (currentStep === 1) {
      setMode(null)
      setCurrentStep(0)
    } else {
      navigate('/batches')
    }
  }

  const handleSubmit = async (data: BatchCreateRequest) => {
    setLoading(true)
    try {
      const result = await batchesApi.create(data)
      message.success(result.message)

      // 显示创建统计
      const { stats } = result.data
      if (stats.skipped > 0) {
        message.info(`跳过 ${stats.skipped} 个已存在的实例`)
      }
      if (stats.overwritten > 0) {
        message.warning(`覆盖 ${stats.overwritten} 个已存在的实例`)
      }

      // 询问是否启动
      const shouldStart = window.confirm(
        `批次创建成功，共 ${stats.total} 个任务。\n\n是否立即启动批次？`
      )

      if (shouldStart) {
        await batchesApi.start(result.data.batch_id)
        message.success('批次已启动')
      }

      navigate(`/batches/${result.data.batch_id}`)
    } catch (error: any) {
      console.error('创建批次失败:', error)
      message.error(error.response?.data?.detail || '创建批次失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAppendSubmit = async (batchId: number, data: BatchAddTasksRequest) => {
    setLoading(true)
    try {
      const stats = await batchesApi.addTasks(batchId, data)
      message.success(`已追加 ${stats.total} 个任务`)
      if (stats.skipped > 0) {
        message.info(`跳过 ${stats.skipped} 个已存在的实例`)
      }
      if (stats.overwritten > 0) {
        message.warning(`覆盖 ${stats.overwritten} 个已存在的实例`)
      }

      if (stats.total > 0) {
        const shouldStart = window.confirm(`已追加 ${stats.total} 个任务。\n\n是否立即启动批次？`)
        if (shouldStart) {
          await batchesApi.start(batchId, true)
          message.success('批次已启动')
        }
      }

      navigate(`/batches/${batchId}`)
    } catch (error: any) {
      console.error('追加任务失败:', error)
      message.error(error.response?.data?.detail || '追加任务失败')
    } finally {
      setLoading(false)
    }
  }

  const steps = [
    {
      title: '选择模式',
      description: '新建或追加'
    },
    {
      title: '配置批次',
      description: mode === 'new' ? '填写批次信息' : '选择目标批次'
    }
  ]

  return (
    <div className="batch-create-page">
      <Card>
        <div className="page-header">
          <Button 
            icon={<ArrowLeftOutlined />}
            onClick={handleBack}
          >
            返回
          </Button>
          <h2>{mode === 'new' ? '创建新批次' : mode === 'append' ? '追加任务到现有批次' : '创建批次'}</h2>
        </div>

        <Steps 
          current={currentStep} 
          items={steps}
          style={{ marginBottom: 32 }}
        />

        {currentStep === 0 && (
          <CreateModeSelector onSelect={handleModeSelect} />
        )}

        {currentStep === 1 && mode === 'new' && (
          <NewBatchForm 
            onSubmit={handleSubmit}
            loading={loading}
            onCancel={handleBack}
          />
        )}

        {currentStep === 1 && mode === 'append' && (
          <AppendBatchForm
            initialBatchId={searchParams.get('append_to')}
            onSubmit={handleAppendSubmit}
            loading={loading}
            onCancel={handleBack}
          />
        )}
      </Card>
    </div>
  )
}
