use criterion::{black_box, criterion_group, criterion_main, Criterion};
use bolt_xl::engine::scheduler::{Scheduler, Batch};
use bolt_xl::config::Config;

fn benchmark_scheduler_step(c: &mut Criterion) {
    let config = Config {
        max_num_batched_tokens: 1000,
        max_num_seqs: 100,
        max_model_len: 1000,
        kvcache_block_size: 16,
        ..Default::default()
    };
    let mut scheduler = Scheduler::new(config);

    // Add some requests
    for i in 0..10 {
        scheduler.add_request(format!("req{}", i), vec![1; 50]).unwrap();
    }

    c.bench_function("scheduler_step", |b| {
        b.iter(|| {
            let _batch = black_box(scheduler.step());
        })
    });
}

fn benchmark_throughput(c: &mut Criterion) {
    // Simulate throughput: tokens per second
    let config = Config {
        max_num_batched_tokens: 2048,
        max_num_seqs: 128,
        max_model_len: 4096,
        kvcache_block_size: 16,
        ..Default::default()
    };
    let mut scheduler = Scheduler::new(config);

    // Fill with requests
    for i in 0..64 {
        scheduler.add_request(format!("req{}", i), vec![1; 100]).unwrap();
    }

    c.bench_function("throughput_simulation", |b| {
        b.iter(|| {
            for _ in 0..100 { // Simulate 100 steps
                let batch = scheduler.step();
                if batch.seq_groups.is_empty() {
                    break;
                }
            }
        })
    });
}

criterion_group!(benches, benchmark_scheduler_step, benchmark_throughput);
criterion_main!(benches);