"""
Comprehensive Metrics Collection System for Ingest Worker

This module provides unified metrics collection across all ingest worker operations:
- Data pipeline performance metrics
- PDF processing success rates and timings  
- STT processing accuracy and performance
- Vector embedding generation metrics
- System resource utilization
- Error rates and recovery statistics
"""

import time
import asyncio
import psutil
import logging
import json
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
from enum import Enum

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: datetime
    metric_type: MetricType
    tags: Dict[str, str]
    unit: str = 'count'


@dataclass
class ProcessingStats:
    """Processing pipeline statistics."""
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    avg_processing_time: float = 0.0
    success_rate: float = 0.0
    error_rate: float = 0.0
    last_processed: Optional[datetime] = None


@dataclass
class SystemMetrics:
    """System resource metrics."""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io_bytes: int
    disk_io_bytes: int
    open_file_descriptors: int
    timestamp: datetime


class IngestWorkerMetrics:
    """Centralized metrics collection for ingest worker operations."""
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.start_time = datetime.utcnow()
        
        # Processing pipeline metrics
        self.pdf_processing = ProcessingStats()
        self.stt_processing = ProcessingStats()
        self.data_processing = ProcessingStats()
        self.vector_processing = ProcessingStats()
        self.scraping_stats = ProcessingStats()
        
        # Performance tracking
        self.active_operations = defaultdict(int)
        self.processing_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.error_counts = defaultdict(int)
        self.quality_scores: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # System resource tracking
        self.system_metrics_history: deque = deque(maxlen=1440)  # 24 hours worth
        
        # Data quality metrics
        self.data_quality = {
            'pdf_extraction_accuracy': deque(maxlen=100),
            'stt_word_error_rate': deque(maxlen=100),
            'vector_similarity_scores': deque(maxlen=100),
            'data_completeness_ratio': deque(maxlen=100)
        }
    
    def record_metric(
        self, 
        name: str, 
        value: float, 
        metric_type: MetricType = MetricType.COUNTER,
        tags: Dict[str, str] = None, 
        unit: str = 'count'
    ):
        """Record a metric point."""
        metric = MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            metric_type=metric_type,
            tags=tags or {},
            unit=unit
        )
        
        self.metrics[name].append(metric)
        self._cleanup_old_metrics()
        
        logger.debug(f"Recorded metric: {name}={value} {unit} {tags}")
    
    def record_processing_operation(
        self, 
        operation_type: str, 
        success: bool, 
        processing_time: float,
        quality_score: Optional[float] = None,
        details: Dict[str, Any] = None
    ):
        """Record processing operation metrics."""
        tags = {
            'operation': operation_type,
            'success': str(success).lower()
        }
        
        if details:
            tags.update({k: str(v) for k, v in details.items()})
        
        # Record basic metrics
        self.record_metric(f'{operation_type}_operations_total', 1, MetricType.COUNTER, tags)
        self.record_metric(f'{operation_type}_duration_seconds', processing_time, MetricType.TIMER, tags, 'seconds')
        
        # Track processing times
        self.processing_times[operation_type].append(processing_time)
        
        # Update operation-specific stats
        stats = self._get_processing_stats(operation_type)
        stats.total_processed += 1
        stats.last_processed = datetime.utcnow()
        
        if success:
            stats.successful += 1
        else:
            stats.failed += 1
            self.error_counts[operation_type] += 1
        
        # Update derived metrics
        stats.success_rate = stats.successful / stats.total_processed
        stats.error_rate = stats.failed / stats.total_processed
        stats.avg_processing_time = sum(self.processing_times[operation_type]) / len(self.processing_times[operation_type])
        
        # Record quality score if provided
        if quality_score is not None:
            self.quality_scores[operation_type].append(quality_score)
            self.record_metric(f'{operation_type}_quality_score', quality_score, MetricType.GAUGE, tags)
    
    def record_pdf_processing(
        self, 
        pdf_url: str, 
        success: bool, 
        processing_time: float,
        extraction_method: str = 'text',
        pages_processed: int = 0,
        text_length: int = 0,
        confidence_score: Optional[float] = None
    ):
        """Record PDF processing metrics."""
        details = {
            'extraction_method': extraction_method,
            'pages': str(pages_processed),
            'text_length_category': self._categorize_text_length(text_length)
        }
        
        self.record_processing_operation(
            'pdf_processing', 
            success, 
            processing_time, 
            confidence_score, 
            details
        )
        
        # PDF-specific metrics
        self.record_metric('pdf_pages_processed_total', pages_processed, MetricType.COUNTER, details)
        self.record_metric('pdf_text_length_chars', text_length, MetricType.GAUGE, details, 'characters')
        
        if confidence_score:
            self.data_quality['pdf_extraction_accuracy'].append(confidence_score)
    
    def record_stt_processing(
        self, 
        audio_duration: float, 
        success: bool, 
        processing_time: float,
        word_count: int = 0,
        confidence_score: Optional[float] = None,
        language: str = 'ja'
    ):
        """Record STT processing metrics."""
        details = {
            'language': language,
            'audio_duration_category': self._categorize_duration(audio_duration)
        }
        
        self.record_processing_operation(
            'stt_processing', 
            success, 
            processing_time, 
            confidence_score, 
            details
        )
        
        # STT-specific metrics
        self.record_metric('stt_audio_duration_seconds', audio_duration, MetricType.GAUGE, details, 'seconds')
        self.record_metric('stt_words_generated_total', word_count, MetricType.COUNTER, details)
        
        if success and audio_duration > 0:
            wpm = word_count / (audio_duration / 60)  # Words per minute
            self.record_metric('stt_words_per_minute', wpm, MetricType.GAUGE, details, 'wpm')
        
        if confidence_score:
            # Convert to Word Error Rate equivalent (inverse)
            wer = 1.0 - confidence_score
            self.data_quality['stt_word_error_rate'].append(wer)
    
    def record_vector_processing(
        self, 
        text_chunks: int, 
        success: bool, 
        processing_time: float,
        embedding_dimension: int = 0,
        similarity_score: Optional[float] = None
    ):
        """Record vector embedding processing metrics."""
        details = {
            'chunks': str(text_chunks),
            'dimension': str(embedding_dimension)
        }
        
        self.record_processing_operation(
            'vector_processing', 
            success, 
            processing_time, 
            similarity_score, 
            details
        )
        
        # Vector-specific metrics
        self.record_metric('vector_chunks_processed_total', text_chunks, MetricType.COUNTER, details)
        self.record_metric('vector_embedding_dimension', embedding_dimension, MetricType.GAUGE, details)
        
        if similarity_score:
            self.data_quality['vector_similarity_scores'].append(similarity_score)
    
    def record_data_pipeline_operation(
        self, 
        operation: str, 
        records_processed: int, 
        success: bool, 
        processing_time: float,
        data_completeness: Optional[float] = None
    ):
        """Record data pipeline operation metrics."""
        details = {
            'pipeline_operation': operation,
            'records_category': self._categorize_record_count(records_processed)
        }
        
        self.record_processing_operation(
            'data_pipeline', 
            success, 
            processing_time, 
            data_completeness, 
            details
        )
        
        # Pipeline-specific metrics
        self.record_metric('pipeline_records_processed_total', records_processed, MetricType.COUNTER, details)
        
        if data_completeness:
            self.data_quality['data_completeness_ratio'].append(data_completeness)
    
    def record_system_metrics(self):
        """Record current system resource metrics."""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network and Disk I/O
            net_io = psutil.net_io_counters()
            disk_io = psutil.disk_io_counters()
            
            # File descriptors
            process = psutil.Process()
            open_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
            
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage_percent=disk_percent,
                network_io_bytes=net_io.bytes_sent + net_io.bytes_recv,
                disk_io_bytes=disk_io.read_bytes + disk_io.write_bytes,
                open_file_descriptors=open_fds,
                timestamp=datetime.utcnow()
            )
            
            self.system_metrics_history.append(metrics)
            
            # Record as individual metrics
            tags = {'service': 'ingest_worker'}
            self.record_metric('system_cpu_percent', cpu_percent, MetricType.GAUGE, tags, 'percent')
            self.record_metric('system_memory_percent', memory.percent, MetricType.GAUGE, tags, 'percent')
            self.record_metric('system_disk_percent', disk_percent, MetricType.GAUGE, tags, 'percent')
            self.record_metric('system_open_fds', open_fds, MetricType.GAUGE, tags)
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """Get comprehensive processing summary."""
        now = datetime.utcnow()
        uptime_seconds = (now - self.start_time).total_seconds()
        
        # Calculate quality metrics averages
        quality_summary = {}
        for metric_name, values in self.data_quality.items():
            if values:
                quality_summary[metric_name] = {
                    'average': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }
        
        # Get latest system metrics
        latest_system = self.system_metrics_history[-1] if self.system_metrics_history else None
        
        return {
            'service': 'ingest_worker',
            'uptime_seconds': uptime_seconds,
            'timestamp': now.isoformat(),
            'processing_stats': {
                'pdf_processing': asdict(self.pdf_processing),
                'stt_processing': asdict(self.stt_processing),
                'data_processing': asdict(self.data_processing),
                'vector_processing': asdict(self.vector_processing),
                'scraping_stats': asdict(self.scraping_stats)
            },
            'quality_metrics': quality_summary,
            'system_metrics': asdict(latest_system) if latest_system else None,
            'active_operations': dict(self.active_operations),
            'error_counts': dict(self.error_counts)
        }
    
    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        # Add service info
        lines.append('# HELP ingest_worker_info Service information')
        lines.append('# TYPE ingest_worker_info gauge')
        lines.append(f'ingest_worker_info{{version="1.0.0"}} 1')
        
        # Group metrics by name
        metric_groups = defaultdict(list)
        for metric_list in self.metrics.values():
            for metric in metric_list:
                metric_groups[metric.name].append(metric)
        
        for metric_name, metric_list in metric_groups.items():
            # Determine Prometheus type
            if metric_list:
                sample_metric = metric_list[0]
                if sample_metric.metric_type == MetricType.COUNTER:
                    prom_type = 'counter'
                elif sample_metric.metric_type == MetricType.GAUGE:
                    prom_type = 'gauge'
                elif sample_metric.metric_type == MetricType.HISTOGRAM:
                    prom_type = 'histogram'
                else:
                    prom_type = 'gauge'
            else:
                prom_type = 'gauge'
            
            lines.append(f'# HELP {metric_name} {metric_name.replace("_", " ").title()}')
            lines.append(f'# TYPE {metric_name} {prom_type}')
            
            # Group by tags and get latest value
            tag_groups = {}
            for metric in metric_list:
                tag_str = ','.join(f'{k}="{v}"' for k, v in sorted(metric.tags.items()))
                tag_groups[tag_str] = metric.value  # Latest value wins
            
            for tags, value in tag_groups.items():
                if tags:
                    lines.append(f'{metric_name}{{{tags}}} {value}')
                else:
                    lines.append(f'{metric_name} {value}')
        
        return '\n'.join(lines)
    
    def _get_processing_stats(self, operation_type: str) -> ProcessingStats:
        """Get processing stats object for operation type."""
        stats_map = {
            'pdf_processing': self.pdf_processing,
            'stt_processing': self.stt_processing,
            'data_pipeline': self.data_processing,
            'vector_processing': self.vector_processing,
            'scraping': self.scraping_stats
        }
        return stats_map.get(operation_type, ProcessingStats())
    
    def _categorize_text_length(self, length: int) -> str:
        """Categorize text length for grouping."""
        if length < 1000:
            return 'short'
        elif length < 10000:
            return 'medium'
        else:
            return 'long'
    
    def _categorize_duration(self, duration: float) -> str:
        """Categorize audio duration for grouping."""
        if duration < 60:
            return 'short'
        elif duration < 600:
            return 'medium'
        else:
            return 'long'
    
    def _categorize_record_count(self, count: int) -> str:
        """Categorize record count for grouping."""
        if count < 10:
            return 'small'
        elif count < 100:
            return 'medium'
        else:
            return 'large'
    
    def _cleanup_old_metrics(self):
        """Remove metrics older than retention period."""
        cutoff = datetime.utcnow() - timedelta(hours=self.retention_hours)
        
        for metric_name, metric_list in self.metrics.items():
            while metric_list and metric_list[0].timestamp < cutoff:
                metric_list.popleft()


class OperationTimer:
    """Context manager for timing operations."""
    
    def __init__(self, metrics: IngestWorkerMetrics, operation_type: str, **kwargs):
        self.metrics = metrics
        self.operation_type = operation_type
        self.kwargs = kwargs
        self.start_time = None
        self.success = True
    
    def __enter__(self):
        self.start_time = time.time()
        self.metrics.active_operations[self.operation_type] += 1
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.success = exc_type is None
            
            self.metrics.record_processing_operation(
                self.operation_type,
                self.success,
                duration,
                **self.kwargs
            )
            
            self.metrics.active_operations[self.operation_type] -= 1
    
    def set_quality_score(self, score: float):
        """Set quality score for this operation."""
        self.kwargs['quality_score'] = score
    
    def set_details(self, **details):
        """Set additional details for this operation."""
        self.kwargs.setdefault('details', {}).update(details)


# Global metrics instance
ingest_metrics = IngestWorkerMetrics()


# Convenience functions
def time_operation(operation_type: str, **kwargs):
    """Decorator for timing operations."""
    return OperationTimer(ingest_metrics, operation_type, **kwargs)


def record_pdf_processing(pdf_url: str, success: bool, processing_time: float, **kwargs):
    """Record PDF processing metrics."""
    ingest_metrics.record_pdf_processing(pdf_url, success, processing_time, **kwargs)


def record_stt_processing(audio_duration: float, success: bool, processing_time: float, **kwargs):
    """Record STT processing metrics."""
    ingest_metrics.record_stt_processing(audio_duration, success, processing_time, **kwargs)


def record_vector_processing(text_chunks: int, success: bool, processing_time: float, **kwargs):
    """Record vector processing metrics."""
    ingest_metrics.record_vector_processing(text_chunks, success, processing_time, **kwargs)


def get_metrics_summary():
    """Get comprehensive metrics summary."""
    return ingest_metrics.get_processing_summary()


def get_prometheus_metrics():
    """Get Prometheus formatted metrics."""
    return ingest_metrics.get_prometheus_metrics()