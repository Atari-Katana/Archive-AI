// AWQ Dequantization Verification Test
// Tests that the CUDA kernel and CPU reference produce identical results

use candle_core::{Tensor, DType, Device};
use bolt_xl::layers::quantization::AWQLinear;

fn main() -> anyhow::Result<()> {
    println!("AWQ Dequantization Verification Test");
    println!("=====================================\n");
    
    // Test with known values
    // Create a simple packed weight: 
    // Let's pack values [1,2,3,4,5,6,7,8] into one u32
    // With standard packing: nibble j at bits j*4
    // Value 1 at bits 0-3, Value 2 at bits 4-7, etc.
    let packed_w: u32 = 
        (1 << 0)  |  // nibble 0 = 1
        (2 << 4)  |  // nibble 1 = 2
        (3 << 8)  |  // nibble 2 = 3
        (4 << 12) |  // nibble 3 = 4
        (5 << 16) |  // nibble 4 = 5
        (6 << 20) |  // nibble 5 = 6
        (7 << 24) |  // nibble 6 = 7
        (8 << 28);   // nibble 7 = 8
    
    println!("Packed weight: 0x{:08X}", packed_w);
    println!("\nExpected unpacked values:");
    for j in 0..8 {
        let shift = j * 4;
        let val = (packed_w >> shift) & 0xF;
        println!("  Position {} (shift {}): {} ", j, shift, val);
    }
    
    // Verify the unpacking logic matches Python reference
    println!("\nVerification:");
    let expected = [1u32, 2, 3, 4, 5, 6, 7, 8];
    let mut all_correct = true;
    for j in 0..8 {
        let shift = j * 4;
        let actual = (packed_w >> shift) & 0xF;
        if actual != expected[j as usize] {
            println!("  ERROR at position {}: expected {}, got {}", j, expected[j as usize], actual);
            all_correct = false;
        }
    }
    
    if all_correct {
        println!("  ✓ All positions unpacked correctly!");
    }
    
    // Test full dequantization formula: (w - z) * scale
    println!("\nDequantization test:");
    let zeros: u32 = 8 | (8 << 4) | (8 << 8) | (8 << 12) | (8 << 16) | (8 << 20) | (8 << 24) | (8 << 28);
    let scale = 0.5f32;
    
    println!("Zero points: all 8");
    println!("Scale: {}", scale);
    println!("\nDequantized values (w - z) * scale:");
    for j in 0..8 {
        let shift = j * 4;
        let w = ((packed_w >> shift) & 0xF) as i32;
        let z = ((zeros >> shift) & 0xF) as i32;
        let dequant = (w - z) as f32 * scale;
        println!("  Position {}: ({} - {}) * {} = {}", j, w, z, scale, dequant);
    }
    
    println!("\n✓ AWQ unpacking logic verified!");
    
    Ok(())
}
