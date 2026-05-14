import { Card, Row, Col } from 'antd'
import { PlusOutlined, AppstoreAddOutlined } from '@ant-design/icons'
import './CreateModeSelector.css'

interface Props {
  onSelect: (mode: 'new' | 'append') => void
}

export default function CreateModeSelector({ onSelect }: Props) {
  return (
    <div className="create-mode-selector">
      <h3 style={{ textAlign: 'center', marginBottom: 32 }}>请选择创建模式</h3>
      
      <Row gutter={32} justify="center">
        <Col span={10}>
          <Card
            hoverable
            className="mode-card"
            onClick={() => onSelect('new')}
          >
            <div className="mode-icon new-batch">
              <PlusOutlined style={{ fontSize: 48 }} />
            </div>
            <h3>创建新批次</h3>
            <p>创建一个全新的评测批次，包含独立的配置和数据实例</p>
            <ul>
              <li>完整配置：数据集、脚本、模型、标签</li>
              <li>灵活选择数据实例</li>
              <li>独立的执行环境</li>
            </ul>
            <div className="mode-action">
              <span>选择此模式 →</span>
            </div>
          </Card>
        </Col>

        <Col span={10}>
          <Card
            hoverable
            className="mode-card"
            onClick={() => onSelect('append')}
          >
            <div className="mode-icon append-batch">
              <AppstoreAddOutlined style={{ fontSize: 48 }} />
            </div>
            <h3>追加到现有批次</h3>
            <p>向已有批次添加更多数据实例进行评测</p>
            <ul>
              <li>继承批次配置（模型、标签、脚本）</li>
              <li>添加新的数据实例</li>
              <li>支持重复检测和覆盖</li>
            </ul>
            <div className="mode-action">
              <span>选择此模式 →</span>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
