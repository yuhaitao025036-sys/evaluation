import { useState } from 'react'
import { Input, Alert } from 'antd'

const { TextArea } = Input

interface Props {
  value?: Record<string, any> | null
  onChange?: (value: Record<string, any> | null) => void
  placeholder?: string
}

export default function JsonEditor({ value, onChange, placeholder }: Props) {
  const [text, setText] = useState(value ? JSON.stringify(value, null, 2) : '')
  const [error, setError] = useState<string>('')

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newText = e.target.value
    setText(newText)

    if (!newText.trim()) {
      setError('')
      onChange?.(null)
      return
    }

    try {
      const parsed = JSON.parse(newText)
      setError('')
      onChange?.(parsed)
    } catch (err) {
      setError('JSON 格式错误')
    }
  }

  return (
    <div>
      <TextArea
        rows={4}
        value={text}
        onChange={handleChange}
        placeholder={placeholder}
        status={error ? 'error' : ''}
      />
      {error && (
        <Alert
          message={error}
          type="error"
          showIcon
          style={{ marginTop: 8 }}
        />
      )}
    </div>
  )
}
