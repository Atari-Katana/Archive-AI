use tokio::sync::mpsc::UnboundedSender;

#[derive(Debug, Clone, PartialEq, Eq, Copy)]
pub enum SequenceStatus {
    Waiting,
    Running,
    Preempted, // For memory eviction/swapping
    Finished,
}

#[derive(Debug, Clone)]
pub struct Sequence {
    pub seq_id: u64,
    pub prompt: String,
    pub prompt_token_ids: Vec<u32>,
    pub output_token_ids: Vec<u32>,
    pub output_text: String,
    pub status: SequenceStatus,
    /// Channel to send token chunks back to the API server
    pub sender: Option<UnboundedSender<String>>,
}

impl Sequence {
    pub fn new(
        seq_id: u64, 
        prompt: String, 
        prompt_token_ids: Vec<u32>, 
        sender: Option<UnboundedSender<String>>
    ) -> Self {
        Self {
            seq_id,
            prompt,
            prompt_token_ids,
            output_token_ids: Vec::new(),
            output_text: String::new(),
            status: SequenceStatus::Waiting,
            sender,
        }
    }

    /// Total length = prompt + generated
    pub fn get_len(&self) -> usize {
        self.prompt_token_ids.len() + self.output_token_ids.len()
    }
    
    pub fn append_token_id(&mut self, token_id: u32) {
        self.output_token_ids.push(token_id);
    }

    pub fn set_status(&mut self, status: SequenceStatus) {
        self.status = status;
    }

    pub fn is_finished(&self) -> bool {
        self.status == SequenceStatus::Finished
    }
    
    pub fn is_running(&self) -> bool {
        self.status == SequenceStatus::Running
    }
}

#[derive(Debug, Clone)]
pub struct SequenceGroup {
    pub request_id: String,
    pub seqs: Vec<Sequence>,
    pub arrival_time: std::time::Instant,
}

impl SequenceGroup {
    pub fn new(request_id: String, seqs: Vec<Sequence>) -> Self {
        Self {
            request_id,
            seqs,
            arrival_time: std::time::Instant::now(),
        }
    }

    /// Check if all sequences in group are finished
    pub fn is_finished(&self) -> bool {
        self.seqs.iter().all(|s| s.is_finished())
    }

    /// Get total tokens in this group (for scheduling cost)
    pub fn total_tokens(&self) -> usize {
        self.seqs.iter().map(|s| s.get_len()).sum()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sequence_lifecycle() {
        let mut seq = Sequence::new(1, "test".to_string(), vec![1, 2, 3], None);
        assert_eq!(seq.status, SequenceStatus::Waiting);
        assert_eq!(seq.get_len(), 3);

        seq.set_status(SequenceStatus::Running);
        assert!(seq.is_running());

        seq.append_token_id(4);
        assert_eq!(seq.get_len(), 4);
        assert_eq!(seq.output_token_ids, vec![4]);

        seq.set_status(SequenceStatus::Finished);
        assert!(seq.is_finished());
    }

    #[test]
    fn test_sequence_group() {
        let seq1 = Sequence::new(1, "p1".to_string(), vec![1], None);
        let seq2 = Sequence::new(2, "p2".to_string(), vec![2], None);
        let group = SequenceGroup::new("req1".to_string(), vec![seq1, seq2]);
        
        assert!(!group.is_finished());
        assert_eq!(group.total_tokens(), 2);
    }
}