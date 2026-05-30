// 按需注册 ECharts 模块，控制打包体积。在使用 <VChart> 的视图中 side-effect 引入本文件即可。
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DatasetComponent,
} from 'echarts/components'

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DatasetComponent,
])

// 暗色主题调色板（与 style.css 设计变量保持一致）
export const CHART = {
  brand: '#c96442',
  brandLight: '#d97757',
  textBody: '#b0aea5',
  textMuted: '#87867f',
  textDim: '#5e5d59',
  border: '#3d3d3a',
  surface: '#30302e',
  bg: '#141413',
  error: '#b53333',
}

// 通用 tooltip 样式
export const TOOLTIP_STYLE = {
  backgroundColor: '#1f1f1d',
  borderColor: CHART.border,
  borderWidth: 1,
  textStyle: { color: CHART.textBody, fontSize: 12 },
}
