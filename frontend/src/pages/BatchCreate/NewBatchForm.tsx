import { useState, useEffect } from 'react'
import { Form, Input, Select, InputNumber, Button, Space, Divider, message } from 'antd'
import { datasetsApi } from '@/api/datasets'
import { scriptsApi } from '@/api/scripts'
import type { Dataset, Script, BatchCreateRequest } from '@/types'
import InstanceSelector from './InstanceSelector'
import ScriptParametersForm from './ScriptParametersForm'

interface Props {
  onSubmit: (data: BatchCreateRequest) => void
  loading: boolean
  onCancel: () => void
}

export default function NewBatchForm({ onSubmit, loading, onCancel }: Props) {
  const [form] = Form.useForm()
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [scripts, setScripts] = useState<Script[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null)
  const [selectedScript, setSelectedScript] = useState<Script | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    const [datasetsResult, scriptsResult] = await Promise.allSettled([
      datasetsApi.list({ page: 1, page_size: 1000 }),
      scriptsApi.list({ page: 1, page_size: 1000 })
    ])

    if (datasetsResult.status === 'fulfilled') {
      setDatasets(datasetsResult.value.items)
    } else {
      console.error('获取数据集失败:', datasetsResult.reason)
      message.error('获取数据集失败')
    }

    if (scriptsResult.status === 'fulfilled') {
      setScripts(scriptsResult.value.items)
      if (selectedScript) {
        setSelectedScript(scriptsResult.value.items.find(script => script.id === selectedScript.id) || null)
      }
    } else {
      console.error('获取脚本失败:', scriptsResult.reason)
      message.error('获取脚本失败')
    }
  }

  const handleSubmit = async (values: any) => {
    const data: BatchCreateRequest = {
      batch_name: values.batch_name,
      dataset_id: values.dataset_id,
      script_id: values.script_id,
      model: values.model,
      tag: values.tag,
      max_concurrency: values.max_concurrency || 10,
      max_retries: values.max_retries || 3,
      priority: values.priority || 0,
      execution_config: values.execution_config || {},
      ...values.instance_selection,
      append_to_existing: false
    }

    onSubmit(data)
  }

  const handleScriptChange = (scriptId: number) => {
    const script = scripts.find(script => script.id === scriptId) || null
    setSelectedScript(script)

    const defaults: Record<string, any> = {}
    for (const argument of script?.argument_schema || []) {
      defaults[argument.name] = argument.default
    }
    form.setFieldsValue({ execution_config: defaults })
  }

  // Ducc 支持的模型列表，可通过 ducc models 查看
  const commonModels = [
    'auto',
    'Kimi-K2.6',
    'MiniMax-M2.7',
    'GLM-5',
    'GLM-5.1',
    'GLM-5-Turbo',
    'gpt-5.5',
    'gpt-5.4',
    'gpt-5.3-codex',
    'Claude Haiku 4.5',
    'Claude Sonnet 4.5',
    'Claude Sonnet 4.6',
    'Claude Opus 4.5',
    'Claude Opus 4.6',
    'Kimi-K2.5',
    'MiniMax-M2-Stable',
    'MiniMax-M2.1',
    'DeepSeek-V4-Flash',
    'DeepSeek-V4-Pro'
  ]

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSubmit}
      initialValues={{
        max_concurrency: 10,
        max_retries: 3,
        priority: 0
      }}
    >
      <Divider orientation="left">基本信息</Divider>
      
      <Form.Item
        name="batch_name"
        label="批次名称"
        rules={[{ required: true, message: '请输入批次名称' }]}
        extra="建议命名格式：{模型}-{数据集}-{标签}，例如：gpt4-swebench-baseline"
      >
        <Input placeholder="例如：gpt4-swebench-baseline" />
      </Form.Item>

      <Divider orientation="left">评测配置</Divider>

      <Form.Item
        name="dataset_id"
        label="数据集"
        rules={[{ required: true, message: '请选择数据集' }]}
      >
        <Select 
          placeholder="请选择数据集"
          showSearch
          optionFilterProp="children"
          onChange={setSelectedDatasetId}
        >
          {datasets.map(dataset => {
            const imported = dataset.imported_instances ?? 0
            const total = dataset.total_instances ?? 0
            return (
              <Select.Option key={dataset.id} value={dataset.id} disabled={imported === 0}>
                {dataset.name}（已导入 {imported} / 总数 {total}）{imported === 0 ? ' - 请先导入实例' : ''}
              </Select.Option>
            )
          })}
        </Select>
      </Form.Item>

      <Form.Item
        name="script_id"
        label="评测脚本"
        rules={[{ required: true, message: '请选择评测脚本' }]}
      >
        <Select placeholder="请选择评测脚本" onChange={handleScriptChange}>
          {scripts.map(script => (
            <Select.Option key={script.id} value={script.id}>
              {script.file_name || script.name || script.file_path}
            </Select.Option>
          ))}
        </Select>
      </Form.Item>

      {selectedScript && (
        <>
          <Divider orientation="left">脚本参数</Divider>
          <ScriptParametersForm argumentsSchema={selectedScript.argument_schema || []} />
        </>
      )}

      <Form.Item
        name="model"
        label="模型"
        rules={[{ required: true, message: '请输入模型名称' }]}
        extra="当前模型列表来自 Ducc Agent，可通过 ducc models 查看；后续接入千帆等平台后，可在此选择对应平台支持的模型，用于结果对比"
      >
        <Select
          placeholder="请选择模型名称"
          showSearch
          allowClear
          optionFilterProp="children"
        >
          {commonModels.map(model => (
            <Select.Option key={model} value={model}>
              {model}
            </Select.Option>
          ))}
        </Select>
      </Form.Item>

      <Form.Item
        name="tag"
        label="标签"
        rules={[{ required: true, message: '请输入标签' }]}
        extra="用于区分不同的实验，例如：baseline, experiment-1, optimized"
      >
        <Input placeholder="例如：baseline" />
      </Form.Item>

      <Form.Item
        name="max_concurrency"
        label="最大并发数"
        extra="同时运行的任务数量，建议根据系统资源设置"
      >
        <InputNumber min={1} max={100} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item
        name="max_retries"
        label="最大重试次数"
        extra="任务失败后的自动重试次数"
      >
        <InputNumber min={0} max={10} style={{ width: '100%' }} />
      </Form.Item>

      <Divider orientation="left">选择数据实例</Divider>

      <Form.Item
        name="instance_selection"
        rules={[{ required: true, message: '请选择数据实例' }]}
      >
        <InstanceSelector datasetId={selectedDatasetId} />
      </Form.Item>

      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={loading} size="large">
            创建批次
          </Button>
          <Button onClick={onCancel} size="large">
            取消
          </Button>
        </Space>
      </Form.Item>
    </Form>
  )
}
