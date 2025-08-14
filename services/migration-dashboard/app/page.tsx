'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Card, Grid, Text, Metric, Flex, ProgressBar, Badge } from '@tremor/react'
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  CloudArrowUpIcon,
  ServerStackIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { MigrationStatus } from '@/components/dashboard/MigrationStatus'
import { SyncMonitor } from '@/components/dashboard/SyncMonitor'
import { DataConsistency } from '@/components/dashboard/DataConsistency'
import { SystemHealth } from '@/components/dashboard/SystemHealth'
import { AlertsPanel } from '@/components/dashboard/AlertsPanel'
import { MigrationControl } from '@/components/dashboard/MigrationControl'
import { useMigrationStore } from '@/stores/migrationStore'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export default function DashboardPage() {
  const { phase, status, metrics } = useMigrationStore()
  const [isClient, setIsClient] = useState(false)

  useEffect(() => {
    setIsClient(true)
  }, [])

  // Fetch dashboard data
  const { data: dashboardData, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: api.getDashboard,
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  if (!isClient) return null

  const stats = [
    {
      title: 'Migration Phase',
      metric: `Phase ${phase}`,
      icon: CloudArrowUpIcon,
      color: 'blue',
      progress: phase === 1 ? 33 : phase === 2 ? 66 : 100,
    },
    {
      title: 'Sync Status',
      metric: status === 'running' ? 'Active' : 'Stopped',
      icon: ArrowPathIcon,
      color: status === 'running' ? 'green' : 'gray',
      badge: status === 'running' ? 'Live' : 'Offline',
    },
    {
      title: 'Data Consistency',
      metric: `${metrics?.consistency || 0}%`,
      icon: CheckCircleIcon,
      color: metrics?.consistency >= 95 ? 'green' : 'yellow',
      progress: metrics?.consistency || 0,
    },
    {
      title: 'Active Alerts',
      metric: dashboardData?.alerts?.length || 0,
      icon: ExclamationTriangleIcon,
      color: dashboardData?.alerts?.length > 0 ? 'red' : 'green',
      badge: dashboardData?.alerts?.length > 0 ? 'Attention' : 'Clear',
    },
  ]

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Flex className="justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Migration Dashboard
              </h1>
              <Text className="mt-2">
                Monitor and control the Airtable to Supabase migration
              </Text>
            </div>
            <MigrationControl />
          </Flex>
        </motion.div>

        {/* Stats Grid */}
        <Grid numItemsLg={4} className="gap-6">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <Card className="card-hover glass-effect">
                <Flex className="justify-between items-start">
                  <div className="space-y-2">
                    <Flex className="items-center gap-2">
                      <stat.icon className="h-5 w-5 text-gray-500" />
                      <Text>{stat.title}</Text>
                    </Flex>
                    <Metric className={`text-${stat.color}-600`}>
                      {stat.metric}
                    </Metric>
                    {stat.progress !== undefined && (
                      <ProgressBar
                        value={stat.progress}
                        color={stat.color}
                        className="mt-2"
                      />
                    )}
                  </div>
                  {stat.badge && (
                    <Badge color={stat.color} size="sm">
                      {stat.badge}
                    </Badge>
                  )}
                </Flex>
              </Card>
            </motion.div>
          ))}
        </Grid>

        {/* Main Content Grid */}
        <Grid numItemsLg={2} className="gap-6">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.4 }}
          >
            <MigrationStatus data={dashboardData?.migration} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.5 }}
          >
            <SyncMonitor data={dashboardData?.sync} />
          </motion.div>
        </Grid>

        {/* Data Consistency */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.6 }}
        >
          <DataConsistency data={dashboardData?.consistency} />
        </motion.div>

        {/* Bottom Grid */}
        <Grid numItemsLg={2} className="gap-6">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.7 }}
          >
            <SystemHealth data={dashboardData?.health} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.8 }}
          >
            <AlertsPanel alerts={dashboardData?.alerts} />
          </motion.div>
        </Grid>
      </div>
    </DashboardLayout>
  )
}