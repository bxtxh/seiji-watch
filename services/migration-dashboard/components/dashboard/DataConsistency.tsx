'use client'

import { Card, Title, Text, Flex, BarChart, Table, TableHead, TableRow, TableHeaderCell, TableBody, TableCell, Badge, DonutChart } from '@tremor/react'
import { CheckCircleIcon, ExclamationTriangleIcon, XCircleIcon } from '@heroicons/react/24/outline'

interface DataConsistencyProps {
  data?: {
    overall: number
    tables: Array<{
      name: string
      airtableCount: number
      supabaseCount: number
      consistency: number
      discrepancies: number
      lastChecked: string
    }>
    distribution: Array<{
      status: string
      count: number
    }>
  }
}

export function DataConsistency({ data }: DataConsistencyProps) {
  if (!data) return <Card><Text>Loading consistency data...</Text></Card>

  const getConsistencyIcon = (consistency: number) => {
    if (consistency >= 95) {
      return <CheckCircleIcon className="h-5 w-5 text-green-500" />
    } else if (consistency >= 90) {
      return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
    } else {
      return <XCircleIcon className="h-5 w-5 text-red-500" />
    }
  }

  const getConsistencyColor = (consistency: number): string => {
    if (consistency >= 95) return 'green'
    if (consistency >= 90) return 'yellow'
    return 'red'
  }

  const chartData = data.tables.map(table => ({
    name: table.name,
    'Airtable': table.airtableCount,
    'Supabase': table.supabaseCount,
    'Consistency %': table.consistency,
  }))

  return (
    <Card className="glass-effect">
      <Flex className="justify-between items-start mb-6">
        <div>
          <Title>Data Consistency</Title>
          <Text className="mt-1">Compare record counts between Airtable and Supabase</Text>
        </div>
        <div className="text-right">
          <Flex className="items-center gap-2 justify-end">
            {getConsistencyIcon(data.overall)}
            <Text className="text-3xl font-bold">
              {data.overall.toFixed(1)}%
            </Text>
          </Flex>
          <Text className="text-xs text-gray-500 mt-1">Overall Consistency</Text>
        </div>
      </Flex>

      {/* Distribution Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2">
          <Text className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">
            Record Count Comparison
          </Text>
          <BarChart
            className="h-64"
            data={chartData}
            index="name"
            categories={['Airtable', 'Supabase']}
            colors={['blue', 'purple']}
            yAxisWidth={48}
            showAnimation={true}
          />
        </div>
        
        <div>
          <Text className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">
            Consistency Distribution
          </Text>
          <DonutChart
            className="h-64"
            data={data.distribution}
            category="count"
            index="status"
            colors={['green', 'yellow', 'red']}
            showAnimation={true}
            showTooltip={true}
          />
        </div>
      </div>

      {/* Detailed Table */}
      <div>
        <Text className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">
          Table Details
        </Text>
        <div className="overflow-x-auto">
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>Table</TableHeaderCell>
                <TableHeaderCell className="text-right">Airtable</TableHeaderCell>
                <TableHeaderCell className="text-right">Supabase</TableHeaderCell>
                <TableHeaderCell className="text-right">Discrepancies</TableHeaderCell>
                <TableHeaderCell className="text-center">Consistency</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.tables.map((table) => (
                <TableRow key={table.name}>
                  <TableCell className="font-medium">{table.name}</TableCell>
                  <TableCell className="text-right">
                    {table.airtableCount.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right">
                    {table.supabaseCount.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right">
                    {table.discrepancies > 0 && (
                      <span className="text-red-600 font-medium">
                        {table.discrepancies}
                      </span>
                    )}
                    {table.discrepancies === 0 && (
                      <span className="text-green-600">0</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Flex className="justify-center items-center gap-2">
                      {getConsistencyIcon(table.consistency)}
                      <span className={`font-medium text-${getConsistencyColor(table.consistency)}-600`}>
                        {table.consistency.toFixed(1)}%
                      </span>
                    </Flex>
                  </TableCell>
                  <TableCell>
                    <Badge 
                      color={getConsistencyColor(table.consistency)}
                      size="sm"
                    >
                      {table.consistency >= 95 ? 'Synced' : table.consistency >= 90 ? 'Warning' : 'Critical'}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </Card>
  )
}