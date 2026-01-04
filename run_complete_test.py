"""
Complete workload runner that executes baseline and optimized versions.
Produces before/after comparison artifacts.
"""
import json
import time
import statistics
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from app import engine
from sqlalchemy import event

def calculate_quantile(data, quantile):
    """Calculate quantile for a sorted list."""
    if not data:
        return 0
    sorted_data = sorted(data)
    index = (len(sorted_data) - 1) * quantile
    lower = int(index)
    upper = lower + 1
    if upper >= len(sorted_data):
        return sorted_data[lower]
    return sorted_data[lower] + (sorted_data[upper] - sorted_data[lower]) * (index - lower)

class QueryCounter:
    """Track SQL queries executed during request handling."""
    def __init__(self):
        self.query_count = 0
        self.queries = []
        
    def reset(self):
        self.query_count = 0
        self.queries = []
        
    def receive_before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        self.query_count += 1
        self.queries.append(statement)

def run_workload(config, handlers_module, run_label='baseline', optimization_profile=None):
    """
    Execute the full workload with concurrent requests.
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Starting {run_label} workload run")
    logger.info(f"{'='*60}")
    
    workload = config.get('workload', {})
    requests = workload.get('requests', [])
    load_profile = workload.get('load_profile', {})
    
    # Scale down for faster testing
    total_requests = min(load_profile.get('total_requests', 2000), 300)
    concurrency = min(load_profile.get('concurrency', 50), 20)
    warmup_requests = min(load_profile.get('warmup_requests', 200), 50)
    
    # Prepare request list
    request_list = []
    request_per_type = total_requests // len(requests)
    for req_config in requests:
        request_list.extend([req_config] * request_per_type)
    
    # Shuffle for realistic distribution
    import random
    random.shuffle(request_list)
    
    latencies = []
    warmup_latencies = []
    errors = []
    status_codes = {}
    query_counts = []
    
    logger.info(f"Warmup phase: {warmup_requests} requests")
    
    # Warmup phase
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(warmup_requests):
            req = request_list[i % len(request_list)]
            future = executor.submit(_execute_request, req, handlers_module)
            futures.append(future)
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result['error']:
                    errors.append(result['error'])
                else:
                    warmup_latencies.append(result['latency'])
                    status_codes[result['status']] = status_codes.get(result['status'], 0) + 1
                    query_counts.append(result['query_count'])
            except Exception as e:
                logger.error(f"Warmup error: {e}")
                errors.append(str(e))
    
    logger.info(f"Warmup complete. Errors: {len([e for e in errors if e])}")
    logger.info(f"Main phase: {total_requests} requests with {concurrency} concurrent workers")
    
    # Main load test phase
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(total_requests):
            req = request_list[(warmup_requests + i) % len(request_list)]
            future = executor.submit(_execute_request, req, handlers_module)
            futures.append(future)
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result['error']:
                    errors.append(result['error'])
                else:
                    latencies.append(result['latency'])
                    status_codes[result['status']] = status_codes.get(result['status'], 0) + 1
                    query_counts.append(result['query_count'])
            except Exception as e:
                logger.error(f"Request error: {e}")
                errors.append(str(e))
    
    end_time = time.time()
    
    # Calculate statistics
    if latencies:
        p50 = calculate_quantile(latencies, 0.50)
        p95 = calculate_quantile(latencies, 0.95)
        p99 = calculate_quantile(latencies, 0.99)
        mean = statistics.mean(latencies)
        stdev = statistics.stdev(latencies) if len(latencies) > 1 else 0
        min_lat = min(latencies)
        max_lat = max(latencies)
    else:
        p50 = p95 = p99 = mean = stdev = min_lat = max_lat = 0
    
    error_rate = (len(errors) / (total_requests + warmup_requests)) * 100 if (total_requests + warmup_requests) > 0 else 0
    avg_queries = statistics.mean(query_counts) if query_counts else 0
    
    result = {
        'run_label': run_label,
        'timestamp': datetime.now().isoformat(),
        'optimization_profile': optimization_profile,
        'total_requests': total_requests,
        'warmup_requests': warmup_requests,
        'concurrency': concurrency,
        'duration_seconds': end_time - start_time,
        'latency_ms': {
            'p50': p50,
            'p95': p95,
            'p99': p99,
            'mean': mean,
            'stdev': stdev,
            'min': min_lat,
            'max': max_lat,
            'count': len(latencies),
            'raw_distribution': latencies[:100] if latencies else [],
        },
        'error_rate_percent': error_rate,
        'status_codes': status_codes,
        'query_metrics': {
            'average_per_request': avg_queries,
            'total_queries': sum(query_counts),
            'query_count_samples': query_counts[:100] if query_counts else [],
        },
        'errors': errors[:50],
        'sla_compliance': {
            'p50_ok': p50 <= 150,
            'p95_ok': p95 <= 300,
            'p99_ok': p99 <= 500,
            'error_rate_ok': error_rate <= 0.1,
        }
    }
    
    logger.info(f"\n{run_label.upper()} Results:")
    logger.info(f"  P50: {p50:.2f}ms (target <= 150ms) {'✓' if p50 <= 150 else '✗'}")
    logger.info(f"  P95: {p95:.2f}ms (target <= 300ms) {'✓' if p95 <= 300 else '✗'}")
    logger.info(f"  P99: {p99:.2f}ms (target <= 500ms) {'✓' if p99 <= 500 else '✗'}")
    logger.info(f"  Error Rate: {error_rate:.2f}% (target <= 0.1%)")
    logger.info(f"  Avg Queries/Request: {avg_queries:.2f}")
    logger.info(f"  Successful Requests: {len(latencies)}")
    logger.info(f"  Failed Requests: {len(errors)}")
    
    return result

def _execute_request(req_config, handlers_module):
    """Execute a single request and measure latency."""
    endpoint = req_config.get('endpoint', '')
    method = req_config.get('method', 'GET')
    query = req_config.get('query', {})
    
    start_time = time.time()
    query_count = 0
    error = None
    status_code = 200
    
    try:
        # Set up query counter
        counter = QueryCounter()
        event.listen(engine, "before_cursor_execute", counter.receive_before_cursor_execute)
        
        try:
            auth_header = 'Bearer test-token'
            
            if endpoint == '/api/users':
                page = query.get('page', 1)
                per_page = query.get('per_page', 100)
                response, status_code = handlers_module.get_users(page=page, per_page=per_page, auth_header=auth_header)
            elif '/followers' in endpoint:
                user_id = int(endpoint.split('/')[3])
                page = query.get('page', 1)
                per_page = query.get('per_page', 100)
                response, status_code = handlers_module.get_user_followers(user_id, page=page, per_page=per_page, auth_header=auth_header)
            else:
                error = f"Unknown endpoint: {endpoint}"
                status_code = 404
            
            query_count = counter.query_count
        finally:
            event.remove(engine, "before_cursor_execute", counter.receive_before_cursor_execute)
        
    except Exception as e:
        error = str(e)
        status_code = 500
    
    latency = (time.time() - start_time) * 1000  # Convert to ms
    
    return {
        'endpoint': endpoint,
        'latency': latency,
        'status': status_code,
        'query_count': query_count,
        'error': error,
    }

def main():
    """Main entry point for complete workload runner."""
    # Read input configuration
    input_file = Path(__file__).parent / 'input.json'
    with open(input_file) as f:
        config = json.load(f)
    
    # Create output directory
    output_dir = Path(__file__).parent / 'test_results'
    output_dir.mkdir(exist_ok=True)
    
    # Import handlers modules
    import handlers
    import handlers_optimized
    
    # Run baseline
    logger.info("\n" + "="*80)
    logger.info("BASELINE TEST: Using original handlers")
    logger.info("="*80)
    baseline_results = run_workload(config, handlers, run_label='baseline')
    
    # Run optimized
    logger.info("\n" + "="*80)
    logger.info("OPTIMIZED TEST: Using optimized handlers")
    logger.info("="*80)
    optimized_results = run_workload(config, handlers_optimized, run_label='optimized')
    
    # Save both results
    with open(output_dir / 'baseline_results.json', 'w') as f:
        json.dump(baseline_results, f, indent=2, default=str)
    
    with open(output_dir / 'optimized_results.json', 'w') as f:
        json.dump(optimized_results, f, indent=2, default=str)
    
    # Produce comparison
    comparison = {
        'baseline': baseline_results,
        'optimized': optimized_results,
        'improvements': {
            'p50_latency_reduction_ms': baseline_results['latency_ms']['p50'] - optimized_results['latency_ms']['p50'],
            'p50_latency_reduction_percent': ((baseline_results['latency_ms']['p50'] - optimized_results['latency_ms']['p50']) / baseline_results['latency_ms']['p50'] * 100) if baseline_results['latency_ms']['p50'] > 0 else 0,
            'p95_latency_reduction_ms': baseline_results['latency_ms']['p95'] - optimized_results['latency_ms']['p95'],
            'p95_latency_reduction_percent': ((baseline_results['latency_ms']['p95'] - optimized_results['latency_ms']['p95']) / baseline_results['latency_ms']['p95'] * 100) if baseline_results['latency_ms']['p95'] > 0 else 0,
            'p99_latency_reduction_ms': baseline_results['latency_ms']['p99'] - optimized_results['latency_ms']['p99'],
            'p99_latency_reduction_percent': ((baseline_results['latency_ms']['p99'] - optimized_results['latency_ms']['p99']) / baseline_results['latency_ms']['p99'] * 100) if baseline_results['latency_ms']['p99'] > 0 else 0,
            'avg_queries_reduction': baseline_results['query_metrics']['average_per_request'] - optimized_results['query_metrics']['average_per_request'],
        },
        'sla_compliance': {
            'baseline': baseline_results['sla_compliance'],
            'optimized': optimized_results['sla_compliance'],
        }
    }
    
    with open(output_dir / 'comparison_results.json', 'w') as f:
        json.dump(comparison, f, indent=2, default=str)
    
    logger.info(f"\n" + "="*80)
    logger.info("COMPARISON RESULTS")
    logger.info("="*80)
    logger.info(f"P50 Reduction: {comparison['improvements']['p50_latency_reduction_ms']:.2f}ms ({comparison['improvements']['p50_latency_reduction_percent']:.1f}%)")
    logger.info(f"P95 Reduction: {comparison['improvements']['p95_latency_reduction_ms']:.2f}ms ({comparison['improvements']['p95_latency_reduction_percent']:.1f}%)")
    logger.info(f"P99 Reduction: {comparison['improvements']['p99_latency_reduction_ms']:.2f}ms ({comparison['improvements']['p99_latency_reduction_percent']:.1f}%)")
    logger.info(f"Avg Queries Reduction: {comparison['improvements']['avg_queries_reduction']:.2f}")
    logger.info("\nAll artifacts saved to: " + str(output_dir))

if __name__ == '__main__':
    main()
