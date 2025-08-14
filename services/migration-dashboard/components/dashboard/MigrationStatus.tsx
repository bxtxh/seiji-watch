'use client'

import { Card, Title, Text, Flex, ProgressBar, List, ListItem, Badge } from '@tremor/react'
import { CheckCircleIcon, ClockIcon, XCircleIcon } from '@heroicons/react/24/outline'
import { format } from 'date-fns'

interface MigrationStatusProps {
  data?: {
    tables: Array<{
      name: string
      airtableCount: number
      supabaseCount: number
      status: 'completed' | 'in_progress' | 'pending' | 'failed'
      lastSync?: string
      progress: number
    }>
    overall: {
      totalTables: number
      completedTables: number
      totalRecords: number
      migratedRecords: number
    }
  }
}

export function MigrationStatus({ data }: MigrationStatusProps) {
  if (!data) return <Card><Text>Loading migration status...</Text></Card>

  const overallProgress = (data.overall.migratedRecords / data.overall.totalRecords) * 100

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'in_progress':
        return <ClockIcon className="h-5 w-5 text-yellow-500 animate-pulse" />
      case 'failed':
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'green'
      case 'in_progress': return 'yellow'
      case 'failed': return 'red'
      default: return 'gray'
    }
  }

  return (
    <Card className="h-full glass-effect">
      <Flex className="justify-between items-start mb-4">
        <div>
          <Title>Migration Status</Title>
          <Text className="mt-1">
            {data.overall.completedTables} of {data.overall.totalTables} tables migrated
          </Text>
        </div>
        <Badge color={overallProgress === 100 ? 'green' : 'blue'}>
          {overallProgress.toFixed(1)}%
        </Badge>
      </Flex>

      <ProgressBar 
        value={overallProgress} 
        color={overallProgress === 100 ? 'green' : 'blue'}
        className="mb-6"
      />

      <div className="space-y-4">
        <Text className="font-medium text-sm text-gray-600 dark:text-gray-400">
          Table Status
        </Text>
        
        <List className="space-y-3">
          {data.tables.map((table) => (
            <ListItem key={table.name} className="border-0">
              <Flex className="justify-between items-center w-full">
                <Flex className="items-center gap-3">
                  {getStatusIcon(table.status)}
                  <div>
                    <Text className="font-medium">{table.name}</Text>
                    <Text className="text-xs text-gray-500">
                      {table.supabaseCount.toLocaleString()} / {table.airtableCount.toLocaleString()} records
                    </Text>
                  </div>
                </Flex>
                
                <div className="text-right">
                  <Badge color={getStatusColor(table.status)} size="sm">
                    {table.status.replace('_', ' ')}
                  </Badge>
                  {table.lastSync && (
                    <Text className="text-xs text-gray-500 mt-1">
                      {format(new Date(table.lastSync), 'HH:mm:ss')}
                    </Text>
                  )}
                </div>
              </Flex>
              
              {table.status === 'in_progress' && (
                <ProgressBar 
                  value={table.progress} 
                  color="blue" 
                  className="mt-2"
                />
              )}
            </ListItem>
          ))}
        </List>
      </div>

      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <Flex className="justify-between">
          <Text className="text-sm">
            Total Records
          </Text>
          <Text className="text-sm font-medium">
            {data.overall.migratedRecords.toLocaleString()} / {data.overall.totalRecords.toLocaleString()}
          </Text>
        </Flex>
      </div>
    </Card>
  )
}