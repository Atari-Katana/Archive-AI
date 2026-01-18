use std::collections::VecDeque;
use crate::engine::sequence::{SequenceGroup, SequenceStatus};
use crate::config::Config;

/// Represents a batch of requests to be processed together
#[derive(Debug)]
pub struct Batch {
    /// Request IDs in this batch
    pub request_ids: Vec<String>,
    /// Sequence groups in this batch
    pub seq_groups: Vec<SequenceGroup>,
}

pub struct Scheduler {
    config: Config,
    waiting: VecDeque<SequenceGroup>,
    running: VecDeque<SequenceGroup>,
}

impl Scheduler {
    pub fn new(config: Config) -> Self {
        Self {
            config,
            waiting: VecDeque::new(),
            running: VecDeque::new(),
        }
    }

    pub fn add_request(&mut self, seq_group: SequenceGroup) -> anyhow::Result<()> {
        self.waiting.push_back(seq_group);
        Ok(())
    }

    pub fn step(&mut self) -> Batch {
        // 1. Prioritize Running (Decode)
        // Since we are running SERIAL execution in the executor for stability,
        // the "batch size" limit is less about tokens and more about latency tolerance.
        // But we respect the config limits.
        
        let mut scheduled = Vec::new();
        let mut current_tokens = 0;
        
        // 1. Keep running existing sequences (Decode)
        let mut next_running = VecDeque::new();
        while let Some(mut sg) = self.running.pop_front() {
            // Check if finished
            if sg.is_finished() {
                continue; 
            }
            
            // Allow if fits in max_num_seqs (already checked) and tokens
            if current_tokens < self.config.max_num_batched_tokens {
                // Decode cost ~ 1 token per seq
                current_tokens += 1;
                scheduled.push(sg.clone());
                next_running.push_back(sg);
            } else {
                // Preempt / Pause
                sg.seqs.iter_mut().for_each(|s| s.set_status(SequenceStatus::Waiting)); // Or Preempted
                self.waiting.push_front(sg);
            }
        }
        self.running = next_running;

        // 2. Promote Waiting (Prefill)
        // Only if we have space (and ideally, don't mix large prefill with decode for latency, but we mix for throughput)
        while let Some(mut sg) = self.waiting.pop_front() {
            let seq_len = sg.total_tokens();
            
            if current_tokens + seq_len <= self.config.max_num_batched_tokens 
               && self.running.len() < self.config.max_num_seqs {
                
                // Mark as running
                for seq in &mut sg.seqs {
                    seq.set_status(SequenceStatus::Running);
                }
                
                current_tokens += seq_len;
                scheduled.push(sg.clone());
                self.running.push_back(sg);
            } else {
                // Head of line blocking: if first one doesn't fit, stop.
                self.waiting.push_front(sg);
                break;
            }
        }

        Batch {
            request_ids: scheduled.iter().map(|sg| sg.request_id.clone()).collect(),
            seq_groups: scheduled,
        }
    }

    pub fn running_mut(&mut self) -> &mut VecDeque<SequenceGroup> {
        &mut self.running
    }
}
