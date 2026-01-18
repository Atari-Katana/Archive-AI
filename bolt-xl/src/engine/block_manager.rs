use std::collections::HashMap;

/// Manages allocation of blocks for KV cache
pub struct BlockAllocator {
    free_blocks: Vec<usize>,
}

impl BlockAllocator {
    pub fn new(num_blocks: usize) -> Self {
        let free_blocks: Vec<usize> = (0..num_blocks).collect();
        Self {
            free_blocks,
        }
    }

    pub fn allocate(&mut self) -> Option<usize> {
        self.free_blocks.pop()
    }

    pub fn free(&mut self, block_id: usize) {
        if !self.free_blocks.contains(&block_id) {
            self.free_blocks.push(block_id);
        }
    }

    pub fn can_allocate(&self, num_blocks: usize) -> bool {
        self.free_blocks.len() >= num_blocks
    }
}

/// Block table for paged KV cache management
#[derive(Debug, Default)]
pub struct BlockTable {
    table: HashMap<String, Vec<usize>>,
}

impl BlockTable {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn set_blocks(&mut self, seq_id: String, blocks: Vec<usize>) {
        self.table.insert(seq_id, blocks);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_block_allocator() {
        let mut allocator = BlockAllocator::new(10);
        assert!(allocator.can_allocate(5));
        let blocks: Vec<_> = (0..5).filter_map(|_| allocator.allocate()).collect();
        assert_eq!(blocks.len(), 5);
        assert!(allocator.can_allocate(5));
        allocator.free(blocks[0]);
        assert!(allocator.can_allocate(6));
    }
}
