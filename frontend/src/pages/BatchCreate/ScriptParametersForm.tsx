import { Checkbox, Empty, Form, Input, InputNumber, Select } from 'antd'
import type { ScriptArgument } from '@/types'

interface Props {
  argumentsSchema?: ScriptArgument[]
}

export default function ScriptParametersForm({ argumentsSchema = [] }: Props) {
  if (argumentsSchema.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="该脚本未识别到可配置参数" />
  }

  return (
    <>
      {argumentsSchema.map((argument) => (
        <Form.Item
          key={argument.name}
          name={['execution_config', argument.name]}
          label={argument.cli_name || argument.name}
          valuePropName={argument.type === 'boolean' ? 'checked' : 'value'}
          rules={[{ required: argument.required, message: `请配置 ${argument.cli_name || argument.name}` }]}
          extra={argument.help}
        >
          {renderInput(argument)}
        </Form.Item>
      ))}
    </>
  )
}

function renderInput(argument: ScriptArgument) {
  if (argument.type === 'boolean') {
    return <Checkbox>启用</Checkbox>
  }

  if (argument.type === 'int') {
    return <InputNumber precision={0} style={{ width: '100%' }} />
  }

  if (argument.type === 'float') {
    return <InputNumber style={{ width: '100%' }} />
  }

  if (argument.type === 'choice') {
    return (
      <Select placeholder={`请选择 ${argument.cli_name || argument.name}`}>
        {(argument.choices || []).map((choice) => (
          <Select.Option key={choice} value={choice}>
            {choice}
          </Select.Option>
        ))}
      </Select>
    )
  }

  return <Input placeholder={`请输入 ${argument.cli_name || argument.name}`} />
}
