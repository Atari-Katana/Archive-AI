use std::process::Command;
use std::fs;

fn main() {
    let out_dir = std::env::var("OUT_DIR").unwrap_or_else(|_| "target/release/build/bolt-xl/out".to_string());
    let _ = fs::create_dir_all(&out_dir);

    let stub_c = format!("{}/stub.c", out_dir);
    let stub_o = format!("{}/stub.o", out_dir);
    let fused_lib = format!("{}/libfused_sampling.a", out_dir);
    let kernels_lib = format!("{}/libkernels.a", out_dir);

    let c_content = r#"\nvoid launch_dequantize_awq() {}\nvoid launch_marlin() {}\nvoid cudaDeviceSynchronize() {}\n"#;

    if !std::path::Path::new(&stub_o).exists() {
        fs::write(&stub_c, c_content).expect("Failed to write stub C file");

        let _ = Command::new("cc")
            .args(["-c", &stub_c, "-o", &stub_o, "-fPIC"])
            .output()
            .expect("Failed to compile stub");
    }

    if !std::path::Path::new(&fused_lib).exists() {
        let _ = Command::new("ar")
            .args(["rcs", &fused_lib, &stub_o])
            .output();
    }

    if !std::path::Path::new(&kernels_lib).exists() {
        let _ = Command::new("ar")
            .args(["rcs", &kernels_lib, &stub_o])
            .output();
    }

    println!("cargo:rustc-link-search={}", out_dir);

    if std::env::var("BOLT_USE_CPU").is_ok() {
        println!("cargo:rustc-cfg=feature=\"cpu\"");
        println!("cargo:warning=Running in CPU mode (CUDA stub libraries used)");
        return;
    }

    println!("cargo:rerun-if-changed=src/kernels/awq_dequant.cu");
    println!("cargo:rerun-if-changed=build.rs");

    let nvcc = if let Ok(path) = std::env::var("NVCC") {
        path
    } else {
        "nvcc".to_string()
    };

    let awq_obj = format!("{}/awq_dequant.o", out_dir);
    let marlin_obj = format!("{}/marlin_kernel.o", out_dir);
    let sampling_obj = format!("{}/sampling_kernel.o", out_dir);

    let awq_result = Command::new(&nvcc)
        .args([
            "-c", "src/kernels/awq_dequant.cu", "-o", &awq_obj, "-O3",
            "--use_fast_math",
            "-gencode=arch=compute_80,code=sm_80",
            "-gencode=arch=compute_89,code=sm_89",
            "-gencode=arch=compute_90,code=sm_90",
            "-cudart=shared",
        ])
        .status();

    let marlin_result = Command::new(&nvcc)
        .args([
            "-c", "src/kernels/marlin/marlin_cuda_kernel.cu", "-o", &marlin_obj, "-O3",
            "--use_fast_math",
            "-gencode=arch=compute_80,code=sm_80",
            "-gencode=arch=compute_89,code=sm_89",
            "-gencode=arch=compute_90,code=sm_90",
            "-cudart=shared",
            "--expt-relaxed-constexpr",
            "-diag-suppress=39",
            "-diag-suppress=177",
        ])
        .status();

    let sampling_result = Command::new(&nvcc)
        .args([
            "-c", "src/kernels/fused_sampling.cu", "-o", &sampling_obj, "-O3",
            "--use_fast_math",
            "-gencode=arch=compute_80,code=sm_80",
            "-gencode=arch=compute_89,code=sm_89",
            "-gencode=arch=compute_90,code=sm_90",
            "-cudart=shared",
        ])
        .status();

    if awq_result.is_ok_and(|s| s.success()) &&
       marlin_result.is_ok_and(|s| s.success()) &&
       sampling_result.is_ok_and(|s| s.success()) {
        println!("cargo:warning=Successfully compiled CUDA kernels");

        let _ = Command::new("ar")
            .args(["rcs", &kernels_lib, &awq_obj, &marlin_obj, &sampling_obj])
            .output();

        println!("cargo:rustc-link-lib=curand");
        println!("cargo:rustc-link-lib=cudart");
        println!("cargo:rustc-link-lib=static=kernels");
    } else {
        println!("cargo:warning=Failed to compile CUDA kernels, using stub libraries");
    }
}