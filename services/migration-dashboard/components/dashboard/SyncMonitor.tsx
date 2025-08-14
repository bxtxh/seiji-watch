'use client'

import { Card, Title, Text, Flex, Badge, LineChart, List, ListItem } from '@tremor/react'
import { ArrowPathIcon, PauseIcon, PlayIcon } from '@heroicons/react/24/outline'
import { format } from 'date-fns'
import { motion } from 'framer-motion'

interface SyncMonitorProps {
  data?: {
    status: 'running' | 'stopped' | 'error'
    mode: 'incremental' | 'full' | 'real_time'
    queueSize: number
    syncRate: number // records per minute
    history: Array<{
      time: string
      records: number
      duration: number
    }>
    lastSync: {
      time: string
      tables: number
      records: number
      errors: number
    }
  }
}

export function SyncMonitor({ data }: SyncMonitorProps) {
  if (!data) return <Card><Text>Loading sync monitor...</Text></Card>

  const chartData = data.history.map((item) => ({
    time: format(new Date(item.time), 'HH:mm'),
    'Records Synced': item.records,
    'Duration (s)': item.duration,
  }))

  const statusColor = {
    running: 'green',
    stopped: 'gray',
    error: 'red',
  }[data.status]

  const modeColor = {
    incremental: 'blue',
    full: 'purple',
    real_time: 'emerald',
  }[data.mode]

  return (
    <Card className="h-full glass-effect">
      <Flex className="justify-between items-start mb-4">
        <div>
          <Title>Sync Monitor</Title>
          <Flex className="items-center gap-2 mt-2">
            <Badge color={statusColor} size="sm">
              <Flex className="items-center gap-1">
                {data.status === 'running' ? (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                  >
                    <ArrowPathIcon className="h-3 w-3" />
                  </motion.div>
                ) : data.status === 'stopped' ? (
                  <PauseIcon className="h-3 w-3" />
                ) : (
                  <XCircleIcon className="h-3 w-3" />
                )}
                {data.status}
              </Flex>
            </Badge>
            <Badge color={modeColor} size="sm">
              {data.mode.replace('_', ' ')}
            </Badge>
          </Flex>
        </div>
        
        <div className="text-right">
          <Text className="text-2xl font-bold text-blue-600">
            {data.syncRate}
          </Text>
          <Text className="text-xs text-gray-500">records/min</Text>
        </div>
      </Flex>

      {/* Sync Activity Chart */}
      <div className="mt-6">
        <Text className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
          Sync Activity (Last Hour)
        </Text>
        <LineChart
          className="h-32"
          data={chartData}
          index="time"
          categories={['Records Synced']}
          colors={['blue']}
          showLegend={false}
          showGridLines={false}
          showXAxis={false}
          showYAxis={false}
        />
      </div>

      {/* Queue Status */}
      <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <Flex className="justify-between items-center">
          <div>
            <Text className="text-sm font-medium">Queue Size</Text>
            <Text className="text-xs text-gray-500">Pending sync operations</Text>
          </div>
          <div className="text-right">
            <Text className="text-xl font-bold">
              {data.queueSize}
            </Text>
            {data.queueSize > 0 && (
              <div className="pulse-dot mt-1">
                <span className="pulse-dot::before bg-yellow-400"></span>
                <span className="pulse-dot::after bg-yellow-500"></span>
              </div>
            )}
          </div>
        </Flex>
      </div>

      {/* Last Sync Details */}
      <div className="mt-6">
        <Text className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">
          Last Sync
        </Text>
        <List className="space-y-2">
          <ListItem className="border-0 py-1">
            <Flex className="justify-between">
              <Text className="text-sm">Time</Text>
              <Text className="text-sm font-medium">
                {format(new Date(data.lastSync.time), 'HH:mm:ss')}
              </Text>
            </Flex>
          </ListItem>
          <ListItem className="border-0 py-1">
            <Flex className="justify-between">
              <Text className="text-sm">Tables</Text>
              <Text className="text-sm font-medium">
                {data.lastSync.tables}
              </Text>
            </Flex>
          </ListItem>
          <ListItem className="border-0 py-1">
            <Flex className="justify-between">
              <Text className="text-sm">Records</Text>
              <Text className="text-sm font-medium">
                {data.lastSync.records.toLocaleString()}
              </Text>
            </Flex>
          </ListItem>
          {data.lastSync.errors > 0 && (
            <ListItem className="border-0 py-1">
              <Flex className="justify-between">
                <Text className="text-sm text-red-600">Errors</Text>
                <Text className="text-sm font-medium text-red-600">
                  {data.lastSync.errors}
                </Text>
              </Flex>
            </ListItem>
          )}
        </List>
      </div>
    </Card>
  )
}